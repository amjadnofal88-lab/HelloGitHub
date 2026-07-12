#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
renewals_report.py — كشف التجديدات
يقرأ تقرير الذمم (Crystal .xls/.xlsx) ويولّد كشف تجديدات إكسل عربي RTL:
  • متأخرة   — انتهت ولم تُجدَّد
  • عاجلة    — تنتهي خلال 15 يوم
  • قادمة    — تنتهي خلال 16-60 يوم
  • الكل     — كل البوالص مع الحالة والأيام المتبقية
  • واتساب   — ملف جاهز للبوت (اسم / جوال / نص الرسالة)

Usage:
    python renewals_report.py receivables.xls
    python renewals_report.py receivables.xls --contacts contacts.xlsx --days 60 -o renewals.xlsx
    python renewals_report.py receivables.xls --icloud
"""
import os
import re
import shutil
import argparse
import datetime as dt
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# ── إعدادات قابلة للتعديل ───────────────────────────────────────────────
URGENT_DAYS = 15          # "عاجل" = ينتهي خلال هذا العدد من الأيام
UPCOMING_DAYS = 60        # نطاق "قادم"
BROKER_PHONE = '0599432658'
BROKER_NAME = 'شركة البديل للخدمات العامة واللوجستية'
ICLOUD_FOLDER = 'AHLEIA Renewals'

HDR_FILL = PatternFill(fill_type='solid', fgColor='1F4E78')
HDR_FONT = Font(bold=True, color='FFFFFF', name='Arial', size=11)
BODY_FONT = Font(name='Arial', size=10)
MONEY = '#,##0.00;[Red]-#,##0.00;-'

FILLS = {
    'متأخرة': PatternFill(fill_type='solid', fgColor='FFC7CE'),   # أحمر فاتح
    'عاجلة': PatternFill(fill_type='solid', fgColor='FFEB9C'),    # أصفر
    'قادمة': PatternFill(fill_type='solid', fgColor='C6EFCE'),    # أخضر
    'سارية': PatternFill(fill_type='solid', fgColor='FFFFFF'),
}


def load_receivables(path):
    """يقرأ .xls (Crystal) عبر LibreOffice أو .xlsx مباشرة."""
    path = Path(path)
    if path.suffix.lower() == '.xls':
        tmp = Path(tempfile.mkdtemp())
        try:
            subprocess.run(['soffice', '--headless', '--convert-to', 'xlsx',
                            '--outdir', str(tmp), str(path)],
                           check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise SystemExit(
                'ERROR: LibreOffice is required to convert .xls files. '
                'Please install it (e.g. apt install libreoffice) or convert '
                'the file to .xlsx manually.\nDetails: {}'.format(exc)
            ) from exc
        path = tmp / (path.stem + '.xlsx')
    df = pd.read_excel(path, header=1)
    return df.dropna(subset=['DOCUMENT_NO'])


def normalize_phone(v):
    """يحوّل الرقم لصيغة واتساب الدولية 970xxxxxxxxx."""
    if pd.isna(v):
        return ''
    d = re.sub(r'\D', '', str(v))
    if d.startswith('00'):
        d = d[2:]
    if d.startswith('972'):
        d = '970' + d[3:]
    if d.startswith('0') and len(d) == 10:
        d = '970' + d[1:]
    if not d.startswith('970') and len(d) == 9:
        d = '970' + d
    return d if len(d) == 12 else ''


def base_policy(doc_no):
    """رقم البوليصة الأساسي بدون لواحق التجديد/الملاحق."""
    return re.split(r'-R-|-E-', str(doc_no))[0]


def build(df, contacts=None, days=UPCOMING_DAYS, today=None):
    today = today or dt.date.today()

    df = df.copy()
    df['EXPIRY'] = pd.to_datetime(df['EXPIRY_DATE'], errors='coerce')
    df['ISSUE'] = pd.to_datetime(df['ISSUE_DATE'], errors='coerce')
    df = df.dropna(subset=['EXPIRY'])
    df['BASE'] = df['DOCUMENT_NO'].map(base_policy)

    # نُبقي أحدث وثيقة لكل بوليصة (التجديد يلغي سابقه)
    df = df.sort_values('EXPIRY').drop_duplicates('BASE', keep='last')

    df['DAYS_LEFT'] = (df['EXPIRY'].dt.date - today).map(lambda x: x.days)

    def status(d):
        if d < 0:
            return 'متأخرة'
        if d <= URGENT_DAYS:
            return 'عاجلة'
        if d <= days:
            return 'قادمة'
        return 'سارية'

    df['STATUS'] = df['DAYS_LEFT'].map(status)

    # دمج جهات الاتصال (اختياري)
    df['PHONE'] = ''
    if contacts is not None:
        cmap = {}
        name_col = next((c for c in contacts.columns
                         if str(c).upper() in ('NAME', 'BENEFICIARY', 'الاسم')), contacts.columns[0])
        ph_col = next((c for c in contacts.columns
                       if str(c).upper() in ('PHONE', 'MOBILE', 'الجوال', 'الهاتف')), contacts.columns[1])
        for _, r in contacts.iterrows():
            p = normalize_phone(r[ph_col])
            if p:
                cmap[str(r[name_col]).strip()] = p
        df['PHONE'] = df['BENEFICIARY'].map(
            lambda n: cmap.get(str(n).strip(), ''))

    return df.sort_values('DAYS_LEFT')


def wa_message(row):
    d = int(row['DAYS_LEFT'])
    when = ('انتهت بتاريخ {:%d-%m-%Y} (متأخرة {} يوم)'.format(row['EXPIRY'], abs(d))
            if d < 0
            else 'تنتهي بتاريخ {:%d-%m-%Y} (بعد {} يوم)'.format(row['EXPIRY'], d))
    veh = row.get('VEHICLE_TYPE') or ''
    plate = row.get('PLATE_NUMBER') or ''
    veh_txt = (' للمركبة {} لوحة {}'.format(veh, plate).rstrip()
               if str(plate) != 'nan' and plate else '')
    return ('مرحباً {}،\n'
            'وثيقة التأمين رقم {}{} {}.\n'
            'يسعدنا تجديدها لك — تواصل معنا على {}.\n'
            '{}'.format(
                row['BENEFICIARY'], row['DOCUMENT_NO'], veh_txt, when,
                BROKER_PHONE, BROKER_NAME))


def sheet(wb, title, rows, headers, widths, money_cols=(), color_by_status=True):
    ws = wb.create_sheet(title)
    ws.sheet_view.rightToLeft = True
    ws.append(headers)
    for c in ws[1]:
        c.font, c.fill = HDR_FONT, HDR_FILL
        c.alignment = Alignment(horizontal='center')
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for col in money_cols:
        for c in ws[get_column_letter(col)][1:]:
            c.number_format = MONEY
    if color_by_status and 'الحالة' in headers:
        si = headers.index('الحالة') + 1
        for row in ws.iter_rows(min_row=2):
            st = row[si - 1].value
            if st in FILLS:
                for c in row:
                    c.fill = FILLS[st]
                    c.font = BODY_FONT
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    return ws


COLS = ['BENEFICIARY', 'DOCUMENT_NO', 'CLASS', 'VEHICLE_TYPE', 'VEHICLE_MODEL',
        'PLATE_NUMBER', 'EXPIRY', 'DAYS_LEFT', 'STATUS', 'NET_PREMIUM_LC',
        'NET_AR_BALANCE', 'PHONE']
HEADERS = ['المؤمَّن له', 'رقم البوليصة', 'الفرع', 'نوع المركبة', 'الموديل',
           'رقم اللوحة', 'تاريخ الانتهاء', 'الأيام المتبقية', 'الحالة',
           'القسط', 'الرصيد المستحق', 'الجوال']
WIDTHS = [30, 24, 12, 14, 14, 12, 14, 13, 11, 12, 14, 15]


def rows_of(d):
    out = []
    for _, r in d.iterrows():
        out.append([
            r['BENEFICIARY'], r['DOCUMENT_NO'], r['CLASS'],
            r.get('VEHICLE_TYPE') if pd.notna(r.get('VEHICLE_TYPE')) else '',
            r.get('VEHICLE_MODEL') if pd.notna(r.get('VEHICLE_MODEL')) else '',
            str(r.get('PLATE_NUMBER')) if pd.notna(r.get('PLATE_NUMBER')) else '',
            r['EXPIRY'].strftime('%d-%m-%Y'), int(r['DAYS_LEFT']), r['STATUS'],
            float(r['NET_PREMIUM_LC']), float(r['NET_AR_BALANCE']), r['PHONE'],
        ])
    return out


def build_workbook(df, out_path, days=UPCOMING_DAYS):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    late = df[df['STATUS'] == 'متأخرة']
    urgent = df[df['STATUS'] == 'عاجلة']
    soon = df[df['STATUS'] == 'قادمة']
    action = df[df['STATUS'] != 'سارية']

    # ملخص
    ws = wb.create_sheet('الملخص')
    ws.sheet_view.rightToLeft = True
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 18
    ws['A1'] = 'كشف التجديدات'
    ws['A1'].font = Font(bold=True, size=14, name='Arial', color='1F4E78')
    ws['A2'] = 'تاريخ التقرير: {:%d-%m-%Y}'.format(dt.date.today())
    ws['A2'].font = Font(italic=True, size=9, name='Arial')

    ws.append([])
    hdr = ['الحالة', 'عدد البوالص', 'إجمالي الأقساط']
    ws.append(hdr)
    for c in ws[4]:
        c.font, c.fill = HDR_FONT, HDR_FILL
    for name, d in [('متأخرة', late), ('عاجلة (\u226415 يوم)', urgent),
                    ('قادمة (\u2264{} يوم)'.format(days), soon),
                    ('إجمالي للمتابعة', action), ('سارية', df[df['STATUS'] == 'سارية'])]:
        ws.append([name, len(d), float(d['NET_PREMIUM_LC'].sum())])
    for row in ws.iter_rows(min_row=5, min_col=3, max_col=3):
        for c in row:
            c.number_format = MONEY
            c.font = BODY_FONT
    ws.cell(row=9, column=1).font = Font(bold=True, name='Arial')
    ws.cell(row=9, column=2).font = Font(bold=True, name='Arial')
    ws.cell(row=9, column=3).font = Font(bold=True, name='Arial')
    ws.append([])
    ws.append(['أرصدة مستحقة على بوالص المتابعة', '',
               float(action['NET_AR_BALANCE'].sum())])
    ws.cell(row=ws.max_row, column=3).number_format = MONEY
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True, name='Arial')

    sheet(wb, 'متأخرة', rows_of(late), HEADERS, WIDTHS, money_cols=(10, 11))
    sheet(wb, 'عاجلة', rows_of(urgent), HEADERS, WIDTHS, money_cols=(10, 11))
    sheet(wb, 'قادمة', rows_of(soon), HEADERS, WIDTHS, money_cols=(10, 11))
    sheet(wb, 'الكل', rows_of(df), HEADERS, WIDTHS, money_cols=(10, 11))

    # شيت واتساب — جاهز للبوت
    wa_rows = [[r['BENEFICIARY'], r['PHONE'], r['DOCUMENT_NO'],
                r['EXPIRY'].strftime('%d-%m-%Y'), int(r['DAYS_LEFT']),
                r['STATUS'], wa_message(r)] for _, r in action.iterrows()]
    sheet(wb, 'واتساب', wa_rows,
          ['الاسم', 'الجوال', 'رقم البوليصة', 'تاريخ الانتهاء',
           'الأيام المتبقية', 'الحالة', 'نص الرسالة'],
          [28, 16, 24, 14, 13, 11, 90], color_by_status=False)

    wb.save(out_path)
    return out_path


def copy_to_icloud(src, folder=ICLOUD_FOLDER):
    root = Path(os.environ.get(
        'ICLOUD_DRIVE_PATH',
        os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs')))
    if not root.exists():
        print('WARNING: iCloud Drive not found at {}. Skipping.'.format(root))
        return None
    dest = root / folder / Path(src).name
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
    except OSError as e:
        print('ERROR: iCloud copy failed: {}'.format(e))
        return None
    print('Copied to iCloud: {}'.format(dest))
    return dest


def main():
    p = argparse.ArgumentParser(description='كشف تجديدات البوالص')
    p.add_argument('receivables', help='ملف الذمم (.xls أو .xlsx)')
    p.add_argument('--contacts', help='ملف جهات الاتصال (اسم + جوال) لدمج الأرقام')
    p.add_argument('--days', type=int, default=UPCOMING_DAYS,
                   help='نطاق التجديدات القادمة بالأيام (افتراضي {})'.format(UPCOMING_DAYS))
    p.add_argument('-o', '--output', default=None)
    p.add_argument('--icloud', action='store_true', help='نسخ الملف إلى iCloud Drive')
    p.add_argument('--icloud-folder', default=ICLOUD_FOLDER)
    a = p.parse_args()

    df = load_receivables(a.receivables)
    contacts = pd.read_excel(a.contacts) if a.contacts else None
    df = build(df, contacts=contacts, days=a.days)

    out = a.output or 'renewals_{:%Y%m%d}.xlsx'.format(dt.date.today())
    build_workbook(df, out, days=a.days)

    c = df['STATUS'].value_counts()
    print('Saved: {}'.format(out))
    print('  متأخرة: {} | عاجلة: {} | قادمة: {} | سارية: {}'.format(
        c.get('متأخرة', 0), c.get('عاجلة', 0),
        c.get('قادمة', 0), c.get('سارية', 0)))

    if a.icloud:
        copy_to_icloud(out, a.icloud_folder)


if __name__ == '__main__':
    main()
