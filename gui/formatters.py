import json
from typing import Any


def _pretty_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return str(data)


def _is_primitive(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _format_value(value: Any, indent: int = 0) -> str:
    space = " " * indent

    if _is_primitive(value):
        return f"{value}"

    if isinstance(value, list):
        if not value:
            return "[]"

        lines = []
        for item in value:
            if _is_primitive(item):
                lines.append(f"{space}- {item}")
            else:
                nested = _format_value(item, indent + 2)
                lines.append(f"{space}- {nested}")
        return "\n".join(lines)

    if isinstance(value, dict):
        if not value:
            return "{}"

        lines = []
        for key, item in value.items():
            title = str(key).replace("_", " ").capitalize()
            if _is_primitive(item):
                lines.append(f"{space}{title}: {item}")
            else:
                lines.append(f"{space}{title}:")
                lines.append(_format_value(item, indent + 2))
        return "\n".join(lines)

    return str(value)


def format_analysis_result(data: dict) -> str:
    if not isinstance(data, dict):
        return _pretty_json(data)

    lines = ["Результат анализа", ""]

    for key, value in data.items():
        title = str(key).replace("_", " ").capitalize()

        if _is_primitive(value):
            lines.append(f"{title}: {value}")
            lines.append("")
        else:
            lines.append(title)
            lines.append("-" * len(title))
            lines.append(_format_value(value, 2))
            lines.append("")

    return "\n".join(lines).strip()


def format_parse_result(data: dict) -> str:
    if not isinstance(data, dict):
        return _pretty_json(data)

    lines = ["Результат парсинга", ""]

    query = data.get("query")
    if query:
        lines.append(f"Запрос: {query}")
        lines.append("")

    competitors = data.get("competitors")
    created_at = data.get("created_at")

    # Если есть поле competitors
    if isinstance(competitors, list):
        if competitors:
            lines.append(f"Найдено конкурентов: {len(competitors)}")
            lines.append("")
            lines.append("Конкуренты:")
            lines.append(_format_value(competitors, 2))
        else:
            lines.append("Конкуренты не найдены.")
            lines.append("Возможные причины:")
            lines.append("- Маркетплейс вернул пустой результат по этому запросу.")
            lines.append("- Маркетплейс временно ограничил доступ (429 / антибот-защита).")
    else:
        # Если структура другая — показываем сыро
        lines.append("Поле конкурентов отсутствует в ответе.")
        lines.append(_pretty_json(data))

    if created_at:
        lines.append("")
        lines.append(f"Время создания отчёта: {created_at}")

    return "\n".join(lines).strip()


def format_card_result(data: dict) -> str:
    if not isinstance(data, dict):
        return _pretty_json(data)

    lines = ["Сгенерированная карточка товара", ""]

    preferred_order = [
        "product_name",
        "category",
        "title",
        "short_title",
        "description",
        "short_description",
        "features",
        "benefits",
        "advantages",
        "keywords",
        "seo_keywords",
        "result",
        "card",
    ]

    used_keys = set()

    for key in preferred_order:
        if key in data:
            value = data[key]
            title = key.replace("_", " ").capitalize()

            if _is_primitive(value):
                lines.append(f"{title}:")
                lines.append(f"{value}")
            else:
                lines.append(f"{title}:")
                lines.append(_format_value(value, 2))
            lines.append("")
            used_keys.add(key)

    for key, value in data.items():
        if key in used_keys:
            continue

        title = key.replace("_", " ").capitalize()
        if _is_primitive(value):
            lines.append(f"{title}:")
            lines.append(f"{value}")
        else:
            lines.append(f"{title}:")
            lines.append(_format_value(value, 2))
        lines.append("")

    return "\n".join(lines).strip()


def format_history(data: dict) -> str:
    if not isinstance(data, dict):
        return _pretty_json(data)

    history = data.get("history", [])

    if not history:
        return "История пуста."

    lines = ["История запросов", ""]

    for index, item in enumerate(history, start=1):
        lines.append(f"{index}. Запись")
        lines.append("-" * 20)

        if isinstance(item, dict):
            for key, value in item.items():
                title = str(key).replace("_", " ").capitalize()
                if _is_primitive(value):
                    lines.append(f"{title}: {value}")
                else:
                    lines.append(f"{title}:")
                    lines.append(_format_value(value, 2))
        else:
            lines.append(str(item))

        lines.append("")

    return "\n".join(lines).strip()


def format_clear_history_result(data: dict) -> str:
    if not isinstance(data, dict):
        return _pretty_json(data)

    if "message" in data:
        return f"История очищена.\n\nСообщение сервера: {data['message']}"

    return "История очищена."


def format_error(error: Exception) -> str:
    return f"Ошибка:\n{str(error)}"