---
name: didox-cli
description: >
  Operate Didox.uz (Uzbekistan e-document exchange) through its partner API
  via the bundled didox.py CLI: list documents and check signing status, look
  up companies by ИНН/TIN, create document drafts with PDF attachments,
  download print forms, delete drafts. Use when the user says didox / дидокс /
  didoks / дидокс.уз in any spelling or layout, or asks to выставить, подать
  or отправить акт/договор/приложение контрагенту, проверить подписал ли
  контрагент, найти документ, пробить компанию по ИНН, hujjat yuborish —
  even if they don't say "Didox". Do NOT use for signing documents (E-IMZO
  key, the user signs), for Russian EDO operators (Diadoc, СБИС), or for
  docx→PDF preparation with no filing.
---

# didox-cli — управление Didox через партнёрский API

## Overview

CLI `scripts/didox.py` покрывает партнёрский API Didox: документы, контрагенты,
черновики. Вывод — JSON в stdout; ошибка — JSON в stderr, exit 1. Черновик
обратим (`draft-delete`), подпись — нет: её делает пользователь ключом E-IMZO.

## Pre-flight

→ `references/runtime-setup.md`. Если чего-то нет (python3, env-файл с
токенами, живой логин) — стоп, сказать пользователю, что именно и где взять.

## Команды

| Задача | Команда |
|---|---|
| Получить/обновить user-токен | `scripts/didox.py login` |
| Свои реквизиты | `scripts/didox.py profile` |
| Документы по контрагенту | `scripts/didox.py docs --partner <ИНН>` |
| Черновики | `scripts/didox.py docs --status 0` |
| Входящие | `scripts/didox.py docs --owner 0` |
| Карточка документа | `scripts/didox.py doc <DOC_ID>` |
| Печатная форма PDF | `scripts/didox.py doc-pdf <DOC_ID> <out.pdf>` |
| Компания по ИНН | `scripts/didox.py partner <ИНН>` |
| Черновик с PDF | `scripts/didox.py draft-000 …` → см. ниже |
| Удалить черновик | `scripts/didox.py draft-delete <DOC_ID>` |
| Прямой вызов эндпоинта | `scripts/didox.py raw GET\|POST '<path>' ['<json>']` |

Токен кэшируется на 6 часов и обновляется сам; `login` руками нужен только
после смены пароля. Справочники подтипов и статусов, формат payload и полный
маршрут «подать акт» → `references/api-details.md`.

## Подача документа (draft-000)

Перед созданием черновика проверь:

- [ ] Договор, на который ссылается документ, существует в Didox и подписан
      обеими сторонами (`docs --partner <ИНН>`, статус 3). Номер и дата — из
      этой выдачи, не из локального docx: расхождение означает, что docx
      устарел, а акт к несуществующему договору контрагент отклонит.
- [ ] PDF чистый: без правок, выносок и пустых полей (подготовка docx→PDF —
      скилл didox).
- [ ] Подтип выбран по таблице в `references/api-details.md` (акт → 5,
      договор → 3, приложения → 9).

```bash
scripts/didox.py draft-000 \
  --number "<номер документа>" --date <YYYY-MM-DD> \
  --buyer-tin <ИНН контрагента> --subtype <код> \
  --name "<полное название документа>" \
  --contract-no <номер договора> --contract-date <YYYY-MM-DD> \
  --pdf <файл.pdf>
```

Реквизиты продавца CLI берёт из профиля, покупателя — из налоговой базы по
ИНН. После создания проверь результат: `docs --partner <ИНН> --status 0`.

## Подпись — только пользователь

Эндпоинты подписи (`sign`, `tosign`, `accept`) не вызывать, в том числе через
`raw`. Подпись ЭЦП юридически равна собственноручной: вызов создаёт
обязательства компании, и «проверить, как работает sign» на проде — это
подписанный документ, который нельзя отозвать. Финал работы CLI — черновик;
дальше пользователь жмёт «Подписать» в кабинете didox.uz.

Типичные рационализации, все — стоп-сигнал: «пользователь явно хочет, чтобы
документ ушёл», «это тестовый документ, подпишу и удалю» (подписанное не
удаляется), «токен же мой, значит можно».

## Common Mistakes

| Ошибка | Что вместо |
|---|---|
| Номер договора взят из локального docx | Номер из `docs` (подписанный, статус 3) |
| Тестовый черновик оставлен в системе | Номер `TEST-…` + сразу `draft-delete` |
| Подтип «Другое» для приложений к договору | 9 «Доп. соглашение» (таблица в api-details) |
| `--partner` не сузил выдачу — взят чужой документ | Сверить `partnerTin` в ответе с ИНН контрагента |
| Секреты в аргументах команд или в git | Только env-файл, см. runtime-setup |
