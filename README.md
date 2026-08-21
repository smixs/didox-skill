<h1 align="center">didox-cli</h1>

<p align="center">
  <strong>Didox.uz из терминала — для людей и AI-агентов</strong>
</p>

<p align="center">
  Документы, контрагенты, черновики — весь партнёрский API узбекского ЭДО<br>
  одним Python-файлом без единой зависимости. Вывод — JSON, агенту читать удобно.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue" alt="python 3.8+">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="zero dependencies">
  <img src="https://img.shields.io/badge/Claude_Code-skill_included-orange" alt="Claude Code skill">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT">
</p>

---

Didox — крупнейший оператор электронного документооборота Узбекистана
(350 000+ компаний). Веб-кабинет удобен человеку и мучителен агенту:
формы, датапикеры, модалки. `didox-cli` разговаривает с партнёрским API
напрямую — а приложенный скилл учит Claude Code делать это самостоятельно.

## Возможности

- Логин по паролю аккаунта (user-токен кэшируется на 6 часов)
- Список документов с фильтрами: контрагент, тип, статус, входящие/исходящие
- Карточка документа и печатная форма в PDF
- Данные любой компании по ИНН из налоговой базы
- Черновик «Произвольный документ» (000) с PDF-вложением: акты, договоры, приложения
- Удаление черновиков
- `raw` — прямой вызов любого эндпоинта API

Подписание намеренно не включено: подпись E-IMZO юридически равна
собственноручной, её ставит человек. CLI доводит документ до черновика.

## Быстрый старт

```bash
git clone https://github.com/smixs/didox-cli && cd didox-cli
mkdir -p ~/.didox && cat > ~/.didox/env <<'EOF'
DIDOX_PARTNER_TOKEN=<партнёрский JWT>
DIDOX_TIN=<ИНН вашей компании>
DIDOX_PASSWORD=<пароль аккаунта Didox>
EOF
chmod 600 ~/.didox/env
./didox-cli/scripts/didox.py login
```

Партнёрский токен выдаёт аккаунт-менеджер Didox ([t.me/Didox_account](https://t.me/Didox_account)).
Пароль аккаунта задаётся в кабинете didox.uz → Профиль → Аккаунт (вход по ЭЦП
пароля не создаёт — задайте его один раз). Тестовый стенд: `DIDOX_URL=https://testapi3.didox.uz`.

## Команды

| Команда | Что делает |
|---|---|
| `didox.py login` | получить и закэшировать user-токен |
| `didox.py profile` | реквизиты своей компании |
| `didox.py docs --partner <ИНН>` | документы по контрагенту |
| `didox.py docs --status 0` | черновики |
| `didox.py docs --owner 0` | входящие |
| `didox.py doc <DOC_ID>` | карточка документа |
| `didox.py doc-pdf <DOC_ID> out.pdf` | печатная форма |
| `didox.py partner <ИНН>` | компания из налоговой базы |
| `didox.py draft-000 …` | черновик с PDF (пример ниже) |
| `didox.py draft-delete <DOC_ID>` | удалить черновик |
| `didox.py raw GET '/v2/documents?limit=5'` | любой эндпоинт |

Подать акт контрагенту:

```bash
didox.py draft-000 \
  --number 1 --date 2026-08-21 \
  --buyer-tin 207151159 --subtype 5 \
  --name "Акт № 1 к Договору № 19062026 от 19.06.2026" \
  --contract-no 19062026 --contract-date 2026-06-19 \
  --pdf act.pdf
```

Подтипы: `2` Письмо · `3` Договор · `5` Акт выполненных работ · `6` Другое ·
`8` Спецификация · `9` Доп. соглашение.
Статусы: `0` черновик · `1` ждёт подписи партнёра · `3` подписан обеими · `4` отказ.

## Скилл для Claude Code

Папка [`didox-cli/`](didox-cli/) — готовый agent skill: SKILL.md с маршрутами
(«подать акт», «проверить подпись»), pre-flight, справочники API и сам CLI.

```bash
cp -R didox-cli ~/.claude/skills/
```

После этого «выстави акт руделлу по подписанному договору» — задача одного
сообщения: агент найдёт договор, создаст черновик, проверит реквизиты и
позовёт вас подписать.

## English

CLI + Claude Code agent skill for **Didox.uz**, Uzbekistan's largest
e-document exchange (EDO) operator. Single-file Python 3.8+, zero
dependencies, JSON output. List documents, check signing status, look up any
company by TIN from the tax registry, create document drafts with PDF
attachments, download print forms. Signing is deliberately excluded: an
E-IMZO digital signature is legally binding, so a human signs. Config lives
in `~/.didox/env` (partner token, TIN, account password) — see Quick Start.

## Oʼzbekcha

**didox-cli** — Didox.uz (elektron hujjat almashinuvi) bilan terminal orqali
ishlash uchun CLI va AI-agentlar uchun tayyor skill. Bitta Python-fayl,
qoʼshimcha kutubxonalarsiz, natijalar JSON koʼrinishida.

Imkoniyatlar:

- Hujjatlar roʼyxati va imzo holatini tekshirish
- STIR boʼyicha istalgan kompaniya maʼlumotlarini soliq bazasidan olish
- PDF ilova bilan qoralama hujjat yaratish: akt, shartnoma, ilova
- Chop etish shaklini PDF koʼrinishida yuklab olish

Imzolash CLI tarkibiga ataylab kiritilmagan: hujjatni E-IMZO kaliti bilan
foydalanuvchining oʼzi imzolaydi. Sozlamalar `~/.didox/env` faylida
saqlanadi — Quick Start boʼlimiga qarang.

## License

MIT
