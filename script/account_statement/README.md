# GitHub Account Statement Generator
> 兴趣是最好的老师，[HelloGitHub](https://github.com/521xueweihan/HelloGitHub) 就是帮你找到兴趣！

该脚本用于生成一个或多个 GitHub 用户的**账户报告（Account Statement）**，内容包括：

- 用户基本信息（头像、简介、关注者/关注数、公开仓库数量、地点、公司）
- 公开仓库列表（按 Star 数量降序，默认展示前 10 名）
- 最近公开活动事件（默认展示最近 20 条）

报告以 HTML 文件形式保存，支持同时为主账户和备用账户生成报告。

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

   示例：
   ```bash
   python account_statement.py torvalds gvanrossum --output-dir /tmp/statements
   ```

4. 生成的 HTML 文件保存在脚本所在目录（或 `--output-dir` 指定的目录），文件名格式为：
   `statement_<username>.html`

## 参数说明

| 参数 | 说明 |
|------|------|
| `usernames` | 一个或多个 GitHub 用户名（空格分隔） |
| `--output-dir` | 输出目录（可选，默认为脚本所在目录） |

## 配置项

可在 `account_statement.py` 中调整以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TOP_REPOS` | `10` | 报告中展示的最多仓库数量 |
| `RECENT_EVENTS` | `20` | 报告中展示的最多活动事件数量 |
