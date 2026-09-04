# Справка DealRocket

Публичная справка по работе с DealRocket. Статьи в [`docs/`](docs/) являются
единым источником правды для сайта и будущего DealRocket Assistant.

- Локальная проверка: `powershell -ExecutionPolicy Bypass -File scripts/check.ps1`
- Локальный просмотр: `powershell -ExecutionPolicy Bypass -File scripts/serve.ps1`
- Публичный адрес: <https://help.dealrocket.ru>
- Машинный корпус: <https://help.dealrocket.ru/assets/help-corpus.v1.json>
- Проверка готовности постоянного домена: `powershell -ExecutionPolicy Bypass -File scripts/check-domain.ps1`

Сайт собирается Material for MkDocs и публикуется GitHub Pages из ветки `main`.
Видео мини-курса встраиваются в статьи через официальный VK Video player и не
копируются в Git-репозиторий как тяжёлые медиафайлы.
