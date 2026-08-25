# GitHub Account Statement Generator
> 兴趣是最好的老师，[HelloGitHub](https://github.com/521xueweihan/HelloGitHub) 就是帮你找到兴趣！

该脚本用于生成一个或多个 GitHub 用户的**账户报告（Account Statement）**，内容包括：

- 用户基本信息（头像、简介、关注者/关注数、公开仓库数量、地点、公司）
- 公开仓库列表（按 Star 数量降序，默认展示前 10 名）
- 最近公开活动事件（默认展示最近 20 条）

报告支持 HTML 和 Excel（.xlsx）两种格式，支持同时为主账户和备用账户生成报告。

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

   导出到 iCloud Drive（仅 macOS）：
   ```bash
   python account_statement.py <username> --icloud
   ```
   文件将复制到 `~/Library/Mobile Documents/com~apple~CloudDocs/Ahleia Reports/`。

   同时生成 Excel 电子表格（.xlsx）：
   ```bash
   python account_statement.py <username> --excel
   ```
   Excel 文件包含三个工作表：**Profile**（用户信息）、**Repositories**（仓库列表）、**Recent Activity**（近期活动）。

   组合使用（生成 HTML + Excel，并同步到 iCloud）：
   ```bash
   python account_statement.py <username> --excel --icloud
   ```

   示例：
   ```bash
   python account_statement.py torvalds gvanrossum --output-dir /tmp/statements
   python account_statement.py torvalds --excel
   python account_statement.py torvalds --excel --icloud
   ```

4. 生成的文件保存在脚本所在目录（或 `--output-dir` 指定的目录），文件名格式为：
   - HTML：`statement_<username>.html`
   - Excel：`statement_<username>.xlsx`

## 参数说明

| 参数 | 说明 |
|------|------|
| `usernames` | 一个或多个 GitHub 用户名（空格分隔） |
| `--output-dir` | 输出目录（可选，默认为脚本所在目录） |
| `--excel` | 额外生成 Excel（.xlsx）电子表格，包含 Profile、Repositories、Recent Activity 三个工作表 |
| `--icloud` | 将生成的文件额外复制到 iCloud Drive 的 `Ahleia Reports` 文件夹（仅 macOS） |

## 配置项

可在 `account_statement.py` 中调整以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TOP_REPOS` | `10` | 报告中展示的最多仓库数量 |
| `RECENT_EVENTS` | `20` | 报告中展示的最多活动事件数量 |
