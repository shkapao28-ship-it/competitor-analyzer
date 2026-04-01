from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
)

from gui.api_client import ApiClient
from gui.formatters import (
    format_analysis_result,
    format_card_result,
    format_clear_history_result,
    format_error,
    format_history,
    format_parse_result,
)


class CompetitionMonitorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.api = ApiClient()
        self.current_image_path = ""

        # сюда будем класть последний ответ /parse/demo,
        # чтобы при клике по строке брать правильного конкурента
        self._last_parse_report = None

        self.setWindowTitle("Competition Monitor")
        self.resize(1100, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_text_tab()
        self._build_image_tab()
        self._build_parse_tab()
        self._build_card_tab()
        self._build_history_tab()

        self.statusBar().showMessage("Готово")

    # --------------------- ВКЛАДКА: ТЕКСТ ---------------------

    def _build_text_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("Анализ текста")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText(
            "Вставь текст товара, описание, отзывы или данные конкурента..."
        )

        self.text_run_btn = QPushButton("Запустить анализ")
        self.text_run_btn.clicked.connect(self.run_text_analysis)

        self.text_result = QTextEdit()
        self.text_result.setReadOnly(True)

        layout.addWidget(title)
        layout.addWidget(self.text_input)
        layout.addWidget(self.text_run_btn)
        layout.addWidget(self.text_result)

        self.tabs.addTab(tab, "Анализ текста")

    # --------------------- ВКЛАДКА: ИЗОБРАЖЕНИЕ ---------------------

    def _build_image_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("Анализ изображения")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        file_row = QHBoxLayout()
        self.image_path_input = QLineEdit()
        self.image_path_input.setPlaceholderText("Выбери файл изображения...")
        browse_btn = QPushButton("Обзор")
        browse_btn.clicked.connect(self.browse_image)

        file_row.addWidget(self.image_path_input)
        file_row.addWidget(browse_btn)

        self.image_run_btn = QPushButton("Запустить анализ изображения")
        self.image_run_btn.clicked.connect(self.run_image_analysis)

        self.image_result = QTextEdit()
        self.image_result.setReadOnly(True)

        layout.addWidget(title)
        layout.addLayout(file_row)
        layout.addWidget(self.image_run_btn)
        layout.addWidget(self.image_result)

        self.tabs.addTab(tab, "Анализ изображения")

    # --------------------- ВКЛАДКА: ПАРСИНГ ---------------------

    def _build_parse_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("Демо-парсинг конкурентов")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        form = QFormLayout()
        self.parse_query_input = QLineEdit()
        self.parse_query_input.setPlaceholderText("Например: беспроводные наушники")
        form.addRow("Запрос:", self.parse_query_input)

        self.parse_run_btn = QPushButton("Запустить парсинг")
        self.parse_run_btn.clicked.connect(self.run_parse_demo)

        # ТАБЛИЦА КОНКУРЕНТОВ
        self.parse_table = QTableWidget()
        self.parse_table.setColumnCount(6)
        self.parse_table.setHorizontalHeaderLabels(
            ["Marketplace", "Название", "Цена", "Рейтинг", "Релевантность", "Ссылка"]
        )
        self.parse_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.parse_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.parse_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.parse_table.horizontalHeader().setStretchLastSection(True)
        self.parse_table.horizontalHeader().setDefaultSectionSize(160)
        self.parse_table.verticalHeader().setVisible(False)
        self.parse_table.setAlternatingRowColors(True)

        # При выборе строки показываем подробный анализ
        self.parse_table.itemSelectionChanged.connect(
            self.on_parse_table_selection_changed
        )

        # ПОДРОБНЫЙ ТЕКСТ ОТЧЁТА
        self.parse_result = QTextEdit()
        self.parse_result.setReadOnly(True)
        self.parse_result.setPlaceholderText(
            "Здесь будет подробный отчёт по выбранному конкуренту..."
        )

        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.parse_run_btn)
        layout.addWidget(self.parse_table, stretch=2)
        layout.addWidget(self.parse_result, stretch=3)

        self.tabs.addTab(tab, "Парсинг")

    # --------------------- ВКЛАДКА: КАРТОЧКА ---------------------

    def _build_card_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("Генерация карточки товара")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        form = QFormLayout()

        self.card_product_name = QLineEdit()
        self.card_product_name.setPlaceholderText(
            "Например: Беспроводные наушники X200"
        )

        self.card_category = QLineEdit()
        self.card_category.setPlaceholderText("Например: Электроника / Наушники")

        self.card_description = QPlainTextEdit()
        self.card_description.setPlaceholderText("Кратко опиши товар...")

        self.card_features = QPlainTextEdit()
        self.card_features.setPlaceholderText(
            "Каждую характеристику пиши с новой строки.\n"
            "Например:\n"
            "Bluetooth 5.3\n"
            "Шумоподавление\n"
            "До 30 часов работы"
        )

        form.addRow("Название товара:", self.card_product_name)
        form.addRow("Категория:", self.card_category)
        form.addRow("Описание:", self.card_description)
        form.addRow("Характеристики:", self.card_features)

        self.card_run_btn = QPushButton("Сгенерировать карточку")
        self.card_run_btn.clicked.connect(self.run_generate_card)

        self.card_result = QTextEdit()
        self.card_result.setReadOnly(True)

        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.card_run_btn)
        layout.addWidget(self.card_result)

        self.tabs.addTab(tab, "Генерация карточки")

    # --------------------- ВКЛАДКА: ИСТОРИЯ ---------------------

    def _build_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("История")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        buttons_row = QHBoxLayout()
        self.history_refresh_btn = QPushButton("Обновить историю")
        self.history_refresh_btn.clicked.connect(self.load_history)

        self.history_clear_btn = QPushButton("Очистить историю")
        self.history_clear_btn.clicked.connect(self.clear_history)

        buttons_row.addWidget(self.history_refresh_btn)
        buttons_row.addWidget(self.history_clear_btn)
        buttons_row.addStretch()

        self.history_result = QTextEdit()
        self.history_result.setReadOnly(True)

        layout.addWidget(title)
        layout.addLayout(buttons_row)
        layout.addWidget(self.history_result)

        self.tabs.addTab(tab, "История")

    # --------------------- ВСПОМОГАТЕЛЬНОЕ ---------------------

    def browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбери изображение",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if file_path:
            self.current_image_path = file_path
            self.image_path_input.setText(file_path)

    def _set_busy(self, busy: bool, message: str = ""):
        buttons = [
            self.text_run_btn,
            self.image_run_btn,
            self.parse_run_btn,
            self.card_run_btn,
            self.history_refresh_btn,
            self.history_clear_btn,
        ]
        for button in buttons:
            button.setEnabled(not busy)

        self.statusBar().showMessage(message if busy else "Готово")

    def _show_error(self, error: Exception):
        text = format_error(error)
        QMessageBox.critical(self, "Ошибка", text)
        self.statusBar().showMessage("Ошибка")

    # --------------------- ЛОГИКА: ТЕКСТ ---------------------

    def run_text_analysis(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Пустой ввод", "Введи текст для анализа.")
            return

        try:
            self._set_busy(True, "Выполняется анализ текста...")
            data = self.api.analyze_text(text)
            self.text_result.setPlainText(format_analysis_result(data))
        except Exception as e:
            self.text_result.setPlainText(format_error(e))
            self._show_error(e)
        finally:
            self._set_busy(False)

    # --------------------- ЛОГИКА: ИЗОБРАЖЕНИЕ ---------------------

    def run_image_analysis(self):
        image_path = self.image_path_input.text().strip()
        if not image_path:
            QMessageBox.warning(self, "Файл не выбран", "Выбери изображение для анализа.")
            return

        try:
            self._set_busy(True, "Выполняется анализ изображения...")
            data = self.api.analyze_image(image_path)
            self.image_result.setPlainText(format_analysis_result(data))
        except Exception as e:
            self.image_result.setPlainText(format_error(e))
            self._show_error(e)
        finally:
            self._set_busy(False)

    # --------------------- ЛОГИКА: ПАРСИНГ ---------------------

    def run_parse_demo(self):
        query = self.parse_query_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Пустой ввод", "Введи запрос для парсинга.")
            return

        try:
            self._set_busy(True, "Выполняется демо-парсинг...")
            data = self.api.parse_demo(query)
            # data — это CompetitorReport: { query, competitors: [...], created_at }
            self._last_parse_report = data
            self._fill_parse_table(data)
            # общий текстовый отчёт по всем конкурентам — оставим как сейчас
            self.parse_result.setPlainText(format_parse_result(data))
        except Exception as e:
            self._last_parse_report = None
            self.parse_table.setRowCount(0)
            self.parse_result.setPlainText(format_error(e))
            self._show_error(e)
        finally:
            self._set_busy(False)

    def _fill_parse_table(self, report: dict):
        """Заполнить таблицу конкурентами из CompetitorReport."""
        competitors = report.get("competitors", []) or []

        self.parse_table.setRowCount(len(competitors))

        for row, comp in enumerate(competitors):
            marketplace = comp.get("marketplace") or ""
            title = comp.get("title") or ""
            price = comp.get("price")
            rating = comp.get("rating")
            relevance_score = comp.get("relevance_score")
            relevance_note = comp.get("relevance_note") or ""
            url = comp.get("url") or ""

            # Приводим к строкам для таблицы
            price_str = "" if price is None else f"{price:.0f}"
            rating_str = "" if rating is None else f"{rating:.1f}"
            if relevance_score is None:
                relevance_str = ""
            else:
                # Короткая форма: "16 — релевантный", остальное можно в detailed
                if relevance_score >= 13:
                    relevance_short = "релевантный"
                elif relevance_score >= 10:
                    relevance_short = "частично релевантный"
                else:
                    relevance_short = "сомнительная релевантность"
                relevance_str = f"{relevance_score} — {relevance_short}"

            items = [
                QTableWidgetItem(marketplace),
                QTableWidgetItem(title),
                QTableWidgetItem(price_str),
                QTableWidgetItem(rating_str),
                QTableWidgetItem(relevance_str),
                QTableWidgetItem(url),
            ]

            for col, item in enumerate(items):
                # делаем ячейки только для чтения
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.parse_table.setItem(row, col, item)

        self.parse_table.resizeColumnsToContents()

    def on_parse_table_selection_changed(self):
        """Когда пользователь выбирает строку в таблице — показать подробный анализ."""
        if not self._last_parse_report:
            return

        selected_rows = self.parse_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        competitors = self._last_parse_report.get("competitors", []) or []
        if row < 0 or row >= len(competitors):
            return

        comp = competitors[row]

        # Если есть analysis — красиво отформатируем, иначе просто покажем основные поля
        analysis = comp.get("analysis")
        relevance_score = comp.get("relevance_score")
        relevance_note = comp.get("relevance_note")

        parts = []

        parts.append(f"Marketplace: {comp.get('marketplace')}")
        parts.append(f"URL: {comp.get('url')}")
        parts.append(f"Название: {comp.get('title')}")
        if comp.get("price") is not None:
            parts.append(f"Цена: {comp.get('price')}")
        if comp.get("rating") is not None:
            parts.append(f"Рейтинг: {comp.get('rating')}")

        if relevance_score is not None:
            parts.append(f"Relevance score: {relevance_score}")
        if relevance_note:
            parts.append(f"Relevance note: {relevance_note}")

        parts.append("")  # пустая строка перед детальным анализом

        if analysis:
            # используем уже готовый форматтер, чтобы не дублировать логику
            parts.append("Детальный анализ конкурента:")
            parts.append("")
            try:
                parts.append(format_analysis_result(analysis))
            except Exception:
                # если форматтер ожидает чуть другой формат, просто покажем сырые поля
                strengths = analysis.get("strengths") or []
                weaknesses = analysis.get("weaknesses") or []
                unique_offers = analysis.get("unique_offers") or []
                recommendations = analysis.get("recommendations") or []
                summary = analysis.get("summary") or ""

                parts.append("Strengths:")
                for s in strengths:
                    parts.append(f"- {s}")
                parts.append("")
                parts.append("Weaknesses:")
                for w in weaknesses:
                    parts.append(f"- {w}")
                parts.append("")
                parts.append("Unique offers:")
                for u in unique_offers:
                    parts.append(f"- {u}")
                parts.append("")
                parts.append("Recommendations:")
                for r in recommendations:
                    parts.append(f"- {r}")
                parts.append("")
                parts.append("Summary:")
                parts.append(summary)
        else:
            parts.append("Анализ по этому конкуренту отсутствует (analysis=None).")

        self.parse_result.setPlainText("\n".join(parts))

    # --------------------- ЛОГИКА: КАРТОЧКА ---------------------

    def run_generate_card(self):
        product_name = self.card_product_name.text().strip()
        category = self.card_category.text().strip()
        description = self.card_description.toPlainText().strip()
        features = self.card_features.toPlainText().strip()

        if not product_name:
            QMessageBox.warning(self, "Нет названия", "Укажи название товара.")
            return

        try:
            self._set_busy(True, "Генерируется карточка товара...")
            data = self.api.generate_card(
                product_name=product_name,
                category=category,
                description=description,
                features=features,
            )
            self.card_result.setPlainText(format_card_result(data))
        except Exception as e:
            self.card_result.setPlainText(format_error(e))
            self._show_error(e)
        finally:
            self._set_busy(False)

    # --------------------- ЛОГИКА: ИСТОРИЯ ---------------------

    def load_history(self):
        try:
            self._set_busy(True, "Загружается история...")
            data = self.api.get_history()
            self.history_result.setPlainText(format_history(data))
        except Exception as e:
            self.history_result.setPlainText(format_error(e))
            self._show_error(e)
        finally:
            self._set_busy(False)

    def clear_history(self):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Точно очистить историю?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._set_busy(True, "Очищается история...")
            data = self.api.clear_history()
            self.history_result.setPlainText(format_clear_history_result(data))
        except Exception as e:
            self.history_result.setPlainText(format_error(e))
            self._show_error(e)
        finally:
            self._set_busy(False)