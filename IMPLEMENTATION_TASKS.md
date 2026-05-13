# Задачи реализации GUI для sing-box

## Текущее состояние

- Код MVP создан.
- Синтаксис модулей проходит `python3 -m compileall src`.
- Non-GUI слой проверен с `SINGBOX_GUI_CONFIG_DIR=/tmp/singbox-gui-check`.
- `PySide6` установлен в локальный `.venv`.
- GUI прошел offscreen smoke-test: `QApplication` и `MainWindow` создаются.
- Добавлен Linux-адаптер конфига для Android-only полей.
- Добавлен root-owned PolicyKit helper для управления `sing-box.service` без пароля после установки.
- No-password flow проверен через `pkexec --disable-internal-agent`.
- Тестовое применение копии текущего конфига через helper прошло успешно.
- Добавлен сборщик `.deb` пакета с bundled `.venv`.
- Для запуска из исходников: `bash scripts/run_dev.sh`.

## Milestone 0. Подготовка

- [x] Зафиксировать продуктовый план.
- [x] Разбить проект на рабочие задачи.
- [x] Проверить доступность PySide6 или подготовить команду установки.

## Milestone 1. Каркас приложения

- [x] Создать Python-проект с `pyproject.toml`.
- [x] Добавить пакет `singbox_gui`.
- [x] Добавить entrypoint `python -m singbox_gui`.
- [x] Добавить базовую иконку-коробочку.
- [x] Добавить главное окно и tray icon.

## Milestone 2. Сервисный слой

- [x] Обертка над `systemctl is-active`.
- [x] Обертка над `systemctl is-enabled`.
- [x] Обертки `start`, `stop`, `restart` через PolicyKit helper.
- [x] Чтение последних ошибок через `journalctl`.
- [x] Проверка конфига через `sing-box check`.

## Milestone 3. Профили

- [x] Хранилище в `~/.config/sing-box-gui`.
- [x] Модель профиля с именем, типом источника, URL и метаданными.
- [x] Создание профиля.
- [x] Сохранение профиля.
- [x] Удаление профиля.
- [x] Выбор активного профиля.
- [x] Импорт текущего `/etc/sing-box/config.json` при первом запуске.

## Milestone 4. Подписки

- [x] URL-профиль с готовым sing-box JSON.
- [x] Ручное обновление URL.
- [x] Plain-text хранение URL в `~/.config/sing-box-gui`.
- [x] Удаление известного Android-only поля `route.override_android_vpn`.
- [ ] Автообновление по расписанию.
- [ ] Дополнительные параметры `allow insecure`, `User-Agent`, `update through proxy`.
- [ ] Адаптеры для base64/proxy URI.
- [ ] Адаптер Clash/Mihomo YAML или внешний конвертер.

## Milestone 5. Применение

- [x] Проверка профиля перед применением.
- [x] Диалог подтверждения перед применением.
- [x] Привилегированный helper для копирования в `/etc/sing-box/config.json`.
- [x] Backup старого `/etc/sing-box/config.json`.
- [x] Отдельное подтверждение перезапуска сервиса.
- [ ] Кнопка отката к предыдущему backup.

## Milestone 6. Автозапуск и упаковка

- [x] Генерация `.desktop` файла для `~/.config/autostart`.
- [x] Автовключение автозапуска при старте GUI.
- [x] Install script для PolicyKit helper.
- [x] `.deb` packaging.
- [x] PolicyKit action для helper после упаковки.

## Milestone 7. Полировка

- [ ] Улучшить визуальный стиль.
- [ ] Live-tail логов.
- [ ] Тест соединения.
- [ ] Выбор узлов внутри подписки.
- [ ] Переводы ru/en.
