---
name: didox
description: >
  Operate Didox.uz (Uzbekistan e-document exchange) end to end: turn a Word
  draft into a clean PDF, file any document type (акт, договор, ЭСФ
  счёт-фактура, акт сверки, доверенность, письмо) to a counterparty, accept
  or reject incoming documents, cancel sent ones, check signing status, look
  up companies and VAT status by ИНН/TIN, sign with the local E-IMZO key.
  Use when the user says didox / дидокс / didoks / дидокс.уз in any spelling
  or layout, or asks to выставить, подать or отправить акт/договор/СФ
  контрагенту, принять или отклонить входящий документ, проверить подписал
  ли контрагент, найти документ, пробить компанию по ИНН, подписать ЭЦП,
  hujjat yuborish — even if they don't say "Didox". Do NOT use for Russian
  EDO operators (Diadoc, СБИС).
---

# didox — управление Didox.uz через партнёрский API

## Overview

Полный жизненный цикл документов ЭДО: подготовка PDF из docx → черновик
любого типа → подпись E-IMZO → приём/отказ/отмена. CLI `scripts/didox.py`
покрывает партнёрский API, `scripts/eimzo_sign.py` — мост к локальному
E-IMZO. Вывод — JSON в stdout; ошибка — JSON в stderr, exit 1.

Что обратимо, а что нет: черновик удаляется (`draft-delete`); подпись,
приём, отказ и отмена — юридические действия, назад не отматываются.

## Pre-flight

→ `references/runtime-setup.md`. Если чего-то нет (python3, env-файл с
токенами, живой логин) — стоп, сказать пользователю, что именно и где взять.
Перед первой подписью проверь `profile` → `offerSigned: 1` (оферта Didox);
не подписана — маршрут в `references/api-details.md` § Оферта.

## Команды

| Задача | Команда |
|---|---|
| Получить/обновить user-токен | `scripts/didox.py login` |
| Свои реквизиты | `scripts/didox.py profile` |
| Документы по контрагенту | `scripts/didox.py docs --partner <ИНН>` |
| Черновики / входящие | `scripts/didox.py docs --status 0` / `docs --owner 0` |
| Карточка / печатная форма | `scripts/didox.py doc <ID>` / `doc-pdf <ID> <out.pdf>` |
| Компания по ИНН | `scripts/didox.py partner <ИНН>` |
| Произвольный документ с PDF | `scripts/didox.py draft-000 …` → см. ниже |
| Черновик любого типа (ЭСФ, акт 005, договор 007…) | `scripts/didox.py create <doctype> payload.json` |
| Обновить черновик | `scripts/didox.py draft-update <ID> <doctype> payload.json` |
| Удалить черновик | `scripts/didox.py draft-delete <ID>` |
| Подписать исходящий | `scripts/didox.py sign <ID> --serial <serial>` |
| Принять входящий | `scripts/didox.py accept <ID> --serial <serial>` |
| Отклонить входящий | `scripts/didox.py reject <ID> --serial <serial> --comment "…"` |
| Отменить отправленный | `scripts/didox.py cancel <ID> --serial <serial>` |
| Любой эндпоинт | `scripts/didox.py raw GET\|POST '<path>' ['<json>']` |

Токен кэшируется на 6 часов и обновляется сам. Полный справочник эндпоинтов,
фильтров, статусов по семействам типов, профиля, каталогов и маршрутов →
`references/api-details.md`. Структуры JSON для `create` →
`references/document-types.md`. API недоступен — подача руками через кабинет
didox.uz: `references/browser-fallback.md`.

## Подача документа (draft-000 / create)

Перед созданием черновика проверь:

- [ ] Договор, на который ссылается документ, существует в Didox и подписан
      обеими сторонами (`docs --partner <ИНН>`, статус 3). Номер и дата — из
      этой выдачи, не из локального docx: расхождение означает, что docx
      устарел, а акт к несуществующему договору контрагент отклонит.
- [ ] Реквизиты сторон — из API (`profile`, `partner <ИНН>`), не из памяти
      и не из docx: налоговая база первична, по ней контрагент сверяет.
- [ ] Для 000: PDF чистый (раздел «Из docx в PDF»); подтип по таблице в
      `references/document-types.md` (акт → 5, договор → 3, приложения → 9).
- [ ] Для роуминговых типов (002/005/007/041): payload собран по
      `references/document-types.md`, правила роуминга соблюдены (null вместо
      пустых объектов, даты yyyy-MM-dd, точность чисел) — принимающая сторона
      валидирует строго и отклоняет молча непонятными ошибками.

```bash
scripts/didox.py draft-000 \
  --number "<номер>" --date <YYYY-MM-DD> \
  --buyer-tin <ИНН> --subtype <код> \
  --name "<полное название документа>" \
  --contract-no <номер договора> --contract-date <YYYY-MM-DD> \
  --pdf <файл.pdf>
```

После создания проверь: `docs --partner <ИНН> --status 0`.

## Из docx в PDF

Договор или акт обычно приходит в .docx с правками и комментариями юриста.
Подавать такой файл нельзя: зачёркнутый текст и выноски попадут в подписанный
документ.

```bash
scripts/clean_docx.py <in.docx> <clean.docx>   # принять правки, убрать комментарии
scripts/docx_to_pdf.sh <clean.docx> <out.pdf>  # pandoc + weasyprint, без Word и GUI
```

`clean_docx.py` печатает `ok … ins=0 del=0 comments=0` и падает, если правки
остались. Перед подачей открой PDF и глянь первую и последнюю страницы: нет
зачёркиваний, нет выносок, реквизиты на месте. Комментарии юриста прочитай ДО
чистки (`references/docx-prep.md`) — после чистки они исчезают безвозвратно.

Имя файла латиницей (`Akt_1_k_Dogovoru_<номер>.pdf`). Один документ = один
PDF: договор и приложения не склеивать.

## Подпись и юридические действия — только по команде пользователя

Подпись ставит ЭЦП-ключ через приложение E-IMZO на машине пользователя
(`scripts/eimzo_sign.py`, CAPIWS `ws://127.0.0.1:64646`). Пароль ключа
вводится в окне E-IMZO — CLI его не видит и не хранит.

```bash
scripts/eimzo_sign.py keys              # ключи: serial, ИНН, срок действия
scripts/didox.py sign <ID> --serial <serial>            # собрать подпись, НЕ отправлять
scripts/didox.py sign <ID> --serial <serial> --submit   # отправить
```

Без `--submit` команды `sign`/`accept`/`reject`/`cancel` только формируют
подпись и подтверждают готовность. `--submit` — только по явной команде
пользователя на конкретный документ: подпись ЭЦП юридически равна
собственноручной и необратима, отказ и отмена меняют состояние у контрагента.
Сам, «чтобы проверить», не отправлять. Рационализации, все — стоп:
«пользователь же хочет, чтобы ушло», «тестовый, подпишу и удалю» (подписанное
не удаляется), «ключ его — значит можно». Тестировать полный цикл — только
на песочнице testapi3 тестовым ключом.

## Common Mistakes

| Ошибка | Что вместо |
|---|---|
| Номер договора взят из локального docx | Номер из `docs` (подписанный, статус 3) |
| Реквизиты сторон набраны руками | `profile` / `partner <ИНН>` из налоговой базы |
| Тестовый черновик оставлен в системе | Номер `TEST-…` + сразу `draft-delete` |
| Подтип «Другое» для приложений к договору | 9 «Доп. соглашение» |
| Статус письма 3 прочитан как «подписан» | Статусы зависят от типа → api-details |
| `--partner` не сузил выдачу — взят чужой документ | Сверить `partnerTin` с ИНН контрагента |
| В payload СФ пустые объекты `{}` вместо null | Правила роуминга → document-types |
| Секреты в аргументах команд или в git | Только env-файл, см. runtime-setup |
| Договор и приложения склеены в один PDF | Два документа — два черновика |
| Открыт Microsoft Word для конвертации | `scripts/docx_to_pdf.sh` — без GUI |
