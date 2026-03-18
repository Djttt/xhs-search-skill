# Xhs Search (小红书内容爬虫与搜索工具)

使用 Playwright 浏览器自动化从小红书抓取搜索结果和笔记详情的高级爬虫工具集。

🔥 **核心优势：**
- **强力反风控**：内置自动化检测绕过（Stealth JS）、随机 User-Agent/Viewport、真实人类行为模拟（自然滚动、随机操作等待）。
- **批量复用**：支持从文件读取 URL 列表进行批量采集，复用同一浏览器实例，大幅提高采集速度并降低封禁风险。

## 前置条件

安装 Python 依赖：

```bash
pip install -r scripts/requirements.txt
```

安装无头浏览器及相关依赖（首次运行需执行）：
```bash
python -m playwright install chromium
```

## Cookie 获取

脚本需要小红书 Cookie 以绕过反爬获取完整的主页面数据。推荐的获取步骤：

1. 在 Chrome 等桌面端浏览器中打开 https://www.xiaohongshu.com 并登录您的账号。
2. 按 `F12` 打开开发者工具，切换至 `Console`（控制台）。
3. 输入 `document.cookie` 并回车。
4. 右键复制输出的两端不含引号的完整字符串内容，保存到项目根目录下的 `cookie.txt` 文件。

## 功能与用法指引

### 1. 按关键词搜索笔记

按关键词搜索小红书笔记列表，支持自动翻页：

```bash
python scripts/xhs_search.py --keyword "旅行攻略" --pages 2 --cookie-file cookie.txt --output data/results.json --delay 6
```

**可选参数：**
- `--keyword, -k`：搜索关键词（必须）
- `--pages, -p`：搜索总页数（默认 1）
- `--cookie, -c`：Cookie 字符串
- `--cookie-file`：包含 Cookie 字符串的文件路径（推荐方式）
- `--delay, -d`：翻页抓取的基础间隔秒数（默认 15 秒，系统会基于此增加随机抖动以规避风控机器检测）
- `--output, -o`：输出 JSON 结果的保存文件路径
- `--no-headless`：不隐藏控制台，在前端显示浏览器真实模拟窗口（主要用于调试操作）

### 2. 爬取笔记详情 (单篇及批量模式)

**提取单篇笔记：**
```bash
# 通过 URL 获取
python scripts/xhs_note_detail.py --url "https://www.xiaohongshu.com/explore/笔记ID" --cookie-file cookie.txt --output data/note.json

# 或是直接通过笔记 ID 获取
python scripts/xhs_note_detail.py --note-id "笔记ID" --cookie-file cookie.txt
```

**批量获取（高效率推荐用于大规模采集）：**
1. 准备包含多条笔记 URL 的纯文本文件 `urls.txt`，每行包含一个小红书链接。
2. 运行批量模式命令（该模式下只会冷启动一次浏览器，后续所有的爬取都会在这个保持住 Cookie 的会话中完成，具有更高性能并降低封禁率）。

```bash
python scripts/xhs_note_detail.py --urls-file urls.txt --delay 8 --cookie-file cookie.txt --output data/batch_results.json
```

**可选参数：**
- `--url, -u`：单篇笔记 URL
- `--note-id, -n`：单篇笔记 ID
- `--urls-file`：包含多个 URL 的行分隔列表文件路径（一旦开启此项，单篇抓取参数将被忽略）
- `--cookie, -c` / `--cookie-file`：必须有的平台认证 Cookie
- `--delay, -d`：访问多篇不同笔记的请求间隔等待时间，默认为 15 秒
- `--output, -o`：输出抓取笔记明细信息的存放文件
- `--no-headless`：显示浏览器窗口页面

## ⚠️ 防风控注意事项

1. **Cookie 失效**：平台 Cookie 的有效期短至几天。如果发现运行报错、卡住无响应或结果中均为“需要验证用户”，请首先检查是不是该 Cookie 过期失效，需要再次登录重新截取复制替换。
2. **频率请求设置**：切勿过度急躁地将延迟 `--delay` 调零。当发现爬取过程触发了频繁的安全校验时，务必将该参数的秒数调大至 8 或至少 10，给平台一种人在慢节奏地划动笔记的错觉。
3. **验证码阻塞**：一旦无头模式频频失利拿不到内容（例如遇到页面要求强行打码等图形防刷），此时需紧急调出 `--no-headless`。遇到验证码界面人工地滑过确认之后程序又能继续畅行无阻。
4. **合法合规**：本项目中的操作方案及工具抓取逻辑仅做技术演示及测试，研究交流相关信息安全、机器防风控用等，严禁滥用该功能进行任何非法的信息大宗获取和不当盈利等违法操作。
