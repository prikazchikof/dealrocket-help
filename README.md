# Справка DealRocket

Публичная справка по работе с DealRocket. Статьи в [`docs/`](docs/) являются
единым источником правды для сайта и будущего DealRocket Assistant.

- Локальная проверка: `powershell -ExecutionPolicy Bypass -File scripts/check.ps1`
- Локальный просмотр: `powershell -ExecutionPolicy Bypass -File scripts/serve.ps1`
- Публичный адрес: <https://help.dealrocket.ru>
- Машинный корпус: <https://help.dealrocket.ru/assets/help-corpus.v1.json>
- Компактный чат: launcher на всех страницах загружает
  <https://support.dealrocket.ru/widget> только после первого открытия.
- Проверка готовности постоянного домена: `powershell -ExecutionPolicy Bypass -File scripts/check-domain.ps1`

Сайт собирается Material for MkDocs и публикуется GitHub Pages из ветки `main`.
Перед загрузкой Pages artifact CI проверяет `/widget`, строгий CSP, assets и
создание отдельной widget-сессии. Локальный сквозной smoke:
`..\dealrocket-support\.venv\Scripts\python.exe scripts\browser_widget_smoke.py`.
Видео мини-курса встраиваются в статьи через официальный VK Video player и не
копируются в Git-репозиторий как тяжёлые медиафайлы.
