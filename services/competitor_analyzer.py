import json
import logging
from typing import Optional

from llm_service import call_llm, _image_to_base64
from models.responses import CompetitionAnalysis, ImageAnalysis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Системные промпты
# ---------------------------------------------------------------------------

_TEXT_SYSTEM_PROMPT = """
Ты — эксперт по конкурентному анализу. Проанализируй предоставленный текст
конкурента и верни строго JSON-ответ без каких-либо пояснений вокруг него.

Формат ответа (строго JSON):
{
  "strengths":       ["сильная сторона 1", "сильная сторона 2", "..."],
  "weaknesses":      ["слабая сторона 1", "слабая сторона 2", "..."],
  "unique_offers":   ["уникальное предложение 1", "..."],
  "recommendations": ["рекомендация 1", "рекомендация 2", "..."],
  "summary":         "Краткое резюме анализа",
  "design_score":    7,
  "animation_potential": 5,
  "seo_score":       6
}

Требования:
- Каждый массив должен содержать 3-5 пунктов
- design_score, animation_potential, seo_score — целые числа от 0 до 10
- Пиши на русском языке
- Будь конкретен и практичен в рекомендациях
- Верни ТОЛЬКО JSON, без markdown-обёртки (без ```json)
""".strip()

_IMAGE_SYSTEM_PROMPT = """
Ты — эксперт по визуальному маркетингу и дизайну. Проанализируй изображение
конкурента (баннер, сайт, упаковка, товар) и верни строго JSON-ответ.

Формат ответа (строго JSON):
{
  "description":           "Детальное описание того, что изображено",
  "marketing_insights":    ["инсайт 1", "инсайт 2", "..."],
  "visual_style_score":    7,
  "visual_style_analysis": "Анализ визуального стиля",
  "recommendations":       ["рекомендация 1", "рекомендация 2", "..."]
}

Требования:
- visual_style_score — целое число от 0 до 10
- Каждый массив должен содержать 3-5 пунктов
- Пиши на русском языке
- Оценивай: цветовую палитру, типографику, композицию, UX/UI-элементы
- Верни ТОЛЬКО JSON, без markdown-обёртки (без ```json)
""".strip()


# ---------------------------------------------------------------------------
# Вспомогательная функция: безопасно извлекает JSON из ответа LLM
# ---------------------------------------------------------------------------

def _parse_json_response(raw: str, model_class):
    """
    Пробует распарсить строку raw как JSON и превратить в Pydantic-модель.
    Если LLM всё же обернул ответ в ```json ... ```, убирает обёртку.
    """
    text = raw.strip()
    if text.startswith("```"):
        # убираем ```json ... ``` если модель всё равно добавила
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
        return model_class(**data)
    except Exception as e:
        logger.error("Ошибка парсинга JSON от LLM: %s\nRaw: %s", e, raw)
        raise ValueError(f"LLM вернул невалидный JSON: {e}\nОтвет: {raw}")


# ---------------------------------------------------------------------------
# Публичные функции анализа
# ---------------------------------------------------------------------------

def analyze_text(text: str) -> CompetitionAnalysis:
    """
    Анализирует текст конкурента (описание товара, лендинг, PDF-контент).
    Возвращает CompetitionAnalysis с оценками и рекомендациями.
    """
    logger.info("Анализ текста конкурента (%d символов)...", len(text))

    raw = call_llm(
        system_prompt=_TEXT_SYSTEM_PROMPT,
        user_content=[{"type": "text", "text": text}],
        temperature=0.3,
        max_tokens=1000,
    )

    return _parse_json_response(raw, CompetitionAnalysis)


def analyze_image(image_path: str, extra_description: Optional[str] = None) -> ImageAnalysis:
    """
    Анализирует изображение конкурента (скриншот, баннер, упаковка).
    Возвращает ImageAnalysis с оценкой визуала и рекомендациями.
    """
    logger.info("Анализ изображения конкурента: %s", image_path)

    image_b64 = _image_to_base64(image_path)

    user_content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
        }
    ]

    if extra_description:
        user_content.insert(0, {
            "type": "text",
            "text": f"Дополнительный контекст: {extra_description}",
        })

    raw = call_llm(
        system_prompt=_IMAGE_SYSTEM_PROMPT,
        user_content=user_content,
        temperature=0.3,
        max_tokens=1000,
    )

    return _parse_json_response(raw, ImageAnalysis)


def analyze_image_base64(image_b64: str, extra_description: Optional[str] = None) -> ImageAnalysis:
    """
    Анализирует изображение конкурента, переданное как base64-строка
    (используется когда изображение пришло через HTTP-запрос, а не с диска).
    """
    logger.info("Анализ изображения конкурента (base64)...")

    user_content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
        }
    ]

    if extra_description:
        user_content.insert(0, {
            "type": "text",
            "text": f"Дополнительный контекст: {extra_description}",
        })

    raw = call_llm(
        system_prompt=_IMAGE_SYSTEM_PROMPT,
        user_content=user_content,
        temperature=0.3,
        max_tokens=1000,
    )

    return _parse_json_response(raw, ImageAnalysis)