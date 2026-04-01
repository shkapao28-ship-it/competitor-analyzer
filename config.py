import os
from dotenv import load_dotenv

load_dotenv()

# Yandex LLM API
YANDEX_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
FOLDER_ID      = os.getenv("YANDEX_CLOUD_FOLDER")
MODEL_ID       = os.getenv("YANDEX_MODEL_ID")

# Сервер FastAPI
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000

# История диалогов
HISTORY_FILE         = "history/history.json"
MAX_HISTORY_MESSAGES = 20

# Парсинг конкурентов
MARKETPLACE_SEARCH_LIMIT = 5
COMPETITOR_SOURCES       = ["mock"]
DEMO_COMPETITOR_URLS     = [
    "https://www.ozon.ru",
    "https://www.wildberries.ru",
]

# Папки проекта
RESULTS_FOLDER = "results"
HISTORY_FOLDER = "history"
DATA_FOLDER    = "data"