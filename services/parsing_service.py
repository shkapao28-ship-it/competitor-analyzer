import logging
import os
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import MARKETPLACE_SEARCH_LIMIT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Заглушка (mock) — используется пока нет реального парсинга
# ---------------------------------------------------------------------------

def _mock_competitors(query: str, limit: int) -> list[dict]:
    """
    Временная заглушка. Возвращает список фейковых конкурентов.
    Позволяет сразу тестировать полный pipeline без реального парсинга.
    Заменишь внутренности на реальный парсер в следующем шаге.
    """
    return [
        {
            "marketplace":       "mock",
            "url":               f"https://example.com/product-{i}",
            "title":             f"{query} — конкурент {i}",
            "price":             100.0 + i * 15,
            "rating":            round(4.0 + i * 0.1, 1),
            "raw_description":   (
                f"Качественный товар '{query}', конкурент {i}. "
                f"Произведён в России. Высокий рейтинг покупателей. "
                f"Натуральный состав, удобная упаковка."
            ),
            "image_url":         None,
        }
        for i in range(1, limit + 1)
    ]


# ---------------------------------------------------------------------------
# Реальный HTTP-парсер (без Selenium, простой requests + BeautifulSoup)
# Работает для сайтов, не требующих JavaScript.
# ---------------------------------------------------------------------------

def _parse_page_simple(url: str) -> dict:
    """
    Делает простой HTTP-запрос к странице и вытаскивает текст.
    Имитирует браузер через заголовок User-Agent.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Убираем скрипты и стили
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title       = soup.title.string.strip() if soup.title else url
        raw_text    = soup.get_text(separator=" ", strip=True)[:3000]  # лимит символов

        return {
            "marketplace":     "web",
            "url":             url,
            "title":           title,
            "price":           None,   # цену из HTML без Selenium получить сложно
            "rating":          None,
            "raw_description": raw_text,
            "image_url":       None,
        }
    except Exception as e:
        logger.error("Ошибка парсинга %s: %s", url, e)
        return {
            "marketplace":     "web",
            "url":             url,
            "title":           url,
            "price":           None,
            "rating":          None,
            "raw_description": f"Ошибка загрузки страницы: {e}",
            "image_url":       None,
        }


# ---------------------------------------------------------------------------
# Selenium-парсер (запускается реальный браузер Chrome)
# Требует: pip install selenium + установленный ChromeDriver
# Раскомментируй когда будешь готов к шагу с Selenium
# ---------------------------------------------------------------------------

# def _parse_page_selenium(url: str, screenshot_dir: str = "data/images") -> dict:
#     from selenium import webdriver
#     from selenium.webdriver.chrome.options import Options
#
#     os.makedirs(screenshot_dir, exist_ok=True)
#     options = Options()
#     options.add_argument("--headless")          # без видимого окна
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--window-size=1280,900")
#
#     driver = webdriver.Chrome(options=options)
#     screenshot_path = None
#
#     try:
#         driver.get(url)
#         time.sleep(2)   # ждём загрузки JS
#
#         # Скриншот
#         safe_name = url.replace("https://", "").replace("/", "_")[:60]
#         screenshot_path = os.path.join(screenshot_dir, f"{safe_name}.png")
#         driver.save_screenshot(screenshot_path)
#
#         title    = driver.title
#         raw_text = driver.find_element("tag name", "body").text[:3000]
#
#         return {
#             "marketplace":     "selenium",
#             "url":             url,
#             "title":           title,
#             "price":           None,
#             "rating":          None,
#             "raw_description": raw_text,
#             "image_url":       screenshot_path,
#         }
#     except Exception as e:
#         logger.error("Selenium ошибка %s: %s", url, e)
#         return {
#             "marketplace":     "selenium",
#             "url":             url,
#             "title":           url,
#             "price":           None,
#             "rating":          None,
#             "raw_description": f"Ошибка Selenium: {e}",
#             "image_url":       None,
#         }
#     finally:
#         driver.quit()


# ---------------------------------------------------------------------------
# Главная публичная функция — именно её вызывает main.py
# ---------------------------------------------------------------------------

def search_competitors_on_marketplace(
    query: str,
    limit: Optional[int] = None,
    urls: Optional[list[str]] = None,
    use_mock: bool = True,
) -> list[dict]:
    """
    Собирает данные конкурентов одним из способов:

    use_mock=True  — возвращает заглушку (для тестирования pipeline).
    use_mock=False + urls — парсит переданные URL через requests+BeautifulSoup.

    Когда будешь готов к Selenium — замени _parse_page_simple
    на _parse_page_selenium и раскомментируй блок выше.

    Возвращает список словарей с полями:
      marketplace, url, title, price, rating, raw_description, image_url
    """
    limit = limit or MARKETPLACE_SEARCH_LIMIT

    if use_mock:
        logger.info("Режим mock: возвращаем заглушку для запроса '%s'", query)
        return _mock_competitors(query, limit)

    if not urls:
        logger.warning("use_mock=False, но urls не переданы. Возвращаем mock.")
        return _mock_competitors(query, limit)

    logger.info("Парсинг %d URL для запроса '%s'...", len(urls[:limit]), query)
    results = []
    for url in urls[:limit]:
        logger.info("  -> %s", url)
        results.append(_parse_page_simple(url))
        time.sleep(1)   # пауза между запросами, чтобы не получить бан

    return results