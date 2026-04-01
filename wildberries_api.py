import time
from typing import List, Dict, Any

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.wildberries.ru/",
    "Origin": "https://www.wildberries.ru",
    "Connection": "keep-alive",
}


def _safe_price(product: dict) -> float | None:
    price_u = product.get("priceU")
    if price_u:
        return price_u / 100

    sizes = product.get("sizes") or []
    if sizes:
        price_info = sizes[0].get("price") or {}
        product_price = price_info.get("product")
        if product_price:
            return product_price / 100

    return None


def _build_product_item(product: dict) -> dict:
    title = (product.get("name") or "").replace("\n", " ").replace("\r", " ").strip()
    product_id = product.get("id")

    url_product = (
        f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"
        if product_id
        else None
    )

    price = _safe_price(product)
    rating = product.get("reviewRating") or product.get("rating")
    feedbacks = product.get("feedbacks")

    raw_description = title
    if price is not None:
        raw_description += f". Цена: {price} руб."
    if rating is not None:
        raw_description += f" Рейтинг: {rating}."
    if feedbacks is not None:
        raw_description += f" Отзывов: {feedbacks}."

    return {
        "marketplace": "wildberries",
        "title": title,
        "url": url_product,
        "price": price,
        "rating": rating,
        "feedbacks": feedbacks,
        "raw_description": raw_description,
    }


def _request_wb_json(query: str, timeout: int = 10) -> dict | None:
    base_url = "https://search.wb.ru/exactmatch/ru/common/v18/search"

    params = {
        "appType": 1,
        "curr": "rub",
        "dest": -1257786,
        "lang": "ru",
        "page": 1,
        "query": query,
        "resultset": "catalog",
        "sort": "popular",
        "spp": 30,
    }

    backoff_schedule = [2, 5, 10]

    for attempt, sleep_seconds in enumerate(backoff_schedule, start=1):
        try:
            resp = requests.get(base_url, params=params, headers=HEADERS, timeout=timeout)

            if resp.status_code == 429:
                print(
                    f">>> WB вернул 429 (попытка {attempt}/{len(backoff_schedule)}), "
                    f"ждём {sleep_seconds} сек"
                )
                time.sleep(sleep_seconds)
                continue

            resp.raise_for_status()
            data = resp.json()
            print(">>> WB JSON keys:", list(data.keys()))
            return data

        except requests.HTTPError as e:
            if getattr(e.response, "status_code", None) == 429:
                print(
                    f">>> WB HTTPError 429 (попытка {attempt}/{len(backoff_schedule)}), "
                    f"ждём {sleep_seconds} сек"
                )
                time.sleep(sleep_seconds)
                continue

            print(f">>> WB HTTP ошибка: {e}")
            return None

        except requests.RequestException as e:
            print(f">>> WB RequestException: {e}")
            return None

        except ValueError as e:
            print(f">>> WB не смог распарсить JSON: {e}")
            return None

    print(">>> WB: исчерпали все попытки после 429")
    return None


def scrape_wb_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Поиск товаров на Wildberries по внутреннему поисковому API.

    Возвращает список словарей вида:
    {
        "marketplace": "wildberries",
        "title": str,
        "url": str | None,
        "price": float | None,
        "rating": float | None,
        "feedbacks": int | None,
        "raw_description": str,
    }
    """
    print(">>> Вызвали scrape_wb_search, query =", query)

    data = _request_wb_json(query=query, timeout=10)
    if not data:
        print(">>> Не удалось получить данные от WB")
        return []

    products = data.get("products", [])[:limit]
    print(">>> WB products count:", len(products))

    items: List[Dict[str, Any]] = []
    for product in products:
        try:
            items.append(_build_product_item(product))
        except Exception as e:
            print(f">>> Ошибка обработки товара WB: {e}")

    print(">>> Вернули товаров из scrape_wb_search:", len(items))
    return items
