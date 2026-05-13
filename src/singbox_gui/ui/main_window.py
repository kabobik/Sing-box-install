from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPolygon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
)

from ..autostart import enable_autostart
from ..config_adapter import adapt_config_for_linux
from ..models import (
    Profile,
    SOURCE_DIRECT_CONFIG,
    SOURCE_REMOTE_CONFIG,
    SOURCE_REMOTE_SUBSCRIPTION,
)
from ..profiles import ProfileStore
from ..service import ServiceState, SingBoxService
from ..subscriptions import SubscriptionError, SubscriptionUpdater


class MainWindow(QMainWindow):
    def __init__(self, store: ProfileStore, service: SingBoxService) -> None:
        super().__init__()
        self.store = store
        self.service = service
        self.updater = SubscriptionUpdater(store)
        self._loading_profile = False
        self._last_state = ServiceState("unknown", "unknown")

        self.setWindowTitle("Singbox GUI")
        self.resize(900, 640)

        self._build_actions()
        self._build_ui()
        self._build_tray()
        self.refresh_profiles()
        self.refresh_status()
        self.refresh_logs()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(5000)

    def _build_actions(self) -> None:
        self.open_action = QAction("Открыть", self)
        self.open_action.triggered.connect(self.show_and_raise)

        self.toggle_service_action = QAction("Старт", self)
        self.toggle_service_action.triggered.connect(self.toggle_service)

        self.restart_action = QAction("Перезапустить", self)
        self.restart_action.triggered.connect(self.restart_service)

        self.refresh_logs_action = QAction("Обновить лог", self)
        self.refresh_logs_action.triggered.connect(self.refresh_logs)

        self.quit_action = QAction("Выход", self)
        self.quit_action.triggered.connect(QApplication.instance().quit)

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_status_tab(), "Статус")
        tabs.addTab(self._build_profiles_tab(), "Профили")
        self.setCentralWidget(tabs)

    def _build_status_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        status_box = QGroupBox("Сервис")
        status_layout = QVBoxLayout(status_box)

        self.status_label = QLabel("Статус: неизвестно")
        self.status_label.setObjectName("statusLabel")
        self.enabled_label = QLabel("Автозагрузка сервиса: неизвестно")
        self.active_profile_label = QLabel("Активный профиль: не выбран")

        button_row = QHBoxLayout()
        self.toggle_button = QPushButton("Старт")
        self.toggle_button.clicked.connect(self.toggle_service)
        self.restart_button = QPushButton("Перезапустить")
        self.restart_button.clicked.connect(self.restart_service)
        self.refresh_status_button = QPushButton("Обновить")
        self.refresh_status_button.clicked.connect(self.refresh_status)

        button_row.addWidget(self.toggle_button)
        button_row.addWidget(self.restart_button)
        button_row.addWidget(self.refresh_status_button)
        button_row.addStretch(1)

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.enabled_label)
        status_layout.addWidget(self.active_profile_label)
        status_layout.addLayout(button_row)

        log_box = QGroupBox("Журнал sing-box")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.refresh_logs_button = QPushButton("Обновить лог")
        self.refresh_logs_button.clicked.connect(self.refresh_logs)
        log_layout.addWidget(self.log_view)
        log_layout.addWidget(self.refresh_logs_button, alignment=Qt.AlignRight)

        layout.addWidget(status_box)
        layout.addWidget(log_box, stretch=1)
        return widget

    def _build_profiles_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        top_row = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self.on_profile_selected)
        new_button = QPushButton("Новый")
        new_button.clicked.connect(self.create_profile)
        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(self.delete_profile)
        duplicate_button = QPushButton("Дублировать")
        duplicate_button.clicked.connect(self.duplicate_profile)

        top_row.addWidget(QLabel("Профиль:"))
        top_row.addWidget(self.profile_combo, stretch=1)
        top_row.addWidget(new_button)
        top_row.addWidget(duplicate_button)
        top_row.addWidget(delete_button)

        form_box = QGroupBox("Настройки профиля")
        form = QFormLayout(form_box)

        self.name_edit = QLineEdit()
        self.source_combo = QComboBox()
        self.source_combo.addItem("Прямой JSON", SOURCE_DIRECT_CONFIG)
        self.source_combo.addItem("URL готового sing-box JSON", SOURCE_REMOTE_CONFIG)
        self.source_combo.addItem("Подписка OpenWrt-style", SOURCE_REMOTE_SUBSCRIPTION)
        self.source_combo.currentIndexChanged.connect(self.update_source_fields)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/sing-box.json")
        self.auto_update_checkbox = QCheckBox("Автообновление позже")
        self.auto_update_checkbox.setEnabled(False)

        form.addRow("Имя:", self.name_edit)
        form.addRow("Источник:", self.source_combo)
        form.addRow("URL:", self.url_edit)
        form.addRow("", self.auto_update_checkbox)

        editor_box = QGroupBox("config.json")
        editor_layout = QVBoxLayout(editor_box)
        self.config_edit = QPlainTextEdit()
        self.config_edit.setPlaceholderText("{\n  \"log\": {\n    \"level\": \"info\"\n  }\n}\n")
        editor_layout.addWidget(self.config_edit)

        button_row = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_current_profile)
        update_button = QPushButton("Обновить URL")
        update_button.clicked.connect(self.update_from_url)
        format_button = QPushButton("Форматировать")
        format_button.clicked.connect(self.format_config)
        adapt_button = QPushButton("Адаптировать под Linux")
        adapt_button.clicked.connect(self.adapt_config_for_linux)
        check_button = QPushButton("Проверить")
        check_button.clicked.connect(self.check_current_profile)
        apply_button = QPushButton("Применить")
        apply_button.clicked.connect(self.apply_current_profile)

        button_row.addWidget(save_button)
        button_row.addWidget(update_button)
        button_row.addWidget(format_button)
        button_row.addWidget(adapt_button)
        button_row.addStretch(1)
        button_row.addWidget(check_button)
        button_row.addWidget(apply_button)

        layout.addLayout(top_row)
        layout.addWidget(form_box)
        layout.addWidget(editor_box, stretch=1)
        layout.addLayout(button_row)
        return widget

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self._status_icon("unknown"))
        self.tray.setToolTip("Singbox GUI")
        self.tray.activated.connect(self.on_tray_activated)

        menu = QMenu()
        menu.addAction(self.open_action)
        menu.addAction(self.toggle_service_action)
        menu.addAction(self.restart_action)
        menu.addSeparator()
        menu.addAction(self.refresh_logs_action)
        menu.addSeparator()
        menu.addAction(self.quit_action)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def refresh_profiles(self, select_id: str | None = None) -> None:
        profiles = self.store.list_profiles()
        active_id = select_id or self.store.active_profile_id()

        self._loading_profile = True
        self.profile_combo.clear()
        for profile in profiles:
            self.profile_combo.addItem(profile.name, profile.id)

        if profiles:
            index = 0
            if active_id:
                for row, profile in enumerate(profiles):
                    if profile.id == active_id:
                        index = row
                        break
            self.profile_combo.setCurrentIndex(index)
            self.load_profile(profiles[index].id)
        else:
            self.clear_profile_form()
        self._loading_profile = False
        self.refresh_active_profile_label()

    def clear_profile_form(self) -> None:
        self.name_edit.clear()
        self.url_edit.clear()
        self.config_edit.clear()
        self.source_combo.setCurrentIndex(0)

    def current_profile_id(self) -> str | None:
        value = self.profile_combo.currentData()
        return str(value) if value else None

    def current_profile(self) -> Profile | None:
        profile_id = self.current_profile_id()
        return self.store.get_profile(profile_id) if profile_id else None

    def on_profile_selected(self) -> None:
        if self._loading_profile:
            return
        profile_id = self.current_profile_id()
        if not profile_id:
            return
        self.store.set_active_profile_id(profile_id)
        self.load_profile(profile_id)
        self.refresh_active_profile_label()

    def load_profile(self, profile_id: str) -> None:
        profile = self.store.get_profile(profile_id)
        if not profile:
            return
        self.name_edit.setText(profile.name)
        self.url_edit.setText(profile.subscription_url or "")
        self.set_source_type(profile.source_type)
        self.config_edit.setPlainText(self.store.read_config_text(profile.id))
        self.update_source_fields()

    def set_source_type(self, source_type: str) -> None:
        for row in range(self.source_combo.count()):
            if self.source_combo.itemData(row) == source_type:
                self.source_combo.setCurrentIndex(row)
                return
        self.source_combo.setCurrentIndex(0)

    def selected_source_type(self) -> str:
        return str(self.source_combo.currentData() or SOURCE_DIRECT_CONFIG)

    def update_source_fields(self) -> None:
        is_remote = self.selected_source_type() != SOURCE_DIRECT_CONFIG
        self.url_edit.setEnabled(is_remote)

    def create_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Новый профиль", "Имя профиля:")
        if not ok:
            return
        profile = Profile.new(name or "New profile")
        self.store.save_profile(profile, config_text=self.config_edit.placeholderText())
        self.store.set_active_profile_id(profile.id)
        self.refresh_profiles(profile.id)

    def duplicate_profile(self) -> None:
        profile = self.current_profile()
        if not profile:
            return
        new_profile = Profile.new(f"{profile.name} copy", source_type=profile.source_type)
        new_profile.subscription_url = profile.subscription_url
        config_text = self.store.read_config_text(profile.id)
        self.store.save_profile(new_profile, config_text=config_text)
        self.store.set_active_profile_id(new_profile.id)
        self.refresh_profiles(new_profile.id)

    def delete_profile(self) -> None:
        profile = self.current_profile()
        if not profile:
            return
        answer = QMessageBox.question(
            self,
            "Удалить профиль",
            f"Удалить профиль '{profile.name}'?",
        )
        if answer != QMessageBox.Yes:
            return
        self.store.delete_profile(profile.id)
        self.refresh_profiles()

    def save_current_profile(self) -> Profile | None:
        profile = self.current_profile()
        if not profile:
            return None
        profile.name = self.name_edit.text().strip() or profile.name
        profile.source_type = self.selected_source_type()
        profile.subscription_url = self.url_edit.text().strip() or None
        self.store.save_profile(profile, config_text=self.config_edit.toPlainText())
        self.refresh_profiles(profile.id)
        return profile

    def update_from_url(self) -> None:
        profile = self.save_current_profile()
        if not profile:
            return
        try:
            text = self.updater.update_profile(profile)
        except SubscriptionError as exc:
            self.show_error("Ошибка обновления", str(exc))
            return
        self.config_edit.setPlainText(text)
        self.refresh_profiles(profile.id)
        QMessageBox.information(self, "Обновлено", "Подписка обновлена и сохранена.")

    def format_config(self) -> None:
        try:
            data = json.loads(self.config_edit.toPlainText())
        except json.JSONDecodeError as exc:
            self.show_error("Ошибка JSON", str(exc))
            return
        self.config_edit.setPlainText(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def adapt_config_for_linux(self) -> bool:
        try:
            result = adapt_config_for_linux(self.config_edit.toPlainText())
        except json.JSONDecodeError as exc:
            self.show_error("Ошибка JSON", str(exc))
            return False

        if not result.changed:
            QMessageBox.information(
                self,
                "Адаптация",
                "Linux-адаптация не требуется.",
            )
            return False

        self.config_edit.setPlainText(result.text)
        profile = self.save_current_profile()
        message = "Выполнены изменения для Linux:\n\n" + result.summary()
        if profile:
            message += "\n\nПрофиль сохранен."
        QMessageBox.information(self, "Адаптация под Linux", message)
        return True

    def check_current_profile(self) -> bool:
        self._auto_adapt_current_editor()
        profile = self.save_current_profile()
        if not profile:
            return False
        result = self.service.check_config(self.store.config_path(profile.id))
        profile.last_check_status = "ok" if result.ok else "error"
        profile.last_error = None if result.ok else result.output
        self.store.save_profile(profile)

        if result.ok:
            QMessageBox.information(self, "Проверка", "Конфиг прошел проверку.")
            return True

        self.show_error("Проверка не пройдена", result.output or "Unknown error")
        return False

    def apply_current_profile(self) -> None:
        self._auto_adapt_current_editor()
        profile = self.save_current_profile()
        if not profile:
            return

        result = self.service.check_config(self.store.config_path(profile.id))
        if not result.ok:
            self.show_error("Проверка не пройдена", result.output or "Unknown error")
            return

        answer = QMessageBox.question(
            self,
            "Применить профиль",
            (
                f"Применить профиль '{profile.name}' в /etc/sing-box/config.json?\n\n"
                "Текущий системный конфиг будет сохранен в backup."
            ),
        )
        if answer != QMessageBox.Yes:
            return

        deploy = self.service.deploy_config(self.store.config_path(profile.id))
        if not deploy.ok:
            self.show_error("Не удалось применить профиль", deploy.output or "Unknown error")
            return

        restart = QMessageBox.question(
            self,
            "Перезапустить сервис",
            "Профиль применен. Перезапустить sing-box сейчас?",
        )
        if restart == QMessageBox.Yes:
            self.restart_service()
        self.refresh_status()

    def _auto_adapt_current_editor(self) -> None:
        try:
            result = adapt_config_for_linux(self.config_edit.toPlainText())
        except json.JSONDecodeError:
            return
        if result.changed:
            self.config_edit.setPlainText(result.text)

    def refresh_status(self) -> None:
        self._last_state = self.service.state()
        state = self._last_state

        title = {
            "active": "Работает",
            "inactive": "Остановлен",
            "failed": "Ошибка",
            "activating": "Запускается",
            "deactivating": "Останавливается",
        }.get(state.active_state, f"Неизвестно ({state.active_state})")

        self.status_label.setText(f"Статус: {title}")
        self.enabled_label.setText(f"Автозагрузка сервиса: {state.enabled_state}")

        if state.is_active:
            action_text = "Стоп"
            icon_state = "active"
        elif state.is_failed:
            action_text = "Старт"
            icon_state = "failed"
        elif state.active_state in {"activating", "deactivating"}:
            action_text = "Старт"
            icon_state = "pending"
        else:
            action_text = "Старт"
            icon_state = "inactive"

        self.toggle_button.setText(action_text)
        self.toggle_service_action.setText(action_text)
        self.tray.setIcon(self._status_icon(icon_state))
        self.tray.setToolTip(f"sing-box: {title}")
        self.refresh_active_profile_label()

    def refresh_active_profile_label(self) -> None:
        profile = self.store.active_profile()
        text = profile.name if profile else "не выбран"
        self.active_profile_label.setText(f"Активный профиль: {text}")

    def refresh_logs(self) -> None:
        result = self.service.recent_logs()
        if result.ok:
            text = result.stdout.strip() or "Записей в журнале sing-box не найдено."
        else:
            text = result.output or "Не удалось прочитать journalctl."
        self.log_view.setPlainText(text)

    def toggle_service(self) -> None:
        if self._last_state.is_active:
            result = self.service.stop()
        else:
            result = self.service.start()
        if not result.ok:
            self.show_error("Ошибка управления сервисом", result.output or "Unknown error")
        self.refresh_status()
        self.refresh_logs()

    def restart_service(self) -> None:
        result = self.service.restart()
        if not result.ok:
            self.show_error("Ошибка перезапуска", result.output or "Unknown error")
        self.refresh_status()
        self.refresh_logs()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.Trigger,
            QSystemTrayIcon.DoubleClick,
        }:
            self.show_and_raise()

    def show_and_raise(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Singbox GUI",
            "Приложение продолжает работать в трее.",
            QSystemTrayIcon.Information,
            2500,
        )

    def show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def _status_icon(self, state: str) -> QIcon:
        colors = {
            "active": QColor("#22c55e"),
            "inactive": QColor("#94a3b8"),
            "failed": QColor("#ef4444"),
            "pending": QColor("#eab308"),
            "unknown": QColor("#64748b"),
        }
        dot = colors.get(state, colors["unknown"])

        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor("#0f172a"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 13, 13)

        top = QPolygon([QPoint(18, 20), QPoint(32, 12), QPoint(46, 20), QPoint(32, 28)])
        left = QPolygon([QPoint(18, 22), QPoint(32, 30), QPoint(32, 46), QPoint(18, 38)])
        right = QPolygon([QPoint(46, 22), QPoint(32, 30), QPoint(32, 46), QPoint(46, 38)])

        painter.setBrush(QColor("#67e8f9"))
        painter.drawPolygon(top)
        painter.setBrush(QColor("#38bdf8"))
        painter.drawPolygon(left)
        painter.setBrush(QColor("#2563eb"))
        painter.drawPolygon(right)

        painter.setBrush(dot)
        painter.setPen(QColor("#0f172a"))
        painter.drawEllipse(43, 43, 14, 14)
        painter.end()
        return QIcon(pixmap)


def run(argv: list[str]) -> int:
    app = QApplication(argv)
    app.setApplicationName("Singbox GUI")
    app.setQuitOnLastWindowClosed(False)

    store = ProfileStore()
    store.ensure_initial_profile()

    try:
        enable_autostart()
    except OSError:
        pass

    window = MainWindow(store, SingBoxService())
    window.show()
    return app.exec()
