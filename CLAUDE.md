# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

HelloGitHub is a curated monthly magazine (updated on the **28th of each month**) that shares interesting, beginner-friendly open-source projects from GitHub. It is not a software application — it is a content repository. There are no build steps, test suites, or dependency managers.

## Repository Structure

- `content/` — Chinese-language monthly issues (`HelloGitHub01.md` through `HelloGitHub120.md`)
- `content/en/` — English translations of issues
- `content/contributors.md` — List of contributors whose projects have been included
- `AIG/` — A separate set of static HTML prototype files for an AIG Insurance Portal (unrelated to the monthly magazine)
- `.github/ISSUE_TEMPLATE/` — Issue templates for project submissions (one in Chinese, one in English)

## Content Format

Each monthly issue follows this structure:

```markdown
# 《HelloGitHub》第 N 期

## 目录
[table of contents instructions]

## 内容
> **以下为本期内容**｜每月 **28** 号更新

### [Category] 项目
N、[project-name](https://hellogithub.com/periodical/statistics/click?target=https://github.com/owner/repo)：[description in Chinese]

<p align="center"><img src='...' style="max-width:80%; max-height=80%;"></img></p>
```

Project links always go through the hellogithub.com statistics redirect URL (not directly to GitHub). Images are hosted on `raw.githubusercontent.com/521xueweihan/img*`.

## Project Submission

New projects are submitted via GitHub Issues using the templates in `.github/ISSUE_TEMPLATE/`. Categories accepted: C, C#, C++, CSS, Go, Java, JS, Kotlin, Objective-C, PHP, Python, Ruby, Rust, Swift, Other, Books, Machine Learning/AI.

The project review guidelines are at: https://github.com/521xueweihan/HelloGitHub/issues/271

## Contribution Workflow

1. Contributors submit projects via the issue templates
2. Accepted projects are added to the next monthly issue file under `content/`
3. Contributors' GitHub usernames are added to `content/contributors.md`

## License

Content is published under **CC BY-NC-ND 4.0** — non-commercial, no derivatives, attribution required.

## AIG Insurance Portal (AIG/)

The `AIG/` directory contains standalone HTML prototype files for an insurance management portal. These are self-contained files with inline CSS and no build process:

- `AIG/SSO/Login/GUI/Frmlogin.html` — Login page
- `AIG/Insurance/GUI/FrmInsurance.html` — Main insurance dashboard
- `AIG/Insurance/Claims/GUI/FrmClaims.html` — Claims management
- `AIG/Insurance/Customer/GUI/FrmCustomer.html` — Customer management
- `AIG/Insurance/Policy/GUI/FrmPolicy.html` — Policy management

These files can be opened directly in a browser; there is no server or framework involved.
