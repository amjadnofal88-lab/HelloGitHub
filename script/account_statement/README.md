# Account Statement Tools

---

## commission_report.py — كشف العمولة المحتجزة

يقرأ كشف حساب الأهلية (PDF) ويحسب العمولة المحتجزة بناءً على نسبة تعاقدية،
ثم يولّد خطة دفعات ويصدرها إلى مصنف إكسل عربي RTL.

### الميزات

- احتساب العمولة المحتجزة من كشف الحساب
- خطة دفعات بعدد محدد أو مبلغ ثابت لكل دفعة
- تصدير إكسل: ورقة الاحتساب + ورقة الدفعات (RTL، عربي)
- جميع البيانات الحساسة (IBAN، المستفيد، البنك) من متغيرات البيئة فقط

### الاستخدام

```bash
# 12 دفعة شهرية
python commission_report.py statement.pdf --installments 12

# مبلغ ثابت 5000₪ لكل دفعة
python commission_report.py statement.pdf --amount-per 5000

# نسبة مخصصة + تحديد ملف الإخراج
python commission_report.py statement.pdf --rate 0.27 --installments 6 -o plan.xlsx

# أيام مخصصة بين الدفعات (افتراضي 30)
python commission_report.py statement.pdf --installments 4 --every 45
```

### المعاملات

| المعامل | الوصف |
|---------|-------|
| `pdf` | مسار ملف PDF لكشف الحساب |
| `--rate` | نسبة العمولة (مثال: `0.27`). إذا لم تُحدَّد تُقرأ من `COMMISSION_RATES` |
| `--installments` | عدد الدفعات |
| `--amount-per` | مبلغ ثابت لكل دفعة (بالشيكل) |
| `--every` | أيام بين الدفعات (افتراضي: `30`) |
| `--start` | تاريخ أول دفعة `YYYY-MM-DD` |
| `-o` / `--output` | مسار ملف الإخراج `.xlsx` |

### متغيرات البيئة

| المتغير | الوصف |
|---------|-------|
| `COMMISSION_RATES` | نسب العمولة لكل حساب (JSON) مثال: `'{"475151": 0.27}'` |
| `BENEFICIARY_NAME` | اسم المستفيد (يظهر في ورقة الاحتساب والبيان) |
| `BENEFICIARY_BANK` | اسم البنك (يظهر في ورقة الاحتساب) |

---

## GitHub Account Statement Generator
> 兴趣是最好的老师，[HelloGitHub](https://github.com/521xueweihan/HelloGitHub) 就是帮你找到兴趣！

该脚本用于生成一个或多个 GitHub 用户的**账户报告（Account Statement）**，内容包括：

- 用户基本信息（头像、简介、关注者/关注数、公开仓库数量、地点、公司）
- 公开仓库列表（按 Star 数量降序，默认展示前 10 名）
- 最近公开活动事件（默认展示最近 20 条）

报告以 HTML 文件形式保存，支持同时为主账户和备用账户生成报告。
使用 `--excel` 标志可额外生成一个包含三个工作表的 `.xlsx` 文件。

## 运行步骤

1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **（可选）配置 GitHub 认证**（提高 API 速率限制，从 60 次/小时 提升至 5000 次/小时）：

   通过环境变量传入 Personal Access Token：
   ```bash
   export GITHUB_TOKEN=your_personal_access_token
   ```

3. **运行脚本**：

   生成单个用户的账户报告：
   ```bash
   python account_statement.py <username>
   ```

   同时生成主账户和备用账户的报告：
   ```bash
   python account_statement.py <primary_username> <alternative_username>
   ```

   指定输出目录：
   ```bash
   python account_statement.py <username> --output-dir /path/to/output
   ```

   将报告同时导出到 iCloud Drive（macOS 专属）：
   ```bash
   python account_statement.py <username> --icloud
   ```

   自定义 iCloud Drive 子文件夹名称（默认为 `GitHub Statements`）：
   ```bash
   python account_statement.py <username> --icloud --icloud-folder "My Reports"
   ```

   额外生成 Excel (.xlsx) 报告（包含 Profile、Repositories、Recent Activity 三个工作表）：
   ```bash
   python account_statement.py <username> --excel
   ```

   同时生成 HTML 和 Excel 并导出到 iCloud Drive：
   ```bash
   python account_statement.py <username> --excel --icloud
   ```

   示例：
   ```bash
   python account_statement.py torvalds gvanrossum --output-dir /tmp/statements
   ```

4. 生成的 HTML 文件（以及可选的 `.xlsx` 文件）保存在脚本所在目录（或 `--output-dir` 指定的目录），文件名格式为：
   `statement_<username>.html` / `statement_<username>.xlsx`

## 参数说明

| 参数 | 说明 |
|------|------|
| `usernames` | 一个或多个 GitHub 用户名（空格分隔） |
| `--output-dir` | 输出目录（可选，默认为脚本所在目录） |
| `--icloud` | 将生成的报告额外复制到 iCloud Drive（仅 macOS） |
| `--icloud-folder` | iCloud Drive 子文件夹名称（默认：`GitHub Statements`，仅与 `--icloud` 搭配使用） |
| `--excel` | 额外生成 `.xlsx` 工作簿（包含 Profile、Repositories、Recent Activity 三个工作表） |

## 环境变量

| 变量 | 说明 |
|------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token，用于提高 API 速率限制 |
| `ICLOUD_DRIVE_PATH` | 覆盖默认的 iCloud Drive 路径（默认：`~/Library/Mobile Documents/com~apple~CloudDocs`） |

## 配置项

可在 `account_statement.py` 中调整以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TOP_REPOS` | `10` | 报告中展示的最多仓库数量 |
| `RECENT_EVENTS` | `20` | 报告中展示的最多活动事件数量 |
