import asyncio
import io
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False


class TencentDocsCollectorAndDownloader:
    def __init__(self, headless=False, render_delay=5, output_format="png", base_dir=None):
        # 采集相关
        self.cookie_file = "qq_docs_cookies.json"
        self.collect_results = []

        # 下载相关
        self.headless = headless
        self.render_delay = render_delay
        self.output_format = output_format.lower()

        if base_dir is None:
            base_dir = os.path.join(os.path.expanduser("~"), "Downloads", "tencent_docs")
        self.base_dir = base_dir
        self.download_dir = self.base_dir

        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

        if self.output_format == "png" and not HAS_PIL:
            print("提示: 未安装 Pillow，PNG 长图将按片段分别保存。")
            print("      安装后即可自动拼接为一张完整长图: pip install Pillow")

        # 共享的浏览器上下文
        self.context = None
        self.browser = None

    # ===================== 采集相关方法 =====================

    async def save_cookies(self, context):
        """保存cookies到文件"""
        cookies = await context.cookies()
        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"✅ Cookies已保存到 {self.cookie_file}")

    async def load_cookies(self, context):
        """从文件加载cookies"""
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print(f"✅ 已加载cookies: {self.cookie_file}")
            return True
        return False

    async def check_login_status(self, page):
        """检查是否已登录"""
        try:
            login_selectors = [
                'text="登录"',
                'text="扫码登录"',
                '.login-btn',
                '[class*="login"]',
                'button:has-text("登录")'
            ]
            for selector in login_selectors:
                try:
                    element = await page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        return False
                except:
                    continue

            user_selectors = [
                '[class*="avatar"]',
                '[class*="user-info"]',
                '[class*="profile"]',
                '.user-avatar'
            ]
            for selector in user_selectors:
                try:
                    element = await page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        return True
                except:
                    continue
            return True
        except Exception as e:
            print(f"检查登录状态异常: {e}")
            return False

    async def login_if_needed(self, page):
        """统一登录方法 - 等待扫码登录"""
        print("🔐 检测到需要登录，请使用微信或QQ扫码登录...")
        print("📱 请在60秒内完成扫码登录")

        try:
            await page.wait_for_url(
                lambda url: "login" not in url.lower() and "auth" not in url.lower(),
                timeout=60000
            )
            await page.wait_for_timeout(3000)
            print("✅ 登录成功！")
            await self.save_cookies(page.context)
            return True
        except Exception as e:
            print(f"⚠️ 登录超时或失败: {e}")
            return False

    async def get_page_title(self, page):
        """获取页面标题"""
        try:
            title = await page.title()
            if title and title.strip():
                return title.strip()

            title_selectors = ['h1', '.title', '[class*="title"]', 'header h1', '.doc-title']
            for selector in title_selectors:
                try:
                    element = await page.locator(selector).first
                    if await element.is_visible(timeout=1000):
                        text = await element.text_content()
                        if text and text.strip():
                            return text.strip()
                except:
                    continue
            return "未获取到标题"
        except Exception as e:
            print(f"获取标题时出错: {e}")
            return "获取标题失败"

    async def collect_data_from_url(self, url, index):
        """处理单个URL的数据采集（使用共享context）"""
        print(f"\n{'=' * 60}")
        print(f"📄 处理第 {index} 个页面: {url}")
        print(f"{'=' * 60}")

        page = await self.context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            page_title = await self.get_page_title(page)
            print(f"📝 页面标题: {page_title}")

            # 等待li元素加载
            try:
                await page.wait_for_selector('li.css-1iabehw.emy3zzt12', timeout=15000)
            except:
                try:
                    await page.wait_for_selector('li[class*="css-"], li[class*="emy3zzt"]', timeout=10000)
                except:
                    print("❌ 未找到任何li元素，跳过此页面")
                    return

            li_elements = await page.locator('li.css-1iabehw.emy3zzt12').all()
            print(f"🔍 找到 {len(li_elements)} 个li元素")

            if len(li_elements) == 0:
                li_elements = await page.locator('li[class*="css-"]').all()
                print(f"🔍 使用宽松选择器找到 {len(li_elements)} 个li元素")

            collected_urls = []

            for i, li in enumerate(li_elements, 1):
                try:
                    print(f"\n  🔄 点击第 {i} 个li元素...")

                    async with self.context.expect_page() as new_page_info:
                        await li.click()

                    new_page = await new_page_info.value
                    print(f"  ⏳ 等待新窗口加载...")

                    await new_page.wait_for_load_state("networkidle", timeout=30000)
                    await new_page.wait_for_timeout(3000)

                    new_url = new_page.url
                    print(f"  ✅ 新窗口URL: {new_url}")

                    new_title = await self.get_page_title(new_page)
                    print(f"  📝 新窗口标题: {new_title}")

                    collected_urls.append(new_url)
                    await new_page.close()
                    print(f"  ✅ 已关闭新窗口")

                except Exception as e:
                    print(f"  ❌ 处理第 {i} 个li时出错: {e}")
                    continue

            if collected_urls:
                self.collect_results.append({
                    "title": page_title,
                    "data": collected_urls
                })
                print(f"\n✅ 页面 '{page_title}' 采集完成，共 {len(collected_urls)} 个链接")
            else:
                print(f"\n⚠️ 页面 '{page_title}' 未采集到任何链接")

        except Exception as e:
            print(f"❌ 处理URL {url} 时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await page.close()
            print(f"✅ 已关闭页面")

    # ===================== 下载相关方法 =====================

    async def download_document(self, page, url, title):
        """下载单个文档"""
        try:
            self.download_dir = os.path.join(self.base_dir, title)
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)

            print(f"正在处理: {url} (标题: {title})")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector("#sc-page-content", timeout=30000)
            await page.wait_for_timeout(2000)

            page_title = await page.title()
            safe_title = "".join(c for c in page_title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            if self.output_format == "pdf":
                result = await self._save_pdf(page, safe_title)
            else:
                result = await self._save_png(page, safe_title)

            print(f"✓ 已下载: {result}")
            return True
        except Exception as e:
            print(f"✗ 下载失败 {url}: {str(e)}")
            return False

    async def _save_pdf(self, page, safe_title):
        await self._scroll_to_load_all(page)
        print(f"等待 {self.render_delay} 秒后生成 PDF...")
        await page.wait_for_timeout(self.render_delay * 1000)

        pdf_path = os.path.join(self.download_dir, f"{safe_title}.pdf")
        await page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"}
        )
        return f"{safe_title}.pdf"

    async def _scroll_to_load_all(self, page):
        """滚动页面以触发懒加载"""
        try:
            await page.evaluate(
                """async () => {
                    const content = document.querySelector('#sc-page-content');
                    let el = content;
                    let target = null;
                    while (el) {
                        if (el.scrollHeight > el.clientHeight + 100) { target = el; break; }
                        el = el.parentElement;
                    }
                    if (!target) target = document.scrollingElement;
                    const step = 400;
                    for (let i = 0; i < 800; i++) {
                        const before = target.scrollHeight;
                        target.scrollTop += step;
                        await new Promise(r => setTimeout(r, 120));
                        const after = target.scrollHeight;
                        const reachedBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 50;
                        if (reachedBottom && after === before) break;
                    }
                    target.scrollTop = 0;
                }"""
            )
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"滚动加载内容时出错: {e}")

    async def _save_png(self, page, safe_title):
        segments = await self._capture_segments(page)
        if not segments:
            raise RuntimeError("截图失败，未获取到任何片段")

        if HAS_PIL:
            png_path = os.path.join(self.download_dir, f"{safe_title}.png")
            total_height = self._stitch(segments, png_path)
            return f"{safe_title}.png (宽高拼接完成, 总高 {total_height}px)"
        else:
            saved = []
            for i, (_, buf) in enumerate(segments, 1):
                p = os.path.join(self.download_dir, f"{safe_title}_part{i:03d}.png")
                with open(p, "wb") as f:
                    f.write(buf)
                saved.append(p)
            return f"{safe_title}_part001.png 等 {len(saved)} 个片段（安装 Pillow 可自动拼接）"

    def _stitch(self, segments, png_path):
        images = [(top, Image.open(io.BytesIO(buf)).convert("RGB")) for top, buf in segments]
        width = images[0][1].width
        total_height = max(top + im.height for top, im in images)
        canvas = Image.new("RGB", (width, total_height), "white")
        for top, im in images:
            canvas.paste(im, (0, top))
        canvas.save(png_path)
        return total_height

    async def _capture_segments(self, page):
        info = await self._get_scroll_info(page)
        vh = int(info["height"])
        total = int(info["total"])
        width = int(info["width"])
        x, y = int(info["x"]), int(info["y"])
        inner_height = int(info.get("innerHeight", vh))
        clip_h = min(vh, inner_height - y)

        segments = []
        overlap = 20
        step = max(clip_h - overlap, 100)
        top = 0
        guard = 0
        while guard < 5000:
            actual_top = int(await self._set_scroll_top(page, top))
            await page.wait_for_timeout(300)

            buf = await page.screenshot(clip={"x": x, "y": y, "width": width, "height": clip_h})
            segments.append((actual_top, buf))

            info = await self._get_scroll_info(page)
            total = max(total, int(info["total"]))
            guard += 1

            if actual_top + clip_h >= total - 5:
                break
            top = actual_top + step

        await self._set_scroll_top(page, 0)
        return segments

    async def _get_scroll_info(self, page):
        return await page.evaluate(
            """() => {
                const content = document.querySelector('#sc-page-content');
                let el = content;
                let target = null;
                while (el) {
                    if (el.scrollHeight > el.clientHeight + 100) { target = el; break; }
                    el = el.parentElement;
                }
                const isWindow = !target;
                let x, y, width, height, total;
                if (isWindow) {
                    x = 0; y = 0;
                    width = window.innerWidth; height = window.innerHeight;
                    total = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
                } else {
                    const r = target.getBoundingClientRect();
                    x = Math.max(0, Math.floor(r.x));
                    y = Math.max(0, Math.floor(r.y));
                    width = Math.floor(r.width);
                    height = Math.floor(r.height);
                    total = target.scrollHeight;
                }
                return {x, y, width, height, total, innerHeight: window.innerHeight};
            }"""
        )

    async def _set_scroll_top(self, page, top):
        return await page.evaluate(
            """(top) => {
                const content = document.querySelector('#sc-page-content');
                let el = content;
                let target = null;
                while (el) {
                    if (el.scrollHeight > el.clientHeight + 100) { target = el; break; }
                    el = el.parentElement;
                }
                if (target) { target.scrollTop = top; return target.scrollTop; }
                window.scrollTo(0, top);
                return window.scrollY;
            }""",
            top
        )

    # ===================== 主运行方法 =====================

    async def run(self, collect_urls, download_docs_list=None):
        """
        统一运行入口

        Args:
            collect_urls: 需要采集的URL列表，如 ["https://docs.qq.com/aio/xxx"]
            download_docs_list: 已有的docs_list（可选），如果提供则跳过采集直接下载
        """
        async with async_playwright() as p:
            # 启动浏览器
            print("🌐 启动浏览器...")
            self.browser = await p.chromium.launch(
                headless=False,
                args=['--start-maximized', '--disable-blink-features=AutomationControlled']
            )

            self.context = await self.browser.new_context(
                viewport=None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # 尝试加载cookies
            cookies_loaded = await self.load_cookies(self.context)

            # 登录验证
            page = await self.context.new_page()
            if not cookies_loaded:
                print("📱 未找到cookies，需要登录...")
                await page.goto("https://docs.qq.com/", wait_until="domcontentloaded")
                await self.login_if_needed(page)
            else:
                print("🔍 验证cookies是否有效...")
                await page.goto("https://docs.qq.com/", wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                is_logged_in = await self.check_login_status(page)
                if is_logged_in:
                    print("✅ Cookies有效，已自动登录")
                else:
                    print("⚠️ Cookies可能已过期，需要重新登录")
                    await self.login_if_needed(page)
            await page.close()

            # ===== 采集阶段 =====
            if download_docs_list is None and collect_urls:
                print("\n" + "=" * 60)
                print("📥 开始采集文档链接...")
                print("=" * 60)

                for idx, url in enumerate(collect_urls, 1):
                    await self.collect_data_from_url(url, idx)
                    await asyncio.sleep(3)

                # 保存采集结果
                if self.collect_results:
                    with open("collected_data.json", "w", encoding="utf-8") as f:
                        json.dump(self.collect_results, f, ensure_ascii=False, indent=2)
                    print(f"\n✅ 采集结果已保存到 collected_data.json")

                docs_to_download = self.collect_results
            else:
                docs_to_download = download_docs_list or []

            # ===== 下载阶段 =====
            if docs_to_download:
                print("\n" + "=" * 60)
                print("📥 开始下载文档...")
                print("=" * 60)

                # 去重合并
                merged = {}
                for item in docs_to_download:
                    title = item.get("title", "未命名")
                    if title not in merged:
                        merged[title] = []
                    merged[title].extend(item.get("data", []))

                unique_docs_list = [{"title": title, "data": data} for title, data in merged.items()]

                total_count = sum(len(item['data']) for item in unique_docs_list)
                print(f"共有 {len(unique_docs_list)} 个分组，总计 {total_count} 个文档需要下载")

                success_count = 0
                for doc_group in unique_docs_list:
                    title = doc_group.get("title", "未命名")
                    urls = doc_group.get("data", [])

                    for i, url in enumerate(urls, 1):
                        print(f"\n[{success_count + 1}/{total_count}] 处理文档... (分组: {title})")
                        new_page = await self.context.new_page()
                        try:
                            if await self.download_document(new_page, url, title):
                                success_count += 1
                        finally:
                            await new_page.close()

                        if success_count < total_count:
                            await asyncio.sleep(2)

                print(f"\n完成！成功下载 {success_count}/{total_count} 个文档")
                print(f"文件保存在: {self.base_dir}")
            else:
                print("⚠️ 没有文档需要下载")

            # 关闭浏览器
            await self.browser.close()
            print("\n🎉 所有任务完成！")


def main():
    # 需要采集的URL列表
    collect_urls = [
        "https://docs.qq.com/aio/DTkdsSW1rT3F2ZkFq?from_wiki_space=1&nlc=1&p=ChQb6mG57WqTunsjA1bkBS",
        "https://docs.qq.com/aio/DTnp4emx1bkJMWGt4?from_wiki_space=1&nlc=1&p=HCKImRsSj2gyeTq65NPtCW"
        "https://docs.qq.com/aio/DTlpFSEdJcHVrbnNY?from_wiki_space=1&nlc=1&p=WqYJr5ULHXHmlUdBhmisZh",
        "https://docs.qq.com/aio/DTkpuTGV3bVdja1Nx?from_wiki_space=1&nlc=1&p=LZA66voQ77yCEH6KfM6AEB",
        "https://docs.qq.com/aio/DTnFYbUpJVVZhbER5?from_wiki_space=1&nlc=1&p=raEB6r7GdP22zrIfE0R7C0"
    ]

    # 可选：如果已有docs_list，可以直接传入，跳过采集
    # 例如：
    # existing_docs_list = [
    #     {
    #         "title": "LangSmith使用",
    #         "data": [
    #             "https://docs.qq.com/aio/xxx",
    #             "https://docs.qq.com/aio/yyy"
    #         ]
    #     }
    # ]
    existing_docs_list = None  # 设为 None 则执行采集+下载

    # 创建合并实例
    app = TencentDocsCollectorAndDownloader(
        headless=False,
        output_format="png",  # 或 "pdf"
        render_delay=5
    )

    # 运行
    if existing_docs_list:
        asyncio.run(app.run(collect_urls=None, download_docs_list=existing_docs_list))
    else:
        asyncio.run(app.run(collect_urls=collect_urls, download_docs_list=None))


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()