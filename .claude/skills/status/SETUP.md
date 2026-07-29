# Настройка навыка `/status` (Discord-статусы)

Навык `/status` уже установлен в репозитории — нужно только **один раз настроить**
Discord-вебхуки под себя. Секреты хранятся локально и в git не попадают.

> **Проще всего:** запусти `>_ Claude` (кнопка вверху справа в CAD UI) и скажи:
> **«настрой status по SETUP.md»** — Claude проведёт по шагам, спросит вебхуки и впишет
> их сам. Ниже — те же шаги, если делаешь вручную.

---

## Что понадобится

- **Доступ к Discord** с правом создавать вебхуки в нужных каналах.
- **Python из `.venv`** — ставится при первом `start.bat` (навык использует только stdlib).
- **Claude Code** — опционально: нужен для авто-черновиков «Трек» (3-часовой тик) и для
  брендированных PDF (агент `cvd-docs`). Ручная отправка статусов работает и без него.

---

## Шаг 1 — Файл конфигурации

Скопируй пример в **корень репозитория** под именем `workspace.config.json`:

```
copy config.example.json workspace.config.json
```

В нём есть блок `status` — с ним и работаем. Файл **в `.gitignore`** — в него можно
безопасно писать секреты, в общий репозиторий он не уедет.

## Шаг 2 — Создай вебхуки в Discord

Для каждого канала: **настройки канала → Integrations → Webhooks → New Webhook → Copy
Webhook URL**. Понадобятся:
- **status** — общий канал (начало/конец дня, присутствие) — обязательно;
- **summary** — канал «Итоги дня» (опционально; если не нужен — оставь плейсхолдер);
- по одному вебхуку **на каждый проект**, чей трек шлём в отдельный канал.

## Шаг 3 — Заполни блок `status`

В `workspace.config.json` → `status`:
- вставь URL в `status_webhook`, `summary_webhook` и в `projects.<key>.webhook`;
- задай `username` / `summary_username` (имя бота в Discord);
- у каждого проекта `path` = папка проекта, обычно `Working directory/<key>` (по этому
  пути навык сопоставляет твою рабочую папку с каналом);
- **убери плейсхолдеры**: любой URL со словом `REPLACE` считается незаполненным, и навык
  честно откажется слать, а не отправит «в никуда».

Пример заполненного проекта:
```json
"projects": {
  "ai-deep-dive": {
    "name": "Ai deep dive",
    "path": "Working directory/ai-deep-dive",
    "webhook": "https://discord.com/api/webhooks/…",
    "username": "Ai deep dive status"
  }
}
```

## Шаг 4 — Проверь, что работает

Из корня репозитория:
```
.venv\Scripts\python .claude\skills\status\send_status.py --channel status "тест"
```
Ожидаешь `Sent. id=…` и сообщение в Discord. Убери тест:
```
.venv\Scripts\python .claude\skills\status\send_status.py --channel status --delete-last
```

## Шаг 5 — Проекты

Проект можно добавить руками в `projects` (Шаг 3) — или навык сам зарегистрирует его при
`/status → Задание → Старт задания` (спросит вебхук и впишет в конфиг). Трек-файлы навык
пишет в `Working directory/<project>/track/`, и они **сразу видны в разделе «Проекты»** CAD UI.

## Шаг 6 (опционально, Windows) — автоматика по расписанию

Три задачи Task Scheduler: авто-«Начало дня» (09:00), авто-«Конец дня» + черновик итогов
(22:00), черновики «Трек» (12/15/18/21):
```
powershell -ExecutionPolicy Bypass -File .claude\skills\status\register_tasks.ps1
```
Своё расписание: `… register_tasks.ps1 -StartTime 08:30 -EndTime 21:00`. Убрать всё:
`… register_tasks.ps1 -Remove`.

Ограничения: **только Windows**; задачи срабатывают лишь когда компьютер включён (планировщик
его не будит); тику и PDF нужен рабочий `claude` в PATH.

---

## Безопасность

- Вебхуки — **секреты**. Они живут только в `workspace.config.json` (git-ignored) и в
  `.cad-ui/status/` (runtime-состояние, тоже git-ignored). **Никогда** не коммить их и не
  вписывай в отслеживаемые файлы.
- Проверка, что ничего не утекает:
  ```
  git check-ignore workspace.config.json .cad-ui/status
  ```
  (обе строки должны вернуться — значит игнорируются). В коммит из этого навыка идёт только
  код `.claude/skills/status/**`, без секретов.

## Если что-то не так

- `workspace.config.json not found` / `has no 'status' object` → не сделан Шаг 1/3.
- Ошибка про `REPLACE` → соответствующий вебхук ещё не заполнен (Шаг 3).
- `claude ... not found` (в тике/PDF) → поставь Claude Code или пропиши путь в
  `claude_command` (верхний ключ `workspace.config.json`); ручная отправка это не затрагивает.

---

## Если ты Claude и тебя попросили «настроить status»

Веди пользователя по шагам этого файла:
1. Убедись, что есть `workspace.config.json` (иначе скопируй из `config.example.json`).
2. Спроси, какие каналы нужны (status обязателен; summary и проекты — по желанию), и
   попроси прислать соответствующие webhook-URL.
3. Впиши их в блок `status` — **никогда не показывай URL обратно** в чат и не клади в
   отслеживаемые файлы; только в `workspace.config.json`.
4. Предложи тест (`send_status.py --channel status "тест"` → затем `--delete-last`).
5. Спроси, нужна ли Windows-автоматика; если да — запусти `register_tasks.ps1`.
6. Перед завершением проверь `git status`: секретов в staged быть не должно.
