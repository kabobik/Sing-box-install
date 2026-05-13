# singbox-gui

Небольшой Linux GUI для управления установленным `sing-box.service`.

Текущий статус: ранний MVP.

## Возможности MVP

- tray icon со статусом сервиса;
- старт, стоп и рестарт `sing-box.service`;
- просмотр последних записей журнала из `journalctl`;
- локальные профили в `~/.config/singbox-gui`;
- профиль из прямого JSON;
- профиль из URL, который отдает готовый sing-box JSON;
- адаптация Android-зависимых и опасных для Linux TUN-полей;
- проверка через `sing-box check`;
- применение профиля в `/etc/sing-box/config.json` после подтверждения;
- автозапуск GUI через `~/.config/autostart`.

## Запуск из исходников

```bash
scripts/install_dev_deps.sh
scripts/install_polkit_helper.sh
scripts/run_dev.sh
```

`scripts/install_dev_deps.sh` создает локальный `.venv` внутри проекта и ставит `PySide6`.
`scripts/install_polkit_helper.sh` ставит root-helper и PolicyKit action. Этот шаг один раз
спросит пароль через `sudo`, зато дальше GUI сможет применять конфиг и управлять
`sing-box.service` без запроса пароля для активного локального пользователя.

## Важное

GUI не запускает отдельный `sing-box`, а управляет системным сервисом `sing-box.service`.
Для применения конфига и управления сервисом используется узкий PolicyKit helper:

```text
/usr/local/libexec/singbox-gui-helper
/usr/share/polkit-1/actions/org.singbox.gui.policy
```

Helper разрешает только ограниченный набор действий:

- применить проверенный конфиг в `/etc/sing-box/config.json`;
- сделать backup текущего конфига в `/etc/sing-box/backups`;
- выполнить `start`, `stop`, `restart` только для `sing-box.service`.

Если helper не установлен, GUI использует старый fallback через `pkexec`, и система снова
может спросить пароль.

## Сборка deb-пакета

```bash
scripts/install_dev_deps.sh
scripts/build_deb.sh
sudo apt install ./dist/singbox-gui_0.1.0_amd64.deb
```

Пакет кладет файлы так:

```text
/opt/singbox-gui/src
/opt/singbox-gui/venv
/usr/bin/singbox-gui
/usr/lib/singbox-gui/singbox-gui-helper
/usr/share/polkit-1/actions/org.singbox.gui.policy
/usr/share/applications/singbox-gui.desktop
/usr/share/icons/hicolor/scalable/apps/singbox-gui.svg
```

Права применяются в `postinst`:

- `/usr/lib/singbox-gui/singbox-gui-helper`: `root:root`, `0755`;
- `/usr/share/polkit-1/actions/org.singbox.gui.policy`: `root:root`, `0644`;
- `/usr/bin/singbox-gui`: `root:root`, `0755`.

После установки GUI вызывает helper через `pkexec`, но PolicyKit action разрешает это
активному локальному пользователю без запроса пароля.

## Адаптация конфигов под Linux

Некоторые подписки отдают конфиг для Android-клиента. Например, поле
`route.override_android_vpn` поддерживается только на Android и ломает запуск
Linux-сервиса.

GUI удаляет такие известные Android-only поля при обновлении URL-профиля, а
также перед проверкой и применением.

Также GUI отключает `strict_route` в TUN inbound, если профиль одновременно
использует `auto_redirect=true` и привязку outbound-интерфейса через
`route.auto_detect_interface` или `route.default_interface`. На Linux такая
комбинация может завернуть собственные outbound-подключения sing-box обратно в
TUN и привести к таймаутам proxy/DNS.

В профиле есть отдельная кнопка `Адаптировать под Linux`, чтобы выполнить это
вручную и увидеть список изменений.
