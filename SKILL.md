---
name: xhs-search
description: 小红书（Xiaohongshu/RED）内容搜索与笔记详情爬取工具。内置强大的反反爬/防风控机制（Stealth JS 注入、UA/视口轮换、模拟人类滚动与随机延迟）。适用于：(1) 按关键词搜索笔记，(2) 提取特定笔记完整内容及互动数据，(3) 通过批量模式（批量阅读不重启浏览器）高效采集小红书数据。
---

# Xhs Search

使用 Playwright 浏览器自动化从小红书抓取搜索结果和笔记详情的高级爬虫工具集。

🔥 **核心优势：**
- **强力反风控**：内置自动化检测绕过（Stealth JS）、随机 User-Agent/Viewport、真实人类行为模拟（自然滚动、随机操作等待）。
- **批量复用**：支持从文件读取 URL 列表进行批量采集，复用同一浏览器实例，大幅提高采集速度并降低封禁风险。

## 前置条件

安装依赖：

```bash
pip install -r scripts/requirements.txt
python -m playwright install chromium
```

## Cookie 获取

脚本需要小红书 Cookie 以获取完整数据。推荐获取步骤：

1. 在 Chrome 中打开 https://www.xiaohongshu.com 并登录
2. 按 F12 打开开发者工具 → Console（控制台）
3. 输入 `document.cookie` 并回车
4. 右键复制输出的完整字符串，保存到 `cookie.txt` 文件

## 工作流

### 搜索笔记

按关键词搜索小红书笔记列表，支持自动翻页：

```bash
python scripts/xhs_search.py --keyword "旅行攻略" --pages 2 --cookie-file cookie.txt --output results.json --delay 6
```

参数：
- `--keyword, -k`：搜索关键词（必填）
- `--pages, -p`：搜索页数，默认 1 页
- `--cookie, -c`：Cookie 字符串（建议存入文件）
- `--cookie-file`：Cookie 文件路径
- `--delay, -d`：翻页抓取的基础间隔秒数（默认 15，实际带有随机抖动）
- `--output, -o`：输出 JSON 文件路径
- `--no-headless`：显示浏览器窗口。遇到滑块验证码或“内容无法浏览”时必选，用于人工通过验证。

### 获取笔记详情（单篇与批量）

**单篇获取：**
```bash
python scripts/xhs_note_detail.py --url "https://www.xiaohongshu.com/explore/笔记ID" --cookie-file cookie.txt --output note.json
# 或根据笔记 ID 抓取
python scripts/xhs_note_detail.py --note-id "笔记ID" --cookie-file cookie.txt
```

**批量获取（推荐用于大规模采集）：**
1. 准备包含 URL 的纯文本文件 `urls.txt`，每行一个链接
2. 执行批量命令（脚本会只打开一个浏览器，按设定间隔逐个抓取）

```bash
python scripts/xhs_note_detail.py --urls-file urls.txt --delay 8 --cookie-file cookie.txt --output batch_results.json
```

参数：
- `--url, -u`：单篇笔记 URL
- `--note-id, -n`：单篇笔记 ID
- `--urls-file`：包含多个 URL 的批量读取文件（与单篇参数互斥）
- `--cookie, -c` / `--cookie-file`：认证所需 Cookie
- `--delay, -d`：笔记之间的访问间隔时间，默认 15 秒（加入随机抖动）
- `--output, -o`：输出 JSON 文件路径
- `--no-headless`：显示浏览器窗口。配合人工手动过验证码以突破风控。

## 数据结构

获取到的精确数据结构以及各字段说明参考 [xhs_data_structure.md](references/xhs_data_structure.md)。

## ⚠️ 防风控注意事项

1. **Cookie 时效**：Cookie 有效期通常为 7-30 天，过期或频繁异常操作会导致失效注销，需重新获取。
2. **访问间隔机制**：使用 `--delay` 控制总体爬取节奏。如果风控较严，建议提高参数至 `--delay 8` 或 `--delay 10`。此参数是"基准"时间，脚本在此基础上会自动加入随机秒数的自然等待及人类仿生操作时间。
3. **验证码阻塞与“无法浏览”拦截**：如果无头模式下出现“当前笔记暂时无法浏览”或抓取超时，请务必开启 `--no-headless`。运行过程中如弹出图形验证码，请**手动滑过**。验证码通过后，脚本会自动继续后续的采集流程。
4. **人工协助**：在批量高频采集时，建议开启提示窗口，随时准备应对偶发的安全查验。
5. 仅用于个人学习研究，请合理控制频率，遵守网站相关规则及法律法规。
