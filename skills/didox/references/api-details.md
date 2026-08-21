# API: полный справочник

Источник: официальная дока api-docs.didox.uz (11 разделов, прочитаны целиком
21.08.2026) + наблюдения живого API. При расхождении верить живому API и
обновлять этот файл. Канал изменений API: t.me/didoxapiupdates.

Все запросы: заголовок `Partner-Authorization: <партнёрский токен>`; все
содержательные — ещё `user-key: <токен пользователя>`.

## Стенды

| Стенд | URL | Особенность |
|---|---|---|
| Прод | `api-partners.didox.uz` | Partner-Authorization + user-key |
| Партнёрский dev | `stage.goodsign.biz` | «тестовая URL» из шапки доки |
| Песочница | `testapi3.didox.uz` | принимает user-key БЕЗ партнёрского токена; ЭЦП — тестовый ключ с my3.soliq.uz |

## Аутентификация

| Способ | Эндпоинт | Что нужно |
|---|---|---|
| Пароль аккаунта | `POST /v1/auth/{tin}/password/ru` `{password}` | пароль (didox.uz → Профиль → Аккаунт) |
| ЭЦП | `POST /v1/auth/{tin}/token/ru` `{signature}` | подписать ИНН (base64) → timestamp → timeStampTokenB64 |
| Вход в компанию | `POST /v1/auth/company/{companyTin}/login/ru` + `user-key` физлица | физлицо входит в контекст компании |
| Регистрация нового | `POST /v1/auth/signup` `{signature, email, password, mobile}` | подписанный ИНН + timestamp |

Токен — UUID, живёт 360 минут. Логин рейт-лимитится (429 после нескольких
неудач) — токен кэшировать, не логиниться на каждый запрос. `Authorization:
Bearer` API не принимает — только заголовок `user-key`.

## Оферта — гейт перед первой подписью

Перед первым подписанием у пользователя должна быть подписана публичная
оферта Didox, иначе `/sign` вернёт `{"message": "Оферта не подписана"}`.
Проверка: `profile` → поле `offerSigned` (1 = подписана). Подписание оферты:
`GET /v1/newoffer/base64` (PDF) → `POST /v1/documents/offer/create`
`{document: "<PDF base64>"}` → подписать `document_json` из ответа обычным
флоу → `POST /v1/documents/offer/sign` `{signature}`.

## Документы: чтение

| Эндпоинт | Что |
|---|---|
| `GET /v2/documents?page=&limit=` | список; limit ≤ 100, page и limit обязательны |
| `GET /v2/documents/statistics/all` | счётчики по статусам (те же фильтры) |
| `GET /v1/documents/{id}?owner=1\|0` | карточка: `data.json` (содержимое), `data.document` (метаданные, подписи), `data.toSign`, `data.relatedDocuments` |
| `GET /v1/documents/{id}/privileges/ru` | льготы в документе |
| `GET /v1/documents/view/{id}/html\|pdf/ru` | печатная форма (с проверкой прав пользователя) |
| `GET /v1/documents/{id}/html\|pdf/ru` | печатная форма БЕЗ user-key (только партнёрский токен) |
| `GET /v1/documents/{id}/file/true/ru` | PDF в base64 + page_count_without_act |
| `GET /v1/documents/{id}/archive` | ZIP: подписи + PDF + JSON |
| `GET /v1/documents/{id}/documentBase64` | base64 документа (для подписи входящего) |

Фильтры списка: `owner` (1 исходящие/0 входящие), `status` (через запятую),
`doctype`, `partner` (ИНН), `name` (номер), `sum`, `contractName`,
`contractDate`, диапазоны дат `dateFrom/ToCreated`, `dateFrom/ToUpdated`,
`signDateFrom/To`, `docDateFrom/ToCreated` (все `yyyy-mm-dd`), флаги
`hasCommittent`, `hasLgota`, `hasMarks`, `oneside`. Без `status` возвращаются
только 1, 2, 3, 4, 6, 8, 40 — черновики (0) и удалённые в общей выдаче не видны.

## Документы: создание и изменение

| Эндпоинт | Что |
|---|---|
| `POST /v1/documents/{doctype}/create/ru` | создать черновик; тело — JSON типа (→ `references/document-types.md`) |
| `POST /v1/documents/{id}/update/{doctype}/ru` | обновить черновик (только статус 0); взять JSON из карточки, поправить, отправить. Для 000: `{document: <PDF base64>, data: {…}}` |
| `POST /v1/documents/{id}/delete/draft` | удалить черновик, подпись не нужна |

Ответ создания: `_id` (ID документа для дальнейших вызовов), `created_date`,
`pending_document.document_json` (итоговый JSON с системными полями).
Ошибки: 403 — нет полномочий на этот тип (роли, см. Профиль п.13), 422 —
неподдерживаемый тип / не PDF / нет файла.

## Документы: подписание и жизненный цикл

Всё, что меняет юридическое состояние, требует PKCS7 + timestamp
(`POST /v1/dsvs/timestamp` `{pkcs7, signatureHex}` → `timeStampTokenB64`).

| Действие | Флоу | CLI |
|---|---|---|
| Подписать исходящий | `data.json` карточки → base64 → PKCS7 → timestamp → `POST /{id}/sign` `{signature}` | `sign` |
| Принять входящий | `documentBase64` → PKCS7+timestamp; взять `toSign` из карточки (owner=0); `POST /v1/dsvs/signature/join` `{signature1: toSign, signature2: своя}` → `pkcs7B64` → `POST /{id}/sign` | `accept` |
| Отказаться от входящего | `POST /{id}/tosign` `{action: "reject", comment}` → подписать `data` → `POST /{id}/reject` `{signature, comment}` | `reject` |
| Отменить отправленный | `POST /{id}/tosign` `{action: "cancel"}` → подписать `data` → `POST /{id}/delete` `{signature}` | `cancel` |

`tosign` actions: `accept`, `cancel`, `reject` — все типы; `responsibleGive`,
`responsibleAccept`, `responsibleTillReturn` — ТТН и гибридная СФ;
`responsibleReturn`, `consignorReturn`, `consignorReturnAccept` — ТТН
(эндпоинты `/give`, `/tillreturn`, `/return`); `accountantAccept`,
`agentAccept` — новая доверенность 062. Ответ — объект для подписания или
готовая base64-строка (для accept/responsibleAccept).

`/sign` может вернуть `warningDetails` (предупреждения НК) при `data: true` —
показать пользователю. Ошибки несут `errorDetails` с расшифровкой
(язык — по `Accept-Language`).

## Типы документов (doctype)

`000` Произвольный (PDF, только внутри Didox) · `002` Счёт-фактура ·
`008` СФ ФАРМ · `023` Гибридная СФ · `041` ТТН · `005` Акт выполненных работ ·
`006` Доверенность · `062` Доверенность (новая) · `007` Договор НК (роуминг +
my.soliq.uz) · `010` Многосторонний произвольный · `052` Акт сверки ·
`054` Акт приёма-передачи · `075` Протокол собрания учредителей · `031` Письмо НК.

Структуры JSON всех типов → `references/document-types.md`.

## Статусы (`doc_status`) — по семействам типов

СФ (002/008): `0` черновик · `1` ждёт партнёра · `2` ждёт вашей подписи ·
`3` подписан · `4` отказ · `5` удалён · `40` недействительный · `50`
аннулирован НК · `55` черновик удалён · `60` ждёт подписи агента.

Акты, произвольные, договоры: `0`, `1`, `2`, `3`, `4`, `5`, `55` — те же значения.

Доверенность 006: + `6` ждёт подписи агента, `8` подписан агентом.
Доверенность 062: `310` отправлено, `340` подписан бухгалтером, `360` подписан агентом.

ТТН 041: `110` отправлено · `140` принято отв. лицом · `150` груз возвращён ·
`160` доставлено получателю · `170` отказано грузополучателем · `190` груз
возвращён отв. лицом · `200` подтверждение возврата. Гибридная СФ 023 —
те же в 200-серии.

Письмо 031: `3` = ПРОЧИТАНО, не «подписан».

## Профиль и справочная информация

| Эндпоинт | Что |
|---|---|
| `GET /v1/profile[?isSeller=true]` | свой профиль; `offerSigned`, `vatRegCode`; isSeller меняет НДС-поля |
| `POST /v1/profile/update` | изменить профиль (только изменяемые поля) |
| `GET /v1/profile/operators` | у каких операторов ЭДО зарегистрирован (важно для роуминга!) |
| `GET /v1/profile/branches?tin=` | филиалы |
| `GET /v1/profile/vatRegStatus/{tin}[?isSeller=true&document_date=]` | статус НДС: 20 активный, 21 неактивный, 22 приостановлен. Для продавца передавать isSeller=true, иначе null. HTTP 200 + `{"status":"failed"}` — проверять поле status! |
| `GET /v1/profile/taxpayerType/{tin}/ru` | тип: 10 НДС, 20-22 НДС+, 30 налог с оборота, 50 ИП, 60 физлицо |
| `GET /v1/profile/productClassCodes[?search=]` | ИКПУ профиля / поиск ИКПУ |
| `POST/DELETE /v1/profile/productClasses[/{code}]` | привязать/отвязать ИКПУ |
| `GET /v1/profile/{tin}/productClasses/check/{code}/ru` | упаковки по ИКПУ |
| `GET /v1/profile/warehouses/{tin}` | склады |
| `PUT /v1/profile/company/users` | роли сотрудника (две подписи: роли НК + роли Didox) |
| `GET /v1/utils/info/{tin}` | карточка компании из налоговой базы |
| `GET /v1/utils/bank-accounts/{tin}` | расчётные счета по ИНН |
| `GET /v1/account`, `POST /v1/account/update` | email/телефон/пароль/уведомления |

Каталоги: `GET /v1/banks/all`, `/v1/measures/all` (язык через
`Accept-Language`), `/v1/regions/all`, `/v1/districts/all`. Льготы по НДС:
`/v1/utils/product-privileges/ru`, `/v1/utils/company-privileges/ru`,
`/v1/utils/lgota/context-check/ru`. Транспорт и ЖД (для ТТН):
`/v1/utils/transport…`, `/v1/utils/stations`, `/v1/utils/waybills/…`.
Шаблоны договоров 007: CRUD на `/v1/document-template`.

## Маршрут «подать акт контрагенту» (произвольный, с PDF)

1. `docs --partner <ИНН>` — найти договор со статусом 3, взять его номер и дату.
   Ссылка в акте обязана указывать на этот договор: акт к номеру из локального
   docx, которого нет в ЭДО, контрагент отклонит.
2. Чистый PDF: раздел «Из docx в PDF» в SKILL.md.
3. `draft-000` с `--subtype 5`, `--contract-no/--contract-date` из шага 1.
4. `docs --partner <ИНН> --status 0` — черновик появился, реквизиты верны.
5. Подпись: `sign <DOC_ID> --serial <serial> --submit` по явной команде
   пользователя, либо кабинет didox.uz.

## Роуминг

Документ 000/010 виден только контрагентам внутри Didox. Контрагент у другого
оператора (Faktura.uz, E-Hujjat, soliqservis)? Проверить его операторов:
`raw GET '/v1/profile/operators'` под его ИНН не посмотреть — спросить
пользователя или использовать роуминговые типы (002, 005, 007, 041 — они
синхронизируются через my.soliq.uz).

## Тестовые прогоны

Черновик для проверки связки — только с номером `TEST-…` и немедленным
`draft-delete`: тестовый документ с обычным номером легко принять за рабочий
и подписать. Полный цикл с подписью — только на песочнице testapi3 тестовым
ключом.
