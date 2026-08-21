# JSON-структуры документов (для `create <doctype> payload.json`)

Скелеты обязательных полей по типам. Полные структуры с построчными
комментариями: https://api-docs.didox.uz/ru/integrators-property-documents
(раздел 07) — при создании нового типа документа свериться с ней, поля
меняются требованиями роуминга.

## Общие правила роуминга (строгая валидация принимающей стороной)

Нарушение любого из них — документ отклоняется на приёме, поэтому проверять
до отправки:

- **Лишние поля запрещены.** Всё, чего нет в примере доки, не передавать
  (в т.ч. WithoutExcise, Expansion, Id, MeasureId в СФ, SellerDepartmentId).
- **Неиспользуемый объект = null**, не `{}` с пустыми строками
  (FacturaRentDoc, OldFacturaDoc, ItemReleasedDoc, FacturaEmpowermentDoc,
  ForeignCompany, FacturaInvestmentObjectDoc).
- **Числа:** Count — до 6 знаков после запятой; остальные суммы/ставки — до 2.
  Точка как разделитель, без разделителей разрядов.
- **Даты:** строго `yyyy-MM-dd`, без времени и таймзоны.
- **WithoutVat** передаётся только при `HasVat = true`.
- **Director** продавца и покупателя — обязательное поле в СФ.
- Односторонний ЭСФ (`SingleSidedType`): `Buyer: null`, `BuyerTin: ""`.

Реквизиты сторон не выдумывать: продавец — из `profile`, покупатель — из
`partner <ИНН>` (налоговая база), счета — из `raw GET '/v1/utils/bank-accounts/<ИНН>'`,
НДС-статус — из `vatRegStatus` (для продавца с `isSeller=true`).

## 000 Произвольный документ (PDF ≤ 10 МБ, только внутри Didox)

CLI-команда `draft-000` собирает его сама. Вручную:

```json
{
  "data": {
    "Document": {"DocumentNo": "1", "DocumentDate": "2026-08-21", "DocumentName": "…"},
    "Subtype": 5,
    "ContractDoc": {"ContractNo": "…", "ContractDate": "yyyy-MM-dd"},
    "SellerTin": "…", "Seller": {"Name": "…", "BranchCode": "", "BranchName": "", "Address": "…"},
    "BuyerTin": "…", "Buyer": {"Name": "…", "BranchCode": "", "BranchName": "", "Address": "…"}
  },
  "document": "data:application/pdf;base64,…"
}
```

Подтипы: `1` Акт сверки · `2` Письмо · `3` Договор · `4` Счёт на оплату ·
`5` Акт выполненных работ · `6` Другое · `7` Заявка · `8` Спецификация ·
`9` Доп. соглашение · `10` Акт приёма-передачи. Приложения к договору —
всегда 9 (юридически это соглашение сторон; «Другое» и «Спецификация»
бухгалтерия контрагента отвергает).

## 002 Счёт-фактура (ЭСФ)

Ядро: `Version: 1`, `FacturaType` (0 стандартный, 1 дополнительный,
2 возмещение, 3 без оплаты, 4 исправленный…; при ≠0 обязателен
`OldFacturaDoc`), `FacturaDoc {FacturaNo, FacturaDate}`, `ContractDoc`,
`SellerTin/Seller`, `BuyerTin/Buyer` (оба с Director, VatRegCode,
VatRegStatus, Account, BankId, Address), `ProductList {Tin, HasVat,
HasExcise, HasCommittent, HasLgota, Products[]}`. Позиция: OrdNo,
Name, CatalogCode+CatalogName (ИКПУ), PackageCode+PackageName, Count, Summa,
DeliverySum, VatRate, VatSum, DeliverySumWithVat, WithoutVat, Origin
(1 производство, 2 купля-продажа, 3 услуги, 4 не участвую). Служебное поле
`didoxcontractid` — связка с Договором НК, в тело не попадает.
`WaybillLocalIds: []`, `HasMarking`, `HasRent`+`FacturaRentDoc`, `LotId`
(биржевые сделки — данные лота через `/v1/documents/exchange`).

008 ФАРМ = 002 + `ProductList.HasMedical: true` + в позициях Serial,
BaseSumma, ProfitRate, DispenseType (1 по рецепту, 2 без).

## 005 Акт выполненных работ (роуминговый, без PDF)

```json
{
  "actdoc": {"actno": "1", "actdate": "yyyy-MM-dd", "acttext": "Мы, нижеподписавшиеся…"},
  "contractdoc": {"contractno": "…", "contractdate": "yyyy-MM-dd"},
  "sellertin": "…", "sellername": "…", "sellerbranchcode": "", "sellerbranchname": "",
  "buyertin": "…", "buyername": "…", "buyerbranchcode": "", "buyerbranchname": "",
  "productlist": {"tin": "<ИНН продавца>", "products": [
    {"ordno": 1, "name": "…", "catalogcode": "<ИКПУ или null>", "catalogname": null,
     "packagecode": null, "packagename": null, "measureid": "<если нет ИКПУ>",
     "count": "1", "summa": "…", "totalsum": "…"}
  ]}
}
```

catalogcode указан → обязательны packagecode/packagename; не указан →
обязателен measureid. `extended_json` с vatrate/vatsum — для позиций с НДС.

## 007 Договор НК (роуминг + my.soliq.uz)

`ContractDoc {ContractName, ContractNo, ContractDate, ContractExpireDate,
ContractPlace}`, `Owner {Tin, Name, FizTin (ПИНФЛ подписанта), Fio, Address,
Account, BankId, Oked}`, `Clients[]` (те же поля по каждому контрагенту),
`Parts[]` (разделы текста: ordno, title, body), `Products[]` (как в СФ),
`HasVat`. Шаблоны разделов — `/v1/document-template`.

## 052 Акт сверки

`VerificationActDoc {No, Date, Text}`, `VerificationActContracts[]` — по
договору: ContractNo/Date, OpenBalance/CloseBalance/TotalBalance (Owner/
PartnerDebit/Credit), items с операциями обеих сторон; `OwnerTin/Name/FizTin/
FizFio`, `PartnerTin/Name/FizTin/FizFio`, `TurnoverBalance`, `OpenBalance`,
`CloseBalance`.

## 054 Акт приёма-передачи

`AcceptanceTransferActDoc {No, Date}`, `ContractDoc`, `SellerPinfl`+`Seller`
(может быть физлицо), `BuyerTinOrPinfl`+`Buyer`, `totalPrice`, `Products[]`.

## 010 Многосторонний произвольный (PDF, внутри Didox)

Как 000, но `Owner` + `Clients[]` (несколько получателей) внутри `data`,
PDF в `document`.

## 031 Письмо НК

`LetterDoc {No, Date}`, `Sender {TinOrPinfl, Name, Address, Head {Pinfl,
FullName, Position}, BankId, BankAccount, Phones[]}`, `Recipient {TinOrPinfl,
Name, Address}`, `HtmlContent` (HTML тела письма), `Attachments[]
{Filename, MimeType, Size, ContentBase64}`. Статус 3 у письма = «прочитано».

## 075 Протокол собрания учредителей

`documentdoc {documentname, documentno, documentplace, documentdate}`,
`company` (реквизиты ООО), `participants[]` (ПИНФЛ, ФИО, доля, ischairman/
issecretary), `parts[]` (повестка: ordno, title, body).

## 006 / 062 Доверенность, 041 ТТН, 023 гибридная СФ

Трёхсторонние и транспортные структуры (стороны + агент/перевозчик, вагоны,
маршруты). Используются редко — при необходимости взять полный пример из
раздела 07 доки и подставить реквизиты; для ТТН есть справочники транспорта
и ЖД-станций (см. api-details «Профиль и справочная информация»).
