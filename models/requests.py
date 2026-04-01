from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TextAnalyzeRequest(BaseModel):
    """Запрос на анализ текста конкурента."""
    text: str


class ImageAnalyzeRequest(BaseModel):
    """Запрос на анализ изображения конкурента (base64)."""
    image_base64: str
    extra_description: Optional[str] = None  # опциональное текстовое дополнение


class Marketplace(str, Enum):
    """Маркетплейс(ы), по которым искать конкурентов."""
    ozon = "ozon"
    wildberries = "wildberries"
    both = "both"


class ParseDemoRequest(BaseModel):
    """Запрос на парсинг и анализ конкурентов по поисковому запросу."""
    query: str                 # например: "яблочное пюре, Россия"
    limit: Optional[int] = 5   # сколько конкурентов собрать
    marketplace: Marketplace = Marketplace.both  # где искать: Ozon, WB или оба


class CardGenerateRequest(BaseModel):
    """Запрос на генерацию карточки товара (текст)."""
    description: str


class CardGenerateImageRequest(BaseModel):
    """Запрос на генерацию карточки товара (изображение, base64)."""
    image_base64: str
    extra_description: Optional[str] = None