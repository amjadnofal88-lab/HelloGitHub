# ahleia-query

أداة سطر أوامر Python لتحليل كشوف حسابات التأمين (PDF) وتخزينها في SQLite واستعراضها.

---

## المتطلبات

```bash
pip install -r requirements.txt
```

> اختياري: ثبّت **poppler-utils** للحصول على أداء أفضل في استخراج النصوص:
> - Ubuntu/Debian: `sudo apt install poppler-utils`
> - macOS: `brew install poppler`
> - Windows: https://github.com/oschwartz10612/poppler-windows/releases

---

## الاستخدام

### 1. استيراد ملفات PDF

```bash
python parse.py كشف1.pdf كشف2.pdf --db statements.db
```

يُنشئ (أو يُحدّث) قاعدة البيانات `statements.db` وجدول `entries` بالأعمدة:

| العمود | الوصف |
|--------|-------|
| id | معرّف تلقائي |
| source | اسم ملف PDF |
| account | رقم الحساب |
| date | التاريخ كما يظهر في الملف |
| iso_date | التاريخ بصيغة ISO-8601 (YYYY-MM-DD) |
| journal_no | رقم القيد |
| journal_type | نوع القيد |
| kind | النوع |
| cheque_no | رقم الشيك |
| note | البيان |
| amount | المبلغ |
| currency | العملة |
| debit | المدين |
| credit | الدائن |
| balance | الرصيد |

---

### 2. الاستعلام عبر سطر الأوامر

```bash
python query.py [--db statements.db] <أمر> [خيارات]
```

| الأمر | الوصف | مثال |
|-------|-------|------|
| `summary` | ملخص المجاميع لكل حساب | `python query.py summary` |
| `cheque` | بحث برقم الشيك | `python query.py cheque 123456` |
| `returned` | الشيكات المرتجعة | `python query.py returned` |
| `duplicates` | قيود مكررة | `python query.py duplicates` |
| `blank` | صفوف بدون بيان | `python query.py blank` |
| `offsets` | مقاصة مدين/دائن | `python query.py offsets` |
| `garage` | مدفوعات الكراجات | `python query.py garage` |
| `reused` | شيكات مُعاد استخدامها | `python query.py reused` |
| `search` | بحث نصي | `python query.py search ورشة` |
| `range` | تصفية بنطاق تاريخ | `python query.py range --from-date 2023-01-01 --to-date 2023-12-31` |
| `sql` | تشغيل SELECT مباشر | `python query.py sql "SELECT * FROM entries LIMIT 5"` |

---

### 3. تصدير Excel

```bash
python report.py --db statements.db --out report.xlsx [--account 12345] [--from-date 2023-01-01] [--to-date 2023-12-31]
```

يُنتج ملف Excel متعدد الأوراق (7 أوراق) بتنسيق عربي RTL:

1. **ملخص** — مجاميع لكل حساب وعملة
2. **كل القيود** — جميع السجلات
3. **الشيكات** — سجلات الشيكات
4. **المرتجعات** — الشيكات المرتجعة
5. **التكرارات** — أرقام قيود مكررة
6. **المقاصة** — أزواج مدين/دائن تساوي صفراً
7. **الكراجات** — مدفوعات الورش والكراجات

---

### 4. واجهة الويب المحلية

```bash
python webapp.py --db statements.db --port 5000
```

ثم افتح المتصفح على: http://127.0.0.1:5000

---

## هيكل المشروع

```
ahleia-query/
├── parse.py          # استيراد PDF → SQLite
├── query.py          # استعلامات سطر الأوامر
├── report.py         # تصدير Excel متعدد الأوراق
├── webapp.py         # واجهة ويب Flask
├── requirements.txt  # المتطلبات
├── .gitignore        # يستثني ملفات PDF/XLSX/DB
└── README.md         # هذا الملف
```

---

## الأمان

- لا توجد بيانات اعتماد مُضمَّنة في الكود.
- لا تُحمَّل أي ملفات بيانات (PDF/XLSX/DB) إلى المستودع.
- واجهة الويب تعمل محلياً فقط على `127.0.0.1` بشكل افتراضي.
- قاعدة البيانات تقبل جمل `SELECT` فقط من واجهة SQL المباشرة.
