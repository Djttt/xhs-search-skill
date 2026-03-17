#!/usr/bin/env python3
"""
小红书笔记详情抓取脚本 - 使用 Playwright 获取笔记完整内容

Usage:
    python xhs_note_detail.py --url "笔记URL" [--cookie "cookie字符串"] [--output note.json]
    python xhs_note_detail.py --note-id "笔记ID" [--cookie "cookie字符串"]

Examples:
    python xhs_note_detail.py --url "https://www.xiaohongshu.com/explore/6xxxxx"
    python xhs_note_detail.py --note-id "6xxxxx" --output note_detail.json
    python xhs_note_detail.py --note-id "6xxxxx" --delay 8  # 更保守的间隔
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


# --- 反检测（与 xhs_search.py 保持一致） ---

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en'],
});
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);
window.chrome = { runtime: {} };
"""

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15',
]

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
    """模拟人类滚动行为"""
    for i in range(times):
        scroll_distance = random.randint(200, 500)
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

    context = browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport=random.choice(VIEWPORTS),
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        color_scheme='light',
    )

    context.add_init_script(STEALTH_JS)

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


def extract_note_detail(page):
    """从笔记页面提取详细信息"""
    note = {}

    try:
        page.wait_for_selector('#detail-cnt, div.note-detail, div[class*="note-content"]', timeout=15000)
        human_delay(1.5, 1.0)
    except Exception:
        print("⚠️ 笔记内容加载超时，尝试解析当前页面...")

    # 模拟人类阅读：慢慢滚动浏览
    human_scroll(page, times=random.randint(1, 2))

    # 提取标题
    title_selectors = [
        '#detail-title',
        'div.title',
        'div[class*="note-content"] div.title',
        'h1',
    ]
    for sel in title_selectors:
        el = page.query_selector(sel)
        if el:
            note['title'] = el.inner_text().strip()
            break

    # 提取正文内容
    content_selectors = [
        '#detail-desc span, #detail-desc',
        'div.desc span, div.desc',
        'div[class*="note-text"]',
        'div.content span',
    ]
    for sel in content_selectors:
        els = page.query_selector_all(sel)
        if els:
            texts = []
            for el in els:
                text = el.inner_text().strip()
                if text:
                    texts.append(text)
            if texts:
                note['content'] = '\n'.join(texts)
                break

    # 提取标签/话题
    tag_selectors = [
        'a.tag, a[class*="tag"]',
        '#detail-desc a[href*="search"]',
        'a[href*="page/topics"]',
    ]
    tags = []
    for sel in tag_selectors:
        tag_els = page.query_selector_all(sel)
        for tag_el in tag_els:
            tag_text = tag_el.inner_text().strip()
            if tag_text and tag_text.startswith('#'):
                tags.append(tag_text)
    if tags:
        note['tags'] = list(set(tags))

    # 提取作者信息
    author_selectors = [
        'div.author-container span.username, a.username',
        'div[class*="author"] span.name',
        'span.username',
    ]
    for sel in author_selectors:
        el = page.query_selector(sel)
        if el:
            note['author'] = el.inner_text().strip()
            break

    # 提取作者头像
    avatar_el = page.query_selector('div.author-container img, a.avatar img')
    if avatar_el:
        note['author_avatar'] = avatar_el.get_attribute('src') or ''

    # 提取互动数据
    interaction_data = {}

    like_selectors = [
        'span.like-wrapper span.count',
        'span[class*="like"] span.count',
        'div.interactions span.like span',
    ]
    for sel in like_selectors:
        el = page.query_selector(sel)
        if el:
            interaction_data['likes'] = el.inner_text().strip()
            break

    collect_selectors = [
        'span.collect-wrapper span.count',
        'span[class*="collect"] span.count',
    ]
    for sel in collect_selectors:
        el = page.query_selector(sel)
        if el:
            interaction_data['collects'] = el.inner_text().strip()
            break

    comment_selectors = [
        'span.chat-wrapper span.count',
        'span[class*="comment"] span.count',
        'span[class*="chat"] span.count',
    ]
    for sel in comment_selectors:
        el = page.query_selector(sel)
        if el:
            interaction_data['comments'] = el.inner_text().strip()
            break

    if interaction_data:
        note['interactions'] = interaction_data

    # 提取图片列表
    images = []
    img_selectors = [
        'div.swiper-slide img, div[class*="slide"] img',
        'div.carousel img',
        'div[class*="image-container"] img',
    ]
    for sel in img_selectors:
        img_els = page.query_selector_all(sel)
        for img_el in img_els:
            src = img_el.get_attribute('src') or ''
            if src and 'avatar' not in src:
                images.append(src)

    if images:
        note['images'] = list(dict.fromkeys(images))

    # 提取视频链接
    video_el = page.query_selector('video source, video')
    if video_el:
        video_src = video_el.get_attribute('src') or ''
        if video_src:
            note['video_url'] = video_src
            note['type'] = '视频'
    else:
        note['type'] = '图文'

    # 提取发布时间
    time_selectors = [
        'span.date, span[class*="date"]',
        'span.time, span[class*="time"]',
        'div.bottom-container span',
    ]
    for sel in time_selectors:
        el = page.query_selector(sel)
        if el:
            time_text = el.inner_text().strip()
            if time_text and any(c.isdigit() for c in time_text):
                note['publish_time'] = time_text
                break

    # 提取 IP 归属地
    ip_el = page.query_selector('span.ip-container, span[class*="location"]')
    if ip_el:
        note['ip_location'] = ip_el.inner_text().strip()

    # 尝试从页面脚本中提取结构化数据
    try:
        json_data = page.evaluate('''() => {
            const scripts = document.querySelectorAll('script');
            for (const script of scripts) {
                const text = script.textContent;
                if (text && text.includes('__INITIAL_STATE__')) {
                    const match = text.match(/__INITIAL_STATE__\\s*=\\s*({.*?})\\s*;?$/m);
                    if (match) {
                        try { return JSON.parse(match[1]); } catch(e) {}
                    }
                }
            }
            return null;
        }''')

        if json_data and 'note' in json_data:
            note_data = json_data.get('note', {}).get('noteDetailMap', {})
            for key, val in note_data.items():
                detail = val.get('note', {})
                if detail:
                    if not note.get('title') and detail.get('title'):
                        note['title'] = detail['title']
                    if not note.get('content') and detail.get('desc'):
                        note['content'] = detail['desc']
                    if detail.get('interactInfo'):
                        info = detail['interactInfo']
                        note['interactions'] = {
                            'likes': str(info.get('likedCount', '')),
                            'collects': str(info.get('collectedCount', '')),
                            'comments': str(info.get('commentCount', '')),
                            'shares': str(info.get('shareCount', '')),
                        }
                    if detail.get('tagList'):
                        note['tags'] = [f"#{t.get('name', '')}" for t in detail['tagList']]
                    if detail.get('imageList') and not note.get('images'):
                        note['images'] = [
                            img.get('urlDefault', '') or img.get('url', '')
                            for img in detail['imageList']
                        ]
                    break
    except Exception as e:
        pass

    return note


def get_note_detail(url, cookie=None, headless=True, delay=15):
    """
    获取小红书笔记详情

    Args:
        url: 笔记 URL
        cookie: 小红书 Cookie 字符串
        headless: 是否无头模式
        delay: 访问前等待基础秒数

    Returns:
        dict: 笔记详情
    """
    with sync_playwright() as p:
        browser, context = create_stealth_context(p, cookie=cookie, headless=headless)
        page = context.new_page()

        try:
            # 先访问首页建立会话
            print(f"📖 正在获取笔记详情: {url}")
            page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=30000)
            human_delay(3.0, 2.0)

            # 模拟首页浏览
            human_scroll(page, times=1)
            human_delay(1.0, 1.0)

            # 访问目标笔记
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            human_delay(3.0, 2.0)

            note = extract_note_detail(page)
            note['url'] = url

            id_match = re.search(r'/([a-f0-9]{24})', url)
            if id_match:
                note['note_id'] = id_match.group(1)

            return note

        except Exception as e:
            print(f"❌ 获取笔记详情出错: {e}")
            return {'url': url, 'error': str(e)}
        finally:
            browser.close()


def get_batch_note_details(urls, cookie=None, headless=True, delay=15):
    """
    批量获取多篇笔记详情（复用同一浏览器实例，更高效）

    Args:
        urls: 笔记 URL 列表
        cookie: 小红书 Cookie 字符串
        headless: 是否无头模式
        delay: 每篇笔记之间的基础间隔秒数

    Returns:
        list[dict]: 笔记详情列表
    """
    results = []

    with sync_playwright() as p:
        browser, context = create_stealth_context(p, cookie=cookie, headless=headless)
        page = context.new_page()

        try:
            # 先访问首页建立会话
            print(f"📦 批量获取 {len(urls)} 篇笔记详情")
            page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=30000)
            human_delay(3.0, 2.0)
            human_scroll(page, times=1)

            for i, url in enumerate(urls):
                print(f"\n📖 [{i + 1}/{len(urls)}] {url}")

                # 笔记间随机延迟
                if i > 0:
                    wait_time = delay + random.uniform(0, delay * 0.6)
                    print(f"   ⏳ 等待 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)

                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    human_delay(3.0, 2.0)

                    note = extract_note_detail(page)
                    note['url'] = url

                    id_match = re.search(r'/([a-f0-9]{24})', url)
                    if id_match:
                        note['note_id'] = id_match.group(1)

                    results.append(note)
                    print(f"   ✅ {note.get('title', '(无标题)')}")

                except Exception as e:
                    print(f"   ❌ 抓取失败: {e}")
                    results.append({'url': url, 'error': str(e)})

        except Exception as e:
            print(f"❌ 批量抓取出错: {e}")
        finally:
            browser.close()

    return results


def main():
    parser = argparse.ArgumentParser(description='小红书笔记详情抓取工具')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--url', '-u', help='笔记 URL（单篇）')
    group.add_argument('--note-id', '-n', help='笔记 ID（单篇）')
    group.add_argument('--urls-file', help='批量 URL 文件路径（每行一个 URL）')

    parser.add_argument('--cookie', '-c', default=None, help='小红书 Cookie 字符串')
    parser.add_argument('--cookie-file', default=None, help='包含 Cookie 的文件路径')
    parser.add_argument('--output', '-o', default=None, help='输出文件路径（JSON格式）')
    parser.add_argument('--delay', '-d', type=float, default=15, help='请求间隔基础秒数（默认15秒）')
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

    headless = not args.no_headless

    # 批量模式
    if args.urls_file:
        urls_path = Path(args.urls_file)
        if not urls_path.exists():
            print(f"❌ URL文件不存在: {args.urls_file}")
            sys.exit(1)
        urls = [line.strip() for line in urls_path.read_text().splitlines() if line.strip()]
        print(f"📂 从文件加载 {len(urls)} 个URL")

        results = get_batch_note_details(
            urls=urls,
            cookie=cookie,
            headless=headless,
            delay=args.delay,
        )

        output_data = results
        print(f"\n✅ 批量抓取完成: {sum(1 for r in results if 'error' not in r)}/{len(results)} 成功")

    # 单篇模式
    else:
        url = args.url
        if args.note_id:
            url = f'https://www.xiaohongshu.com/explore/{args.note_id}'

        note = get_note_detail(
            url=url,
            cookie=cookie,
            headless=headless,
            delay=args.delay,
        )

        output_data = note
        print(f"\n✅ 笔记详情获取完成")

    if not args.output:
        data_dir = Path(__file__).parent.parent / 'data'
        data_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        prefix = "batch" if getattr(args, 'urls_file', None) else "note"
        args.output = str(data_dir / f"{prefix}_detail_{timestamp}.json")

    output_path = Path(args.output)
    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    print(f"📁 结果已保存到: {args.output}")


if __name__ == '__main__':
    main()
