import os
import base64
import logging
from typing import Optional

import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ---------------------------------------------------------------------------
# Переменные окружения (берутся из .env в корне проекта)
# ---------------------------------------------------------------------------
YANDEX_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
FOLDER_ID      = os.getenv("YANDEX_CLOUD_FOLDER")
MODEL_ID       = os.getenv("YANDEX_MODEL_ID")

if not YANDEX_API_KEY:
    raise ValueError("Не найден YANDEX_CLOUD_API_KEY в .env")
if not FOLDER_ID:
    raise ValueError("Не найден YANDEX_CLOUD_FOLDER в .env")
if not MODEL_ID:
    raise ValueError("Не найден YANDEX_MODEL_ID в .env")

# ---------------------------------------------------------------------------
# Константы API
# ---------------------------------------------------------------------------
BASE_URL             = "https://ai.api.cloud.yandex.net/v1"
CHAT_COMPLETIONS_URL = f"{BASE_URL}/chat/completions"

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _build_headers() -> dict:
    return {
        "Authorization": f"Api-Key {YANDEX_API_KEY.strip()}",
        "Content-Type": "application/json",
    }


def _image_to_base64(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Файл изображения не найден: {image_path}")
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _extract_text_from_response(data: dict) -> str:
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, str):
        return content
    return str(content)


def call_llm(
    system_prompt: str,
    user_content: list,
    temperature: float = 0.4,
    max_tokens: int = 1200,
) -> str:
    """
    Универсальный метод вызова Yandex LLM.
    Используется всеми сервисами проекта.
    """
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = requests.post(
        CHAT_COMPLETIONS_URL,
        headers=_build_headers(),
        json=payload,
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Ошибка Yandex Chat API: {resp.status_code} — {resp.text}"
        )

    return _extract_text_from_response(resp.json())


# ---------------------------------------------------------------------------
# Генерация карточек товара (совместимость с Flaskmedia)
# ---------------------------------------------------------------------------

_CARD_SYSTEM_PROMPT = """
ТЫ — ЭКСПЕРТ ПО СОЗДАНИЮ ПРОДАЮЩИХ КАРТОЧЕК ТОВАРОВ ДЛЯ OZON И WILDBERRIES.

ТВОЯ ЗАДАЧА — ПРЕОБРАЗОВАТЬ ДАННЫЕ (ОПИСАНИЕ ИЛИ ФОТО ТОВАРА)
В КОММЕРЧЕСКИ ЭФФЕКТИВНУЮ, SEO-ОПТИМИЗИРОВАННУЮ И СТРУКТУРИРОВАННУЮ КАРТОЧКУ ТОВАРА.

СТРУКТУРА ВЫВОДА:
1. Название
2. Краткое описание
3. Полное описание
4. Преимущества
5. Характеристики
6. Сценарии использования
7. SEO-ключи
""".strip()


def generate_card_from_text(description: str) -> str:
    user_prompt = f"""
Ниже текстовое описание товара:

\"\"\"{description}\"\"\"

Создай по нему карточку товара по указанной структуре.
""".strip()

    return call_llm(
        system_prompt=_CARD_SYSTEM_PROMPT,
        user_content=[{"type": "text", "text": user_prompt}],
        temperature=0.4,
        max_tokens=1200,
    )


def generate_card_from_image(
    image_path: str,
    extra_description: Optional[str] = None,
) -> str:
    extra = (
        f'\nДополнительное описание:\n"""{extra_description}"""'
        if extra_description
        else ""
    )

    user_prompt = f"""
На фото изображён товар для маркетплейса.

Твоя задача:
1. Понять, что за товар на картинке, как он выглядит и используется.
2. Используя изображение{extra}, сформировать карточку товара по структуре
(Название, Краткое описание, Полное описание, Преимущества, Характеристики,
Сценарии использования, SEO-ключи).

Не придумывай точные цифры, если их нельзя определить по фото.
Пиши деловым, понятным языком.
""".strip()

    image_b64 = _image_to_base64(image_path)

    return call_llm(
        system_prompt=_CARD_SYSTEM_PROMPT,
        user_content=[
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
            },
        ],
        temperature=0.4,
        max_tokens=1200,
    )