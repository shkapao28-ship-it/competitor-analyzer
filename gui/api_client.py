import os
from typing import Any

import requests


class ApiClient:
    def __init__(self, base_url: str | None = None, timeout: int = 120):
        self.base_url = (base_url or os.getenv("API_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _handle_response(self, response: requests.Response) -> Any:
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise RuntimeError(f"HTTP {response.status_code}: {detail}") from e

        try:
            return response.json()
        except Exception as e:
            raise RuntimeError("Сервер вернул не JSON-ответ.") from e

    def analyze_text(self, text: str) -> dict:
        response = requests.post(
            self._url("/analyze/text"),
            json={"text": text},
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def analyze_image(self, image_path: str) -> dict:
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                self._url("/analyze/image"),
                files=files,
                timeout=self.timeout,
            )
        return self._handle_response(response)

    def parse_demo(self, query: str) -> dict:
        response = requests.post(
            self._url("/parse/demo"),
            json={"query": query},
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def generate_card(self, product_name: str, category: str, description: str, features: str) -> dict:
        payload = {
            "product_name": product_name,
            "category": category,
            "description": description,
            "features": [item.strip() for item in features.splitlines() if item.strip()],
        }
        response = requests.post(
            self._url("/generate/card"),
            json=payload,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def get_history(self) -> dict:
        response = requests.get(
            self._url("/history"),
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def clear_history(self) -> dict:
        response = requests.delete(
            self._url("/history"),
            timeout=self.timeout,
        )
        return self._handle_response(response)