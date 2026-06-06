# GitHub Customer Data Fetcher
> يسحب ملفات بيانات العملاء من مستودع GitHub ويحوّلها إلى ملف Excel واحد.

## التشغيل

1. **تثبيت المتطلبات**:
   ```bash
   pip install -r requirements.txt
   ```

2. **(اختياري) ضبط GitHub Token** لزيادة حدود الاستدعاء:
   ```bash
   export GITHUB_TOKEN=your_personal_access_token
   ```

3. **تشغيل السكربت**:
   ```bash
   python fetch_customer_data.py
   ```

## أمثلة

- استخدام المستودع الافتراضي:
  ```bash
  python fetch_customer_data.py
  ```

- تحديد مستودع/فرع مختلف:
  ```bash
  python fetch_customer_data.py --owner amjadnofal88-lab --repo HelloGitHub --branch main
  ```

- تحديد اسم ملف الإخراج:
  ```bash
  python fetch_customer_data.py --output customers_export.xlsx
  ```

## الملفات المدعومة

- `.json`
- `.csv`
- `.xlsx`
- `.db`
- `.sqlite`

> ملاحظة: ملفات `.xls` يتم اكتشافها لكن يلزم تحويلها إلى `.xlsx` قبل المعالجة.

## السلوك

- يبحث السكربت داخل المستودع بالكامل عبر GitHub Contents API.
- يجمع السجلات من الملفات المدعومة.
- يضيف أعمدة مصدر مثل `_source_file` و `_source_type`.
- يزيل التكرارات ثم يصدّر النتائج إلى ملف Excel.
