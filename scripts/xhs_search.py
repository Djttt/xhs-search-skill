#!/usr/bin/env python3
"""
小红书搜索脚本 - 使用 Playwright 搜索小红书笔记

Usage:
    python xhs_search.py --keyword "关键词" [--pages 1] [--cookie "cookie字符串"] [--output results.json]

Examples:
    python xhs_search.py --keyword "旅行攻略" --pages 2
    python xhs_search.py --keyword "美食推荐" --cookie "从浏览器复制的cookie" --output food.json
    python xhs_search.py --keyword "穿搭" --delay 8 --pages 3  # 更保守的间隔
"""

import argparse
import json
import sys
import time
import re
import random
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ 请先安装 playwright: pip install playwright && python -m playwright install chromium")
    sys.exit(1)


# --- 反检测 ---

STEALTH_JS = """
// 隐藏 webdriver 标记
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 伪造 plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// 伪造 languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en'],
});

// 隐藏 Playwright/headless 痕迹
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);

// 伪造 Chrome runtime
window.chrome = { runtime: {} };
"""

# 多个真实 User-Agent，随机选择
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15',
]

# 随机视口尺寸
VIEWPORTS = [
    {'width': 1440, 'height': 900},
    {'width': 1536, 'height': 864},
    {'width': 1920, 'height': 1080},
    {'width': 1366, 'height': 768},
]


def human_delay(base=2.0, jitter=1.5):
    """模拟人类操作的随机延迟"""
    delay = base + random.uniform(0, jitter)
    time.sleep(delay)


def human_scroll(page, times=3):
    """模拟人类滚动行为：随机速度和距离"""
    for i in range(times):
        scroll_distance = random.randint(300, 600)
        page.mouse.wheel(0, scroll_distance)
        time.sleep(random.uniform(0.8, 2.0))


def create_stealth_context(playwright_instance, cookie=None, headless=True):
    """创建带反检测的浏览器上下文"""
    browser = playwright_instance.chromium.launch(
        headless=headless,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--no-first-run',
        ],
    )

    ua = random.choice(USER_AGENTS)
    vp = random.choice(VIEWPORTS)

    context = browser.new_context(
        user_agent=ua,
        viewport=vp,
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        color_scheme='light',
    )

    # 注入反检测脚本（在每个新页面加载前执行）
    context.add_init_script(STEALTH_JS)

    # 设置 Cookie
    if cookie:
        cookies = []
        for item in cookie.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.xiaohongshu.com',
                    'path': '/',
                })
        context.add_cookies(cookies)

    return browser, context


def parse_search_results(page):
    """从搜索页面解析笔记列表"""
    results = []

    # 等待搜索结果加载
    try:
        page.wait_for_selector('section.note-item, div.note-item, a.cover', timeout=15000)
        human_delay(1.5, 1.0)
    except Exception:
        print("⚠️ 搜索结果加载超时，尝试解析当前页面...")

    # 模拟人类滚动
    human_scroll(page, times=random.randint(2, 4))

    # 尝试多种选择器提取笔记卡片
    note_items = page.query_selector_all('section.note-item')
    if not note_items:
        note_items = page.query_selector_all('div[class*="note-item"]')
    if not note_items:
        note_items = page.query_selector_all('div.feeds-container section')

    for item in note_items:
        try:
            note = {}

            # 提取笔记链接和 ID
            link_el = item.query_selector('a[href*="/explore/"], a[href*="/search_result/"]')
            if not link_el:
                link_el = item.query_selector('a.cover, a[href*="xhslink"]')

            if link_el:
                href = link_el.get_attribute('href') or ''
                note['url'] = href if href.startswith('http') else f'https://www.xiaohongshu.com{href}'
                id_match = re.search(r'/([a-f0-9]{24})', href)
                if id_match:
                    note['note_id'] = id_match.group(1)

            # 提取标题
            title_el = item.query_selector('span.title, div.title, a.title')
            if title_el:
                note['title'] = title_el.inner_text().strip()

            # 提取封面图
            img_el = item.query_selector('img')
            if img_el:
                note['cover_image'] = img_el.get_attribute('src') or ''

            # 提取作者信息
            author_el = item.query_selector('span.author-wrapper span.name, div.author-wrapper span, span.name')
            if author_el:
                note['author'] = author_el.inner_text().strip()

            # 提取点赞数
            like_el = item.query_selector('span.like-wrapper span.count, span.count, span[class*="like"]')
            if like_el:
                note['likes'] = like_el.inner_text().strip()

            # 提取笔记类型标记
            video_icon = item.query_selector('svg.play-icon, span.play-icon, div[class*="video"]')
            note['type'] = '视频' if video_icon else '图文'

            if note.get('title') or note.get('url'):
                results.append(note)

        except Exception as e:
            print(f"⚠️ 解析某条笔记时出错: {e}")
            continue

    return results


def search_xiaohongshu(keyword, pages=1, cookie=None, headless=True, delay=15):
    """
    搜索小红书笔记

    Args:
        keyword: 搜索关键词
        pages: 搜索页数（默认1页）
        cookie: 小红书 Cookie 字符串
        headless: 是否无头模式运行
        delay: 翻页基础间隔秒数（默认15秒，实际为 delay ± 随机抖动）

    Returns:
        list: 搜索结果列表
    """
    all_results = []

    with sync_playwright() as p:
        browser, context = create_stealth_context(p, cookie=cookie, headless=headless)
        page = context.new_page()

        try:
            # 先访问首页建立会话，模拟正常浏览
            print(f"🔍 正在搜索: {keyword}")
            page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=30000)
            human_delay(3.0, 2.0)  # 首页停留 3~5 秒

            # 模拟首页浏览行为
            human_scroll(page, times=1)
            human_delay(1.0, 1.0)

            for page_num in range(1, pages + 1):
                print(f"📄 正在抓取第 {page_num}/{pages} 页...")

                import urllib.parse
                encoded_keyword = urllib.parse.quote(keyword)
                search_url = f'https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_search_result_notes'

                if page_num > 1:
                    search_url += f'&page={page_num}'

                page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                human_delay(3.0, 2.0)  # 页面加载后等待 3~5 秒

                # 解析搜索结果
                results = parse_search_results(page)
                print(f"   找到 {len(results)} 条结果")
                all_results.extend(results)

                # 翻页间隔：使用 delay 参数 + 随机抖动
                if page_num < pages:
                    wait_time = delay + random.uniform(0, delay * 0.5)
                    print(f"   ⏳ 等待 {wait_time:.1f} 秒后翻页...")
                    time.sleep(wait_time)

        except Exception as e:
            print(f"❌ 搜索出错: {e}")
        finally:
            browser.close()

    # 去重
    seen_urls = set()
    unique_results = []
    for r in all_results:
        url = r.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)

    return unique_results


def main():
    parser = argparse.ArgumentParser(description='小红书搜索工具')
    parser.add_argument('--keyword', '-k', required=True, help='搜索关键词')
    parser.add_argument('--pages', '-p', type=int, default=1, help='搜索页数（默认1页）')
    parser.add_argument('--cookie', '-c', default=None, help='小红书 Cookie 字符串')
    parser.add_argument('--cookie-file', default=None, help='包含 Cookie 的文件路径')
    parser.add_argument('--output', '-o', default=None, help='输出文件路径（JSON格式）')
    parser.add_argument('--delay', '-d', type=float, default=15, help='翻页基础间隔秒数（默认15秒）')
    parser.add_argument('--no-headless', action='store_true', help='显示浏览器窗口（调试用）')

    args = parser.parse_args()

    # 读取 Cookie
    cookie = args.cookie
    if args.cookie_file:
        cookie_path = Path(args.cookie_file)
        if cookie_path.exists():
            cookie = cookie_path.read_text().strip()
        else:
            print(f"❌ Cookie 文件不存在: {args.cookie_file}")
            sys.exit(1)

    # 执行搜索
    results = search_xiaohongshu(
        keyword=args.keyword,
        pages=args.pages,
        cookie=cookie,
        headless=not args.no_headless,
        delay=args.delay,
    )

    print(f"\n✅ 共获取 {len(results)} 条搜索结果")

    # 输出结果
    output_data = {
        'keyword': args.keyword,
        'total_results': len(results),
        'results': results,
    }

    if not args.output:
        data_dir = Path(__file__).parent.parent / 'data'
        data_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        clean_keyword = "".join(c for c in args.keyword if c.isalnum() or c in ('_', '-'))
        args.output = str(data_dir / f"search_{clean_keyword}_{timestamp}.json")

    output_path = Path(args.output)
    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    print(f"📁 结果已保存到: {args.output}")


if __name__ == '__main__':
    main()
