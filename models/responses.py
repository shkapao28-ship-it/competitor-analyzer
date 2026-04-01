from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CompetitionAnalysis(BaseModel):
    """
    Результат анализа текста конкурента.
    Возвращается эндпоинтом POST /analyze/text
    """
    strengths: list[str]
    weaknesses: list[str]
    unique_offers: list[str]
    recommendations: list[str]
    summary: str
    design_score: Optional[int] = None
    animation_potential: Optional[int] = None
    seo_score: Optional[int] = None


class ImageAnalysis(BaseModel):
    """
    Результат анализа изображения конкурента.
    Возвращается эндпоинтом POST /analyze/image
    """
    description: str
    marketing_insights: list[str]
    visual_style_score: int
    visual_style_analysis: str
    recommendations: list[str]


class ParsingResult(BaseModel):
    """
    Результат парсинга одного конкурента.
    Используется внутри CompetitorReport.
    """
    marketplace: str
    url: str
    title: str
    price: Optional[float] = None
    rating: Optional[float] = None
    analysis: Optional[CompetitionAnalysis] = None
    relevance_score: Optional[int] = None
    relevance_note: Optional[str] = None


class CompetitorReport(BaseModel):
    """
    Полный отчёт по конкурентам для одного запроса.
    Возвращается эндпоинтом POST /parse/demo
    """
    query: str
    competitors: list[ParsingResult]
    created_at: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Ответ эндпоинта GET /health."""
    status: str = "ok"