from typing import List, Dict
from urllib.parse import quote_plus
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


def create_driver(headless: bool = False) -> webdriver.Chrome:
    """
    Создаёт и настраивает Chrome WebDriver.

    По умолчанию headless=False, чтобы ты видел окно браузера
    и мог смотреть, что показывает Ozon.
    """
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ru-RU")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    )

    # Чтобы окно не закрывалось сразу после завершения скрипта (удобно для отладки)
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)

    return driver


def scrape_ozon_search(query: str, limit: int = 5, headless: bool = False) -> List[Dict]:
    """
    Парсит результаты поиска Ozon по запросу query и возвращает список товаров.

    Каждый товар — dict с ключами:
    marketplace, url, title, price, rating, raw_description.
    """
    driver = create_driver(headless=headless)
    items: List[Dict] = []

    try:
        search_url = f"https://www.ozon.ru/search/?text={quote_plus(query)}"
        logger.info("Ozon: открываем %s", search_url)
        driver.get(search_url)

        # Ждём, пока на странице появятся кликабельные плитки товаров
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "a.tile-clickable-element")
                )
            )
        except Exception as e:
            # Если не дождались плиток, сразу сохраняем HTML и логируем
            logger.warning("Ozon: не дождались плиток товаров: %s", e)
            _dump_ozon_html(driver)
            _log_access_restriction_hint(driver)
            return items

        links = driver.find_elements(By.CSS_SELECTOR, "a.tile-clickable-element")
        logger.info("Ozon: найдено ссылок-плиток: %s", len(links))

        if not links:
            _dump_ozon_html(driver)
            _log_access_restriction_hint(driver)
            return items

        for link_el in links[:limit]:
            try:
                href = link_el.get_attribute("href") or ""
                if href.startswith("/"):
                    url = "https://www.ozon.ru" + href
                else:
                    url = href

                # Заголовок — текст внутри ссылки
                title = link_el.text.strip()

                # Находим родительскую плитку, чтобы достать цену
                tile = link_el.find_element(
                    By.XPATH, "./ancestor::div[contains(@class, 'tile-root')]"
                )

                price_el = tile.find_element(
                    By.CSS_SELECTOR,
                    "span.tsHeadline500Medium",
                )
                price_text = price_el.text.split("₽")[0]
                price_text = (
                    price_text.replace("\u2009", "")
                    .replace("\xa0", "")
                    .replace(" ", "")
                )
                price = int(price_text)

                rating = None

                items.append(
                    {
                        "marketplace": "ozon",
                        "url": url,
                        "title": title,
                        "price": price,
                        "rating": rating,
                        "raw_description": title,
                    }
                )
            except Exception as e:
                logger.warning("Ошибка разбора карточки Ozon: %s", e)

    except Exception as e:
        logger.warning("Ошибка парсинга Ozon: %s", e)
        _dump_ozon_html(driver)
        _log_access_restriction_hint(driver)
    finally:
        # Для глубокой отладки можно ВРЕМЕННО закомментировать эту строку,
        # чтобы окно Chrome не закрывалось автоматически.
        driver.quit()

    logger.info("Ozon: вернули товаров: %s", len(items))
    return items


def _dump_ozon_html(driver: webdriver.Chrome) -> None:
    """Сохраняет текущий HTML страницы Ozon в файл для отладки."""
    try:
        html = driver.page_source
        with open("ozon_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("Ozon: HTML сохранён в ozon_debug.html")
    except Exception as e:
        logger.warning("Не удалось сохранить ozon_debug.html: %s", e)


def _log_access_restriction_hint(driver: webdriver.Chrome) -> None:
    """
    Пытается понять, нет ли на странице текста про ограничение доступа,
    и пишет подсказку в лог.
    """
    try:
        html_lower = driver.page_source.lower()
        if "доступ ограничен" in html_lower or "access denied" in html_lower:
            logger.warning(
                "Ozon: страница сообщает, что доступ ограничен / access denied. "
                "Это похоже на срабатывание антибот-защиты."
            )
    except Exception:
        pass