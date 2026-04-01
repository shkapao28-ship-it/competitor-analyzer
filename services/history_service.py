import json
import os
import logging
from datetime import datetime
from typing import Optional

from config import HISTORY_FILE, MAX_HISTORY_MESSAGES, HISTORY_FOLDER

logger = logging.getLogger(__name__)


class HistoryService:
    """
    Сервис управления историей диалогов и анализов.

    Хранит историю в памяти (список сообщений) и синхронизирует
    её с файлом HISTORY_FILE на диске.

    Используется как синглтон: один объект на всё приложение.
    Это гарантирует, что контекст диалога не теряется между запросами.
    """

    def __init__(self):
        os.makedirs(HISTORY_FOLDER, exist_ok=True)
        self._messages: list[dict] = []
        self._load_from_file()

    # ------------------------------------------------------------------
    # Основные методы
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str, meta: Optional[dict] = None) -> None:
        """
        Добавляет сообщение в историю.

        role    — "user" | "assistant" | "system"
        content — текст сообщения или JSON-строка с результатом анализа
        meta    — опциональные доп. данные (тип запроса, url и т.п.)
        """
        message = {
            "role":       role,
            "content":    content,
            "created_at": datetime.now().isoformat(),
        }
        if meta:
            message["meta"] = meta

        self._messages.append(message)

        # Обрезаем историю, если превышен лимит
        if len(self._messages) > MAX_HISTORY_MESSAGES:
            self._messages = self._messages[-MAX_HISTORY_MESSAGES:]

        self._save_to_file()

    def get_history(self) -> list[dict]:
        """Возвращает всю историю сообщений."""
        return self._messages

    def clear_history(self) -> None:
        """Очищает историю в памяти и на диске."""
        self._messages = []
        self._save_to_file()
        logger.info("История очищена.")

    def get_last_n(self, n: int) -> list[dict]:
        """Возвращает последние n сообщений (удобно для контекста LLM)."""
        return self._messages[-n:]

    # ------------------------------------------------------------------
    # Работа с файлом
    # ------------------------------------------------------------------

    def _save_to_file(self) -> None:
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Ошибка сохранения истории: %s", e)

    def _load_from_file(self) -> None:
        if not os.path.exists(HISTORY_FILE):
            self._messages = []
            return
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                self._messages = json.load(f)
            logger.info("История загружена: %d сообщений.", len(self._messages))
        except Exception as e:
            logger.error("Ошибка загрузки истории: %s", e)
            self._messages = []


# ---------------------------------------------------------------------------
# Синглтон — один экземпляр на всё приложение.
# Импортируй его так: from services.history_service import history_service
# ---------------------------------------------------------------------------
history_service = HistoryService()