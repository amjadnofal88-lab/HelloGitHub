#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Generate a local HTML renewals dashboard for ESKA files."""

import argparse
import html as html_module
import json
import re
from datetime import date, timedelta
from urllib.parse import quote

import pandas as pd


COLUMN_HINTS = {
    'policy_number': [
        'رقم الوثيقة', 'رقم الوثيقه', 'رقم البوليصة', 'رقم البوليصه',
        'policy number', 'policy no', 'policy', 'document number', 'document no'
    ],
    'customer_name': [
        'اسم العميل', 'اسم المؤمن له', 'اسم المؤمن', 'اسم الزبون', 'العميل',
        'customer name', 'client name', 'insured name', 'name'
    ],
    'company': [
        'شركة التأمين', 'الشركة', 'شركة', 'insurance company', 'insurer', 'company'
    ],
    'expiry_date': [
        'تاريخ الانتهاء', 'الانتهاء', 'تاريخ نهاية', 'expiry', 'expiration', 'expire date', 'end date'
    ],
    'phone': [
        'رقم الجوال', 'الجوال', 'الهاتف', 'رقم الهاتف', 'رقم الموبايل',
        'mobile', 'phone', 'cell', 'tel', 'telephone'
    ],
    'email': [
        'البريد', 'البريد الإلكتروني', 'البريد الالكتروني', 'email', 'e-mail', 'mail'
    ],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description='Build a local HTML dashboard for upcoming ESKA renewals.'
    )
    parser.add_argument('input_file', help='Path to ESKA renewals file (.xls/.xlsx).')
    parser.add_argument('--contacts', default='', help='Optional contacts file to enrich phone/email.')
    parser.add_argument('--days', type=int, default=365, help='Future window in days (default: 365).')
    parser.add_argument('--company', default='', help='Optional insurance company filter.')
    parser.add_argument('--out', default='renewals_dashboard.html', help='Output HTML path.')
    parser.add_argument('--country-code', default='970', help='Country code for local numbers (default: 970).')
    args = parser.parse_args()

    if args.days <= 0:
        parser.error('--days must be greater than 0.')
    if not re.fullmatch(r'\d{1,4}', str(args.country_code).strip()):
        parser.error('--country-code must be 1-4 digits.')

    args.country_code = str(args.country_code).strip()
    return args


def normalize_name(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).lower()


def find_column(columns, key):
    normalized = [(col, normalize_name(col)) for col in columns]
    for hint in COLUMN_HINTS[key]:
        hint_n = normalize_name(hint)
        for original, col_n in normalized:
            if hint_n == col_n or hint_n in col_n:
                return original
    return None


def parse_date_series(series):
    return pd.to_datetime(series, errors='coerce', dayfirst=True).dt.date


def normalize_phone(raw_phone, country_code='970'):
    value = re.sub(r'[^\d+]', '', str(raw_phone or '').strip())
    if not value:
        return ''
    if value.startswith('+970') or value.startswith('+972'):
        return value
    if value.startswith('00'):
        value = '+' + value[2:]
        if value.startswith('+970') or value.startswith('+972'):
            return value
        return value
    if value.startswith('+'):
        return value
    if value.startswith(country_code):
        return '+' + value
    if value.startswith('0'):
        return '+' + country_code + value[1:]
    if value.isdigit():
        return '+' + country_code + value
    return value


def mask_phone(phone):
    phone = str(phone or '').strip()
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if len(digits) <= 4:
        return '*' * len(digits)
    visible_start = digits[:3]
    visible_end = digits[-2:]
    return '{}{}{}'.format(visible_start, '*' * max(1, len(digits) - 5), visible_end)


def mask_email(email):
    email = str(email or '').strip()
    if not email or '@' not in email:
        return ''
    name, domain = email.split('@', 1)
    if len(name) <= 1:
        masked_name = '*'
    elif len(name) == 2:
        masked_name = name[0] + '*'
    else:
        masked_name = name[0] + '*' * (len(name) - 2) + name[-1]
    return masked_name + '@' + domain


def classify_priority(days_left):
    if days_left <= 30:
        return 'عاجل'
    if days_left <= 90:
        return 'قريب'
    return 'لاحق'


def build_message(row):
    company = row.get('company') or '-'
    policy = row.get('policy_number') or '-'
    customer = row.get('customer_name') or '-'
    expiry = row.get('expiry_date_str') or '-'
    return (
        'مرحبًا {}،\n'
        'نود تذكيركم بأن وثيقة التأمين رقم ({}) لدى {}\n'
        'ستنتهي بتاريخ {}.\n'
        'يرجى التواصل معنا لإتمام التجديد.\n'
        'مع الشكر.'.format(customer, policy, company, expiry)
    )


def load_excel(path):
    return pd.read_excel(path)


def prepare_contacts(df, country_code='970'):
    column_map = {
        'policy_number': find_column(df.columns, 'policy_number'),
        'customer_name': find_column(df.columns, 'customer_name'),
        'phone': find_column(df.columns, 'phone'),
        'email': find_column(df.columns, 'email'),
    }

    prepared = pd.DataFrame()
    if column_map['policy_number']:
        prepared['policy_number'] = df[column_map['policy_number']].astype(str).str.strip()
    else:
        prepared['policy_number'] = ''

    if column_map['customer_name']:
        prepared['customer_name'] = df[column_map['customer_name']].astype(str).str.strip()
    else:
        prepared['customer_name'] = ''

    prepared['phone'] = ''
    prepared['email'] = ''

    if column_map['phone']:
        prepared['phone'] = df[column_map['phone']].map(lambda v: normalize_phone(v, country_code))
    if column_map['email']:
        prepared['email'] = df[column_map['email']].astype(str).str.strip().replace({'nan': ''})

    prepared['name_key'] = prepared['customer_name'].map(normalize_name)
    prepared = prepared.drop_duplicates(subset=['policy_number', 'name_key'], keep='first')
    return prepared


def enrich_with_contacts(base_df, contacts_df):
    output = base_df.copy()

    merged = output.merge(
        contacts_df[['policy_number', 'name_key', 'phone', 'email']],
        how='left', on=['policy_number', 'name_key'], suffixes=('', '_contact')
    )
    for field in ['phone', 'email']:
        merged[field] = merged[field].fillna('')
        merged[field] = merged[field].where(merged[field].astype(str).str.strip() != '', merged[field + '_contact'])
        merged[field] = merged[field].fillna('').astype(str).str.strip()
    drop_cols = [c for c in merged.columns if c.endswith('_contact')]
    return merged.drop(columns=drop_cols)


def build_dataset(input_df, contacts_df=None, days=365, company_filter='', country_code='970'):
    col_policy = find_column(input_df.columns, 'policy_number')
    col_name = find_column(input_df.columns, 'customer_name')
    col_company = find_column(input_df.columns, 'company')
    col_expiry = find_column(input_df.columns, 'expiry_date')
    col_phone = find_column(input_df.columns, 'phone')
    col_email = find_column(input_df.columns, 'email')

    if not col_expiry:
        raise ValueError('Could not find expiry-date column in input file.')

    base = pd.DataFrame()
    base['policy_number'] = input_df[col_policy].astype(str).str.strip() if col_policy else ''
    base['customer_name'] = input_df[col_name].astype(str).str.strip() if col_name else ''
    base['company'] = input_df[col_company].astype(str).str.strip() if col_company else ''
    base['expiry_date'] = parse_date_series(input_df[col_expiry])
    base['phone'] = input_df[col_phone].map(lambda v: normalize_phone(v, country_code)) if col_phone else ''
    base['email'] = input_df[col_email].astype(str).str.strip().replace({'nan': ''}) if col_email else ''

    base = base.dropna(subset=['expiry_date']).copy()
    base['name_key'] = base['customer_name'].map(normalize_name)

    if contacts_df is not None:
        base = enrich_with_contacts(base, prepare_contacts(contacts_df, country_code))

    today = date.today()
    end_date = today + timedelta(days=days)

    base = base[(base['expiry_date'] >= today) & (base['expiry_date'] <= end_date)].copy()

    if company_filter:
        needle = normalize_name(company_filter)
        base = base[base['company'].map(normalize_name).str.contains(needle, na=False)].copy()

    base['days_left'] = base['expiry_date'].map(lambda d: (d - today).days)
    base['priority'] = base['days_left'].map(classify_priority)
    base['expiry_date_str'] = base['expiry_date'].map(lambda d: d.strftime('%Y-%m-%d'))
    base['phone'] = base['phone'].fillna('').astype(str).str.strip()
    base['email'] = base['email'].fillna('').astype(str).str.strip()
    base['phone_masked'] = base['phone'].map(mask_phone)
    base['email_masked'] = base['email'].map(mask_email)
    base['has_contact'] = ((base['phone'] != '') | (base['email'] != ''))

    rows = []
    for _, record in base.sort_values(by=['expiry_date', 'days_left']).iterrows():
        item = record.to_dict()
        item['message'] = build_message(item)
        phone_digits = re.sub(r'\D', '', item.get('phone', ''))
        whatsapp_phone = phone_digits
        item['whatsapp_url'] = ''
        if whatsapp_phone:
            item['whatsapp_url'] = 'https://wa.me/{}?text={}'.format(whatsapp_phone, quote(item['message']))
        item['sms_url'] = ''
        if item.get('phone'):
            item['sms_url'] = 'sms:{}?&body={}'.format(item['phone'], quote(item['message']))
        rows.append(item)

    summary = {
        'total': len(rows),
        'urgent': sum(1 for r in rows if r['priority'] == 'عاجل'),
        'near': sum(1 for r in rows if r['priority'] == 'قريب'),
        'later': sum(1 for r in rows if r['priority'] == 'لاحق'),
        'contact_ratio': round((sum(1 for r in rows if r.get('has_contact')) / len(rows)) * 100, 1) if rows else 0.0,
    }

    return rows, summary


def escape_js_string(text):
    return json.dumps(str(text or ''), ensure_ascii=False)


def render_html(rows, summary, output_path):
    table_rows = []
    for row in rows:
        message_js = escape_js_string(row.get('message', ''))
        whatsapp_btn = '<a class="btn" href="{}" target="_blank" rel="noopener">واتساب</a>'.format(
            html_module.escape(row['whatsapp_url'])
        ) if row.get('whatsapp_url') else '<span class="btn disabled">واتساب</span>'
        sms_btn = '<a class="btn" href="{}" target="_blank" rel="noopener">SMS</a>'.format(
            html_module.escape(row['sms_url'])
        ) if row.get('sms_url') else '<span class="btn disabled">SMS</span>'

        table_rows.append(
            '<tr data-priority="{priority}" data-company="{company_lc}">'
            '<td>{expiry}</td>'
            '<td>{days_left}</td>'
            '<td>{priority}</td>'
            '<td>{company}</td>'
            '<td>{policy}</td>'
            '<td>{customer}</td>'
            '<td dir="ltr">{phone}</td>'
            '<td dir="ltr">{email}</td>'
            '<td><textarea readonly>{message}</textarea></td>'
            '<td>'
            '<button class="btn" onclick="copyMsg({message_js})">نسخ الرسالة</button>'
            '{wa}{sms}'
            '</td>'
            '</tr>'.format(
                expiry=html_module.escape(str(row.get('expiry_date_str', ''))),
                days_left=html_module.escape(str(row.get('days_left', ''))),
                priority=html_module.escape(row.get('priority', '')),
                company=html_module.escape(row.get('company', '')),
                company_lc=html_module.escape(normalize_name(row.get('company', ''))),
                policy=html_module.escape(row.get('policy_number', '')),
                customer=html_module.escape(row.get('customer_name', '')),
                phone=html_module.escape(row.get('phone_masked', '')),
                email=html_module.escape(row.get('email_masked', '')),
                message=html_module.escape(row.get('message', '')),
                message_js=message_js,
                wa=whatsapp_btn,
                sms=sms_btn,
            )
        )

    html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>شاشة تجديدات ESKA</title>
  <style>
    body { font-family: Tahoma, Arial, sans-serif; margin: 16px; background: #f7f8fa; color: #222; }
    h1 { margin: 0 0 10px 0; }
    .note { margin: 0 0 12px 0; color: #555; }
    .summary, .filters { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
    .summary-grid { display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 8px; }
    .card { background: #fafafa; border: 1px solid #eee; border-radius: 6px; padding: 8px; }
    .filters label { margin-left: 8px; }
    .filters input, .filters select { padding: 6px; margin-left: 10px; }
    table { width: 100%; border-collapse: collapse; background: #fff; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; font-size: 13px; }
    th { background: #f0f2f5; position: sticky; top: 0; z-index: 1; }
    textarea { width: 100%; min-height: 84px; border: 1px solid #ddd; border-radius: 4px; font-family: inherit; font-size: 12px; }
    .btn { display: inline-block; margin: 2px; padding: 5px 8px; background: #0b5ed7; color: #fff; border-radius: 4px; text-decoration: none; border: none; cursor: pointer; font-size: 12px; }
    .btn.disabled { background: #aaa; pointer-events: none; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <h1>شاشة تجديدات ESKA</h1>
  <p class="note">الشاشة محلية: لا يتم رفع البيانات للإنترنت ولا إرسال رسائل تلقائيًا.</p>

  <section class="summary">
    <div class="summary-grid">
      <div class="card"><strong>الإجمالي</strong><br>{total}</div>
      <div class="card"><strong>عاجل</strong><br>{urgent}</div>
      <div class="card"><strong>قريب</strong><br>{near}</div>
      <div class="card"><strong>لاحق</strong><br>{later}</div>
      <div class="card"><strong>توفر التواصل</strong><br>{contact_ratio}%</div>
    </div>
  </section>

  <section class="filters">
    <label>بحث:</label>
    <input id="search" type="text" placeholder="اسم/وثيقة/شركة" oninput="applyFilters()" />

    <label>الأولوية:</label>
    <select id="priority" onchange="applyFilters()">
      <option value="">الكل</option>
      <option value="عاجل">عاجل</option>
      <option value="قريب">قريب</option>
      <option value="لاحق">لاحق</option>
    </select>

    <label>المدة:</label>
    <select id="window" onchange="applyFilters()">
      <option value="">الكل</option>
      <option value="30">خلال 30 يوم</option>
      <option value="90">خلال 90 يوم</option>
      <option value="365">خلال 365 يوم</option>
    </select>

    <label>شركة التأمين:</label>
    <input id="company" type="text" placeholder="اسم الشركة" oninput="applyFilters()" />
  </section>

  <table id="renewalsTable">
    <thead>
      <tr>
        <th>الانتهاء</th>
        <th>متبقي (يوم)</th>
        <th>الأولوية</th>
        <th>الشركة</th>
        <th>رقم الوثيقة</th>
        <th>العميل</th>
        <th>الجوال (مقنع)</th>
        <th>البريد (مقنع)</th>
        <th>الرسالة</th>
        <th>إجراءات</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <script>
    function copyMsg(message) {
      navigator.clipboard.writeText(message).then(function () {
        alert('تم نسخ الرسالة');
      });
    }

    function applyFilters() {
      const search = document.getElementById('search').value.toLowerCase().trim();
      const priority = document.getElementById('priority').value;
      const windowDays = document.getElementById('window').value;
      const company = document.getElementById('company').value.toLowerCase().trim();

      const rows = document.querySelectorAll('#renewalsTable tbody tr');
      rows.forEach((row) => {
        const text = row.innerText.toLowerCase();
        const rowPriority = row.getAttribute('data-priority') || '';
        const rowCompany = row.getAttribute('data-company') || '';
        const daysCell = row.children[1] ? parseInt(row.children[1].innerText, 10) : null;

        let ok = true;
        if (search && !text.includes(search)) ok = false;
        if (priority && rowPriority !== priority) ok = false;
        if (company && !rowCompany.includes(company)) ok = false;
        if (windowDays && Number.isFinite(daysCell)) {
          if (daysCell > parseInt(windowDays, 10)) ok = false;
        }

        row.style.display = ok ? '' : 'none';
      });
    }
  </script>
</body>
</html>
""".format(
        total=summary['total'],
        urgent=summary['urgent'],
        near=summary['near'],
        later=summary['later'],
        contact_ratio=summary['contact_ratio'],
        rows='\n'.join(table_rows),
    )

    with open(output_path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(html_content)


def run(args):
    input_df = load_excel(args.input_file)
    contacts_df = load_excel(args.contacts) if args.contacts else None

    rows, summary = build_dataset(
        input_df=input_df,
        contacts_df=contacts_df,
        days=args.days,
        company_filter=args.company,
        country_code=args.country_code,
    )

    render_html(rows, summary, args.out)
    print('Dashboard generated: {}'.format(args.out))


def main():
    args = parse_args()
    run(args)


if __name__ == '__main__':
    main()
