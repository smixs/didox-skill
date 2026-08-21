---
name: didox-cli
description: >
  Operate the Didox.uz EDO platform through its partner API using the didox.py
  CLI: list and inspect documents, look up counterparties by TIN, create
  arbitrary-document drafts (contracts, acts, appendices) with PDF attachments,
  download print forms, delete drafts. Use when the user asks to find or file
  documents in Didox, check a document's signing status, look up a company by
  ИНН, or submit an act/contract to a counterparty via ЭДО — and a partner
  token is configured. Prefer this over browser automation of didox.uz.
  Do NOT use for signing (E-IMZO key required — the user signs), or for
  Russian EDO operators (Diadoc, СБИС).
---

# didox-cli — управление Didox через API

## Setup

CLI: `didox.py` (лежит рядом с этим скиллом). Конфиг ищется в `./.env`,
`~/.didox/env` или `--env PATH`. Обязательные переменные: `DIDOX_PARTNER_TOKEN`,
`DIDOX_TIN`, `DIDOX_PASSWORD`. Опционально `DIDOX_URL` (по умолчанию прод
`https://api-partners.didox.uz`; тестовый стенд — `https://testapi3.didox.uz`).

Первый вызов: `./didox.py login` — получает user-токен (живёт 360 минут,
кэшируется в `~/.didox/`). Остальные команды сами переиспользуют кэш и
перелогиниваются при протухании. Если `login` падает с `Incorrect login` —
пароль аккаунта не задан или сменился: пользователь задаёт его на didox.uz →
Профиль → Аккаунт. Не проси пароль в чат — пусть пользователь сам положит его
в env-файл.

## Команды

Весь вывод — JSON в stdout. Ошибка — JSON в stderr, exit 1.

| Задача | Команда |
|---|---|
| Кто я / свои реквизиты | `./didox.py profile` |
| Документы по контрагенту | `./didox.py docs --partner <ИНН>` |
| Черновики | `./didox.py docs --status 0` |
| Входящие | `./didox.py docs --owner 0` |
| Карточка документа | `./didox.py doc <DOC_ID>` |
| Печатная форма PDF | `./didox.py doc-pdf <DOC_ID> out.pdf` |
| Компания по ИНН | `./didox.py partner <ИНН>` |
| Черновик 000 с PDF | `./didox.py draft-000 …` (см. ниже) |
| Удалить черновик | `./didox.py draft-delete <DOC_ID>` |
| Любой эндпоинт | `./didox.py raw GET\|POST '<path>' ['<json>']` |

## Подача документа (черновик 000 + PDF)

```bash
./didox.py draft-000 \
  --number "1" --date 2026-08-21 \
  --buyer-tin 207151159 \
  --subtype 5 \
  --name "Акт № 1 сдачи-приемки оказанных услуг к Договору № 19062026 от 19.06.2026" \
  --contract-no 19062026 --contract-date 2026-06-19 \
  --pdf /path/to/act.pdf
```

Реквизиты продавца CLI берёт сам из профиля, покупателя — из налоговой базы
по ИНН. PDF ≤ 10 МБ, один файл на документ. Даты в формате `YYYY-MM-DD`.

Подтипы (Subtype): `2` Письмо · `3` Договор · `5` Акт выполненных работ ·
`6` Другое · `8` Спецификация · `9` Доп. соглашение.
Правила выбора — как в браузерном скилле didox: договор → 3, приложения к
договору → 9 (не «Другое», не «Спецификация»), акт → 5.

Статусы (`doc_status`): `0` черновик · `1` подписан нами, ждёт партнёра ·
`3` подписан обеими · `4` отказ.

## Рабочий цикл «подать акт контрагенту»

1. `docs --partner <ИНН>` — проверить, что договор в статусе 3 (подписан), и
   взять его номер/дату для ссылки в акте.
2. Подготовить чистый PDF акта (docx → PDF: см. скилл didox, скрипты
   `clean_docx.py` и `docx_to_pdf.sh`).
3. `draft-000` с `--subtype 5` и `--contract-no/--contract-date` подписанного
   договора.
4. `docs --partner <ИНН> --status 0` — убедиться, что черновик создан.
5. Сказать пользователю подписать: кабинет didox.uz → Черновики → документ →
   «Подписать» (E-IMZO). CLI подписи не делает.

## Guardrails

- Проверяй перед созданием: номер договора в акте = номер РЕАЛЬНО подписанного
  в Didox договора (статус 3), а не локального docx. Расхождение — стоп, спроси.
- Черновик безвреден (можно `draft-delete`), но НЕ вызывай никакие sign/accept
  эндпоинты через `raw` — подпись юридически значима, её делает пользователь.
- Тестовые прогоны — с номером вида `TEST-…` и немедленным `draft-delete`.
- Токены и пароли: только env-файлы (chmod 600), в чат и в git не попадают.
