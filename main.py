import os
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from enum import Enum
from typing import Literal

from selenium_scraper import scrape_ozon_search
from wildberries_api import scrape_wb_search

from config import BACKEND_HOST, BACKEND_PORT, RESULTS_FOLDER, HISTORY_FOLDER, DATA_FOLDER
from models.requests import TextAnalyzeRequest, ParseDemoRequest, CardGenerateRequest
from models.responses import (
    CompetitionAnalysis,
    ImageAnalysis,
    CompetitorReport,
    ParsingResult,
    HealthResponse,
)
from services.history_service import history_service
from services.competitor_analyzer import analyze_text, analyze_image_base64
from llm_service import generate_card_from_text

import base64

# ---------------------------------------------------------------------------
# Инициализация приложения
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаём нужные папки при старте
for folder in [RESULTS_FOLDER, HISTORY_FOLDER, DATA_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app = FastAPI(
    title="Competitor Analyzer",
    description="AI-анализатор конкурентов на базе Yandex LLM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — разрешаем фронтенду обращаться к бэкенду
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Статика (frontend/)
# ---------------------------------------------------------------------------
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ---------------------------------------------------------------------------
# Эндпоинты
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    """Отдаёт главную страницу фронтенда."""
    index_path = os.path.join("frontend", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()

    return HTMLResponse(
        """
        <h2>Competitor Analyzer API</h2>
        <p>Документация: <a href="/docs">/docs</a></p>
        """
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Проверка работоспособности сервера."""
    return HealthResponse(status="ok")


# ------------------------------------------------------------------
# Анализ текста конкурента
# ------------------------------------------------------------------
@app.post("/analyze/text", response_model=CompetitionAnalysis)
async def analyze_text_endpoint(body: TextAnalyzeRequest):
    """
    Принимает текст конкурента (описание товара, лендинг, PDF-контент).
    Возвращает структурированный JSON-анализ с оценками и рекомендациями.
    """
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Текст не может быть пустым")

    try:
        result = analyze_text(body.text)

        history_service.add_message(
            role="user",
            content=body.text[:300],
            meta={"type": "analyze_text"},
        )
        history_service.add_message(
            role="assistant",
            content=result.model_dump_json(),
            meta={"type": "analyze_text_result"},
        )

        return result
    except Exception as e:
        logger.error("Ошибка анализа текста: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Анализ изображения конкурента
# ------------------------------------------------------------------
@app.post("/analyze/image", response_model=ImageAnalysis)
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    extra_description: Optional[str] = Form(None),
):
    """
    Принимает изображение конкурента (скриншот, баннер, упаковка).
    Возвращает анализ визуального стиля и маркетинговые рекомендации.
    """
    contents = await file.read()
    image_b64 = base64.b64encode(contents).decode("utf-8")

    try:
        result = analyze_image_base64(image_b64, extra_description)

        history_service.add_message(
            role="user",
            content=f"[изображение: {file.filename}]",
            meta={"type": "analyze_image", "filename": file.filename},
        )
        history_service.add_message(
            role="assistant",
            content=result.model_dump_json(),
            meta={"type": "analyze_image_result"},
        )

        return result
    except Exception as e:
        logger.error("Ошибка анализа изображения: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Фильтрация конкурентов по запросу
# ------------------------------------------------------------------
def _normalize_words(text: str) -> list[str]:
    if not text:
        return []

    cleaned = (
        text.lower()
        .replace(",", " ")
        .replace(".", " ")
        .replace("/", " ")
        .replace("-", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace(":", " ")
        .replace(";", " ")
        .replace('"', " ")
        .replace("'", " ")
    )
    return [w.strip() for w in cleaned.split() if w.strip()]


def _split_query_keywords(query: str) -> tuple[list[str], list[str]]:
    """
    Возвращает:
    - strong_keywords: тип товара и базовые смысловые слова
    - soft_keywords: модель, бренд, характеристики
    """
    stop_words = {
        "для", "с", "со", "по", "на", "и", "или", "в", "во", "под", "над",
        "из", "без", "от", "до", "у", "к", "ко", "о", "об", "это",
        "the", "a", "an"
    }

    product_words = {
        "наушники", "телефон", "смартфон", "айфон", "iphone", "гарнитура",
        "пюре", "сок", "йогурт", "ноутбук", "планшет", "часы", "колонка",
        "клавиатура", "мышь", "монитор", "микрофон", "камера"
    }

    words = _normalize_words(query)
    words = [w for w in words if len(w) >= 2 and w not in stop_words]

    strong_keywords: list[str] = []
    soft_keywords: list[str] = []

    for w in words:
        if w in product_words:
            strong_keywords.append(w)
        elif len(w) >= 3:
            soft_keywords.append(w)

    if not strong_keywords:
        strong_keywords = [w for w in words if len(w) >= 4][:2]

    return strong_keywords, soft_keywords


def _score_product_relevance(title: str, query: str) -> tuple[int, str]:
    """
    Возвращает:
    - score: числовой рейтинг релевантности
    - note: пояснение
    """
    title_words = _normalize_words(title)
    strong_keywords, soft_keywords = _split_query_keywords(query)

    strong_hits = [kw for kw in strong_keywords if kw in title_words or kw in title.lower()]
    soft_hits = [kw for kw in soft_keywords if kw in title_words or kw in title.lower()]

    score = 0
    note_parts: list[str] = []

    if strong_hits:
        score += 10 * len(strong_hits)
        note_parts.append(f"совпали ключевые слова товара: {', '.join(strong_hits)}")

    if soft_hits:
        score += 3 * len(soft_hits)
        note_parts.append(f"совпали доп. слова: {', '.join(soft_hits)}")

    if strong_hits and not soft_hits:
        note = "Частично релевантный товар: совпадает тип товара, но модель/характеристики отличаются."
    elif strong_hits and soft_hits:
        note = "Релевантный товар: совпадает тип товара и часть уточняющих характеристик."
    else:
        note = "Нерелевантный товар: не найдено совпадений по ключевым словам запроса."

    if note_parts:
        note += " " + " | ".join(note_parts)

    return score, note


def filter_competitors_by_query(products: list[dict], query: str) -> list[dict]:
    """
    Логика:
    - если товар не совпадает по типу товара/смысловым словам — выбрасываем;
    - если совпадает по типу товара, но модель отличается (например X300 вместо X200) —
      оставляем как частично релевантный;
    - если после фильтрации ничего не осталось — возвращаем пустой список.
    """
    if not products or not query:
        return products

    filtered: list[dict] = []

    for product in products:
        title = str(product.get("title", "")).strip()
        if not title:
            continue

        score, note = _score_product_relevance(title, query)

        if score >= 10:
            item = dict(product)
            item["relevance_score"] = score
            item["relevance_note"] = note
            filtered.append(item)

    filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    print(">>> После фильтрации по query осталось:", len(filtered))
    for item in filtered:
        print(
            ">>> REL:",
            item.get("relevance_score"),
            "|",
            item.get("title"),
            "|",
            item.get("relevance_note"),
        )

    return filtered


# ------------------------------------------------------------------
# Вспомогательная функция парсинга конкурентов (Ozon + WB)
# ------------------------------------------------------------------
def search_competitors_on_marketplace(
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    Собирает список конкурентов с Ozon и Wildberries.
    Возвращает list[dict] с полями:
    marketplace, url, title, price, rating, raw_description, relevance_score, relevance_note.
    """
    competitors: list[dict] = []

    # 1. Ozon через Selenium
    try:
        ozon_products = scrape_ozon_search(query, limit)
        for p in ozon_products:
            title = p.get("title", "")
            score, note = _score_product_relevance(title, query)

            if score >= 10:
                competitors.append(
                    {
                        "marketplace": "ozon",
                        "url": p.get("url", ""),
                        "title": title,
                        "price": p.get("price"),
                        "rating": p.get("rating"),
                        "raw_description": title,
                        "relevance_score": score,
                        "relevance_note": note,
                    }
                )
    except Exception as e:
        logger.warning("Ошибка парсинга Ozon: %s", e)

    print(">>> После Ozon конкурентов:", len(competitors))

    # 2. Wildberries через API
    try:
        wb_products = scrape_wb_search(query, limit)
        print(">>> WB вернул товаров до фильтрации:", len(wb_products))

        wb_products = filter_competitors_by_query(wb_products, query)
        print(">>> WB вернул товаров после фильтрации:", len(wb_products))

        competitors.extend(wb_products)
    except Exception as e:
        print(">>> ОШИБКА WB:", e)

    print(">>> Всего конкурентов после WB:", len(competitors))
    return competitors[:limit]


# ------------------------------------------------------------------
# Парсинг и анализ конкурентов
# ------------------------------------------------------------------
@app.post("/parse/demo", response_model=CompetitorReport)
async def parse_demo_endpoint(body: ParseDemoRequest):
    """
    Собирает данные конкурентов по поисковому запросу,
    анализирует каждого через LLM и возвращает сводный отчёт.
    Сохраняет отчёт в history/.
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Запрос не может быть пустым")

    limit = body.limit or 5

    try:
        raw_competitors = search_competitors_on_marketplace(
            query=body.query,
            limit=limit,
        )

        analyzed: list[ParsingResult] = []

        for c in raw_competitors:
            try:
                analysis_input = c.get("raw_description") or c.get("title") or ""
                analysis = analyze_text(analysis_input)

                analyzed.append(
                    ParsingResult(
                        marketplace=c["marketplace"],
                        url=c["url"],
                        title=c["title"],
                        price=c.get("price"),
                        rating=c.get("rating"),
                        analysis=analysis,
                        relevance_score=c.get("relevance_score"),
                        relevance_note=c.get("relevance_note"),
                    )
                )
            except Exception as e:
                logger.warning("Ошибка анализа конкурента %s: %s", c.get("url"), e)
                analyzed.append(
                    ParsingResult(
                        marketplace=c["marketplace"],
                        url=c["url"],
                        title=c["title"],
                        price=c.get("price"),
                        rating=c.get("rating"),
                        analysis=None,
                        relevance_score=c.get("relevance_score"),
                        relevance_note=c.get("relevance_note"),
                    )
                )

        report = CompetitorReport(query=body.query, competitors=analyzed)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(HISTORY_FOLDER, f"competition_{ts}.json")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        history_service.add_message(
            role="user",
            content=body.query,
            meta={"type": "parse_demo", "limit": limit},
        )
        history_service.add_message(
            role="assistant",
            content=f"Отчёт сохранён: {report_path}",
            meta={"type": "parse_demo_result", "file": report_path},
        )

        return report

    except Exception as e:
        logger.error("Ошибка parse/demo: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Генерация карточки товара (перенос из Flaskmedia)
# ------------------------------------------------------------------
@app.post("/generate/card")
async def generate_card_endpoint(body: CardGenerateRequest):
    """Генерирует карточку товара для Ozon/Wildberries по текстовому описанию."""
    if not body.description.strip():
        raise HTTPException(status_code=400, detail="Описание не может быть пустым")

    try:
        card = generate_card_from_text(body.description)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_path = os.path.join(RESULTS_FOLDER, f"card_{ts}.json")

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(
                {"created_at": datetime.now().isoformat(), "card": card},
                f,
                ensure_ascii=False,
                indent=2,
            )

        return {"card": card, "saved_to": result_path}
    except Exception as e:
        logger.error("Ошибка генерации карточки: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# История диалогов
# ------------------------------------------------------------------
@app.get("/history")
async def get_history():
    """Возвращает историю всех запросов и ответов."""
    return {"history": history_service.get_history()}


@app.delete("/history")
async def clear_history():
    """Очищает историю диалогов."""
    history_service.clear_history()
    return {"status": "ok", "message": "История очищена"}