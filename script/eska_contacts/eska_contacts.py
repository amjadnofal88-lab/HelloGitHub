#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
eska_contacts.py — سحب بيانات التواصل من بوابة إسكا لكل وثيقة في ملف الذمم.

الاستخدام:
    python eska_contacts.py "ذمم.xls"                   # سحب كامل (٥٦٣ وثيقة)
    python eska_contacts.py "ذمم.xls" --renewals-only   # التجديدات فقط (٣٤٨ وثيقة)
    python eska_contacts.py "ذمم.xls" --out contacts.xlsx

متطلبات:
    ESKA_PASS — متغير بيئة يحتوي على كلمة المرور للبوابة.

المخرجات:
    contacts.xlsx — ملف إكسل يحتوي على بيانات التواصل لكل وثيقة.
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, timedelta

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ── إعدادات البوابة ────────────────────────────────────────────────────────────
# عدّل هذه القيم لتتوافق مع بيئتك
ESKA_BASE_URL = os.environ.get('ESKA_URL', 'https://portal.eska.com.sa')
ESKA_LOGIN_PATH = '/login'          # مسار صفحة تسجيل الدخول
ESKA_SEARCH_PATH = '/policies'      # مسار صفحة البحث عن الوثائق

ESKA_USER = os.environ.get('ESKA_USER', '')
ESKA_PASS = os.environ.get('ESKA_PASS', '')

# ── محددات عناصر HTML (CSS Selectors) ─────────────────────────────────────────
# عدّلها لتتوافق مع الصفحات الفعلية في البوابة
SEL_USERNAME_INPUT = 'input[name="username"], input[name="email"], #username'
SEL_PASSWORD_INPUT = 'input[name="password"], input[type="password"]'
SEL_LOGIN_BUTTON   = 'button[type="submit"], input[type="submit"]'
SEL_SEARCH_INPUT   = 'input[name="policy_no"], #policy_no, input[placeholder*="وثيقة"]'
SEL_SEARCH_BUTTON  = 'button[type="submit"]'
SEL_CLIENT_PHONE   = '[data-field="phone"], .client-phone, td.phone'
SEL_CLIENT_EMAIL   = '[data-field="email"], .client-email, td.email'
SEL_CLIENT_MOBILE  = '[data-field="mobile"], .client-mobile, td.mobile'

# ── أعمدة ملف الذمم XLS ───────────────────────────────────────────────────────
# عدّل أسماء الأعمدة لتتطابق مع الملف الفعلي
COL_POLICY_NO    = 'رقم الوثيقة'
COL_CLIENT_NAME  = 'اسم العميل'
COL_EXPIRY_DATE  = 'تاريخ الانتهاء'
COL_INSURER      = 'شركة التأمين'
COL_POLICY_TYPE  = 'نوع التأمين'
COL_PREMIUM      = 'إجمالي القسط'

# ── نافذة التجديد ──────────────────────────────────────────────────────────────
# الوثائق التي تنتهي خلال هذه الأيام تُعدّ "تجديدات"
RENEWAL_DAYS = 90

PAGE_TIMEOUT = 15_000  # ميلي ثانية — خفّض إذا كانت البوابة بطيئة

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('eska_contacts')


# ── تحميل وتصفية ملف الذمم ────────────────────────────────────────────────────

def load_xls(path: str) -> pd.DataFrame:
    """تحميل ملف XLS أو XLSX وإعادة DataFrame."""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.xls',):
        df = pd.read_excel(path, engine='xlrd')
    else:
        df = pd.read_excel(path, engine='openpyxl')
    logger.info('تم تحميل %d صف من "%s"', len(df), path)
    return df


def filter_renewals(df: pd.DataFrame) -> pd.DataFrame:
    """
    إعادة الصفوف التي تنتهي وثائقها خلال RENEWAL_DAYS يومًا القادمة.
    إذا لم يكن عمود تاريخ الانتهاء موجودًا، تُعاد جميع الصفوف مع تحذير.
    """
    if COL_EXPIRY_DATE not in df.columns:
        logger.warning(
            'العمود "%s" غير موجود — سيتم إرجاع جميع الصفوف بدون تصفية.',
            COL_EXPIRY_DATE,
        )
        return df

    df = df.copy()
    df[COL_EXPIRY_DATE] = pd.to_datetime(df[COL_EXPIRY_DATE], errors='coerce')
    today = pd.Timestamp(date.today())
    cutoff = today + pd.Timedelta(days=RENEWAL_DAYS)
    mask = (df[COL_EXPIRY_DATE] >= today) & (df[COL_EXPIRY_DATE] <= cutoff)
    renewals = df[mask].copy()
    logger.info('عدد التجديدات (تنتهي خلال %d يومًا): %d', RENEWAL_DAYS, len(renewals))
    return renewals


def get_policy_numbers(df: pd.DataFrame) -> list:
    """استخراج قائمة أرقام الوثائق من DataFrame."""
    if COL_POLICY_NO not in df.columns:
        # محاولة استخدام أول عمود إذا لم يُوجد العمود المحدد
        logger.warning(
            'العمود "%s" غير موجود — سيُستخدم العمود الأول كرقم الوثيقة.',
            COL_POLICY_NO,
        )
        col = df.columns[0]
    else:
        col = COL_POLICY_NO
    return df[col].astype(str).str.strip().tolist()


# ── منطق Playwright ───────────────────────────────────────────────────────────

async def login(page, base_url: str, username: str, password: str) -> None:
    """تسجيل الدخول إلى البوابة."""
    login_url = base_url.rstrip('/') + ESKA_LOGIN_PATH
    logger.info('الانتقال إلى صفحة تسجيل الدخول: %s', login_url)
    await page.goto(login_url, timeout=PAGE_TIMEOUT)
    await page.wait_for_load_state('networkidle', timeout=PAGE_TIMEOUT)

    if username:
        await page.fill(SEL_USERNAME_INPUT, username)
    await page.fill(SEL_PASSWORD_INPUT, password)
    await page.click(SEL_LOGIN_BUTTON)
    await page.wait_for_load_state('networkidle', timeout=PAGE_TIMEOUT)
    logger.info('تم تسجيل الدخول بنجاح')


async def fetch_contact(page, base_url: str, policy_no: str) -> dict:
    """
    البحث عن وثيقة وسحب بيانات التواصل.
    تُعيد قاموسًا يحتوي على: policy_no, phone, mobile, email.
    """
    result = {
        'رقم الوثيقة': policy_no,
        'هاتف': '',
        'جوال': '',
        'بريد إلكتروني': '',
        'ملاحظات': '',
    }

    try:
        search_url = base_url.rstrip('/') + ESKA_SEARCH_PATH
        await page.goto(search_url, timeout=PAGE_TIMEOUT)
        await page.wait_for_load_state('networkidle', timeout=PAGE_TIMEOUT)

        # كتابة رقم الوثيقة في حقل البحث
        await page.fill(SEL_SEARCH_INPUT, policy_no)
        await page.click(SEL_SEARCH_BUTTON)
        await page.wait_for_load_state('networkidle', timeout=PAGE_TIMEOUT)

        # سحب بيانات التواصل
        phone = await _safe_text(page, SEL_CLIENT_PHONE)
        mobile = await _safe_text(page, SEL_CLIENT_MOBILE)
        email = await _safe_text(page, SEL_CLIENT_EMAIL)

        result['هاتف'] = phone
        result['جوال'] = mobile
        result['بريد إلكتروني'] = email

    except PlaywrightTimeout:
        logger.warning('انتهت مهلة انتظار الوثيقة: %s', policy_no)
        result['ملاحظات'] = 'timeout'
    except Exception as exc:  # noqa: BLE001
        logger.error('خطأ أثناء معالجة الوثيقة %s: %s', policy_no, exc)
        result['ملاحظات'] = str(exc)

    return result


async def _safe_text(page, selector: str) -> str:
    """إعادة النص من أول عنصر يطابق المحدد، أو سلسلة فارغة إذا لم يُوجد."""
    try:
        el = page.locator(selector).first
        if await el.count() == 0:
            return ''
        return (await el.inner_text()).strip()
    except Exception:  # noqa: BLE001
        return ''


async def scrape_contacts(
    policy_numbers: list,
    base_url: str,
    username: str,
    portal_pass: str,
    headless: bool = True,
) -> list:
    """
    تسجيل الدخول وسحب بيانات التواصل لكل رقم وثيقة في القائمة.
    تُعيد قائمة من القواميس.
    """
    records = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(locale='ar-SA')
        page = await context.new_page()

        await login(page, base_url, username, portal_pass)

        total = len(policy_numbers)
        for idx, policy_no in enumerate(policy_numbers, start=1):
            logger.info('[%d/%d] سحب بيانات الوثيقة: %s', idx, total, policy_no)
            record = await fetch_contact(page, base_url, policy_no)
            records.append(record)

        await browser.close()

    return records


# ── الحفظ في إكسل ─────────────────────────────────────────────────────────────

def save_contacts(records: list, source_df: pd.DataFrame, out_path: str) -> None:
    """
    دمج بيانات التواصل مع بيانات الذمم وحفظها في ملف إكسل.
    """
    contacts_df = pd.DataFrame(records)

    # دمج مع ملف الذمم إذا توفّر عمود رقم الوثيقة
    if COL_POLICY_NO in source_df.columns:
        merged = source_df.merge(
            contacts_df,
            left_on=COL_POLICY_NO,
            right_on='رقم الوثيقة',
            how='left',
            suffixes=('', '_scraped'),
        )
    else:
        merged = contacts_df

    merged.to_excel(out_path, index=False, engine='openpyxl')
    logger.info('تم حفظ %d سجل في "%s"', len(merged), out_path)


# ── نقطة الدخول الرئيسية ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='سحب بيانات التواصل من بوابة إسكا لكل وثيقة في ملف الذمم.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('xls', help='مسار ملف الذمم (XLS أو XLSX)')
    parser.add_argument(
        '--renewals-only',
        action='store_true',
        help='سحب التجديدات فقط (الوثائق المنتهية خلال {} يومًا)'.format(RENEWAL_DAYS),
    )
    parser.add_argument(
        '--out',
        default='contacts.xlsx',
        help='مسار ملف الإخراج (الافتراضي: contacts.xlsx)',
    )
    parser.add_argument(
        '--url',
        default=ESKA_BASE_URL,
        help='رابط بوابة إسكا الأساسي',
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='تشغيل المتصفح بواجهة مرئية (للتشخيص)',
    )
    args = parser.parse_args()

    # التحقق من كلمة المرور
    portal_pass = os.environ.get('ESKA_PASS', '')
    if not portal_pass:
        sys.exit('خطأ: متغير البيئة ESKA_PASS غير مضبوط.')

    headless = not args.no_headless

    # تحميل الملف
    if not os.path.isfile(args.xls):
        sys.exit('خطأ: الملف "{}" غير موجود.'.format(args.xls))

    df = load_xls(args.xls)

    if args.renewals_only:
        df = filter_renewals(df)

    policy_numbers = get_policy_numbers(df)
    logger.info('إجمالي الوثائق المراد معالجتها: %d', len(policy_numbers))

    # سحب بيانات التواصل
    records = asyncio.run(
        scrape_contacts(
            policy_numbers,
            base_url=args.url,
            username=ESKA_USER,
            portal_pass=portal_pass,
            headless=headless,
        )
    )

    # الحفظ
    save_contacts(records, df, args.out)
    print('اكتمل — تم حفظ بيانات التواصل في: {}'.format(args.out))


if __name__ == '__main__':
    main()
