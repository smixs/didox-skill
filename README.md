# didox-cli

CLI для партнёрского API [Didox.uz](https://didox.uz) — узбекского оператора ЭДО.
Один файл, Python 3.8+, ноль зависимостей. Сделан для AI-агентов и людей:
весь вывод — JSON, ошибки — в stderr с кодом 1.

## Возможности

- Логин по паролю аккаунта Didox (user-токен кэшируется на 6 часов)
- Список документов с фильтрами (контрагент, тип, статус, страницы)
- Карточка документа, печатная форма в PDF
- Данные любой компании по ИНН из налоговой базы
- Создание черновика «Произвольный документ» (000) с PDF-вложением
- Удаление черновиков
- `raw` — прямой вызов любого эндпоинта API

Подписание (E-IMZO) намеренно не включено: подпись юридически значима
и требует ключ ЭЦП. См. раздел «Подписание» ниже.

## Структура

```
didox-cli/            # скилл для AI-агентов (Claude Code и совместимые)
├── SKILL.md          # инструкция агенту
├── scripts/didox.py  # сам CLI (один файл, stdlib)
└── references/       # pre-flight, справочники API
```

## Установка

CLI: скопируйте `didox-cli/scripts/didox.py` куда угодно — нужен только Python 3.8+.

Скилл для Claude Code: `cp -R didox-cli ~/.claude/skills/`

## Настройка

Env-файл (`./.env` рядом, `~/.didox/env`, или путь через `--env`):

```
DIDOX_PARTNER_TOKEN=<партнёрский JWT от аккаунт-менеджера Didox>
DIDOX_TIN=<ИНН вашей компании>
DIDOX_PASSWORD=<пароль аккаунта Didox>
# необязательно:
DIDOX_URL=https://api-partners.didox.uz   # или https://testapi3.didox.uz
```

Партнёрский токен выдаёт аккаунт-менеджер Didox: https://t.me/Didox_account.
Пароль аккаунта задаётся в личном кабинете didox.uz → Профиль → Аккаунт.

## Команды

```bash
didox-cli/scripts/didox.py login                        # получить и закэшировать user-токен
didox-cli/scripts/didox.py profile                      # реквизиты своей компании
didox-cli/scripts/didox.py docs --partner 207151159     # документы по контрагенту
didox-cli/scripts/didox.py docs --status 0              # черновики
didox-cli/scripts/didox.py doc <DOC_ID>                 # карточка документа
didox-cli/scripts/didox.py doc-pdf <DOC_ID> out.pdf     # печатная форма
didox-cli/scripts/didox.py partner <ИНН>                # данные компании из налоговой базы
didox-cli/scripts/didox.py draft-000 --number 1 --date 2026-08-21 \
    --buyer-tin 207151159 --subtype 5 \
    --name "Акт № 1 к Договору № X" \
    --contract-no X --contract-date 2026-06-19 \
    --pdf act.pdf                       # черновик произвольного документа
didox-cli/scripts/didox.py draft-delete <DOC_ID>        # удалить черновик
didox-cli/scripts/didox.py raw GET '/v2/documents?limit=5'   # любой эндпоинт
```

## Справочники (наблюдённые значения)

Подтипы произвольного документа (000): `2` Письмо · `3` Договор ·
`5` Акт выполненных работ · `6` Другое · `8` Спецификация · `9` Доп. соглашение.

Статусы документов: `0` черновик · `1` подписан отправителем, ждёт партнёра ·
`3` подписан обеими сторонами · `4` отказ от подписи.

## Подписание

Документ 000 виден только контрагентам внутри Didox (не уходит в роуминг
к другим операторам ЭДО). Подпись выполняется ключом E-IMZO:

- вручную в кабинете didox.uz (кнопка «Подписать»), либо
- программно: `POST /v1/documents/:docId/sign` с PKCS7-подписью,
  сформированной локальным E-IMZO (CAPIWS, `ws://127.0.0.1:64443`).
  Мост для этого — в планах.

## Лицензия

MIT
