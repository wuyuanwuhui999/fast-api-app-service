import asyncio
import io
import os
from datetime import datetime
from playwright.async_api import async_playwright

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False


class TencentDocsDownloader:
    def __init__(self, headless=False, render_delay=5, output_format="pdf"):
        self.headless = headless
        # 旧版 page.pdf 用的等待秒数；当前分段截图方案已内置等待，此参数保留兼容
        self.render_delay = render_delay
        # 输出格式: "pdf"（完整多页 PDF）或 "png"（完整长图）
        self.output_format = output_format.lower()
        self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "tencent_docs")

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

        if not HAS_PIL:
            print("提示: 未安装 Pillow。PNG 模式将按片段分别保存；PDF 模式无法使用。")
            print("      安装 Pillow 后可自动拼接长图/生成完整 PDF: pip install Pillow")

    async def download_document(self, page, url):
        """下载单个文档"""
        try:
            print(f"正在处理: {url}")

            # 访问文档页面
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # 等待页面内容加载
            await page.wait_for_selector("#sc-page-content", timeout=30000)

            # 等待初始渲染
            await page.wait_for_timeout(2000)

            # 获取页面标题
            title = await page.title()
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
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

    # ------------------------------------------------------------------
    # 分段截图：应对腾讯文档虚拟滚动「DOM 只保留可视区域」导致 page.pdf 只出可视区的问题
    # ------------------------------------------------------------------
    async def _capture_segments(self, page):
        """分段滚动截图，返回 [(scrollTop, png_bytes), ...]"""
        info = await self._get_scroll_info(page)
        vh = int(info["height"])
        total = int(info["total"])
        width = int(info["width"])
        x, y = int(info["x"]), int(info["y"])
        inner_height = int(info.get("innerHeight", vh))
        clip_h = min(vh, inner_height - y)

        segments = []
        overlap = 20          # 段与段之间重叠 20px，避免拼接出缝隙
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

            # 已滚到底部则结束
            if actual_top + clip_h >= total - 5:
                break
            top = actual_top + step

        await self._set_scroll_top(page, 0)
        return segments

    async def _get_scroll_info(self, page):
        """定位实际滚动容器，返回可视区域坐标、尺寸与文档总高度"""
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
        """滚动容器到指定位置，返回实际滚动后的 scrollTop"""
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

    # ------------------------------------------------------------------
    # 拼接与输出
    # ------------------------------------------------------------------
    def _stitch_image(self, segments):
        """把 [(scrollTop, png_bytes), ...] 垂直拼接成一张完整长图（返回 PIL Image）"""
        images = [(top, Image.open(io.BytesIO(buf)).convert("RGB")) for top, buf in segments]
        width = images[0][1].width
        total_height = max(top + im.height for top, im in images)
        canvas = Image.new("RGB", (width, total_height), "white")
        for top, im in images:
            canvas.paste(im, (0, top))
        return canvas

    def _split_image_to_pages(self, img, page_ratio=297 / 210):
        """把完整长图按 A4 宽高比切成多页，返回 [Image, ...]"""
        width, height = img.size
        page_h = max(int(width * page_ratio), 1)
        pages = []
        for y in range(0, height, page_h):
            pages.append(img.crop((0, y, width, min(y + page_h, height))))
        return pages

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
        """拼接长图并保存为 PNG，返回总高"""
        canvas = self._stitch_image(segments)
        canvas.save(png_path)
        return canvas.height

    async def _save_pdf(self, page, safe_title):
        """生成完整多页 PDF。

        为什么不用 page.pdf()：腾讯文档是虚拟滚动，DOM 里只保留可视区域附近的内容，
        page.pdf() 走 Chromium 打印路径，只能输出当前已渲染的 DOM，所以只会得到可视区。
        因此这里复用「分段截图 → 拼接完整长图 → 按 A4 比例切页」生成多页 PDF，内容完整。
        """
        if not HAS_PIL:
            raise RuntimeError("PDF 模式依赖 Pillow，请先安装: pip install Pillow")

        segments = await self._capture_segments(page)
        if not segments:
            raise RuntimeError("截图失败，未获取到任何片段")

        full = self._stitch_image(segments)
        pages = self._split_image_to_pages(full)

        pdf_path = os.path.join(self.download_dir, f"{safe_title}.pdf")
        pages[0].save(pdf_path, save_all=True, append_images=pages[1:], resolution=96.0)
        return f"{safe_title}.pdf (共 {len(pages)} 页, 由完整长图切分生成)"

    async def login_if_needed(self, page):
        """处理登录流程"""
        try:
            login_selector = '//*[contains(text(), "扫码登录") or contains(text(), "微信登录")]'
            if await page.locator(login_selector).count() > 0:
                print("检测到需要登录，请在浏览器中扫码登录...")
                print("登录后脚本将自动继续执行")

                await page.wait_for_selector("#sc-page-content", timeout=300000)
                print("登录成功！")

                await page.context.storage_state(path="tencent_auth.json")
                print("登录状态已保存")
                return True
            return False
        except Exception as e:
            print(f"登录过程出错: {e}")
            return False

    async def run(self, urls):
        """主运行函数"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                storage_state="tencent_auth.json" if os.path.exists("tencent_auth.json") else None
            )

            page = await context.new_page()

            if urls:
                print("访问第一个文档...")
                await page.goto(urls[0], wait_until="networkidle", timeout=60000)
                await self.login_if_needed(page)

            success_count = 0
            for i, url in enumerate(urls, 1):
                print(f"\n[{i}/{len(urls)}] 处理文档...")

                new_page = await context.new_page()
                try:
                    if await self.download_document(new_page, url):
                        success_count += 1
                finally:
                    await new_page.close()

                if i < len(urls):
                    await page.wait_for_timeout(2000)

            print(f"\n完成！成功下载 {success_count}/{len(urls)} 个文档")
            print(f"文件保存在: {self.download_dir}")

            await browser.close()


def main():
    urls = [
        "https://docs.qq.com/aio/DTkxzbHpNc1RQcGhr?from_wiki_space=1&nlc=1&p=z7jYvZcqaGTLRvMd8jndrP",
        "https://docs.qq.com/aio/DTnpsYnZqY3ZnYW1u?from_wiki_space=1&nlc=1&p=lXLBi3UN9yr5uHXVu1bQJm",
        "https://docs.qq.com/aio/DTmpJWkR2T3BuWUV4?nlc=1&p=8fwQzj0Qs9wz1x6BHtEXJt",
        "https://docs.qq.com/aio/DTkpYR3VQZGZoenFJ?nlc=1&p=oLeFpNFoSkvv4Fqfrscx47",
        "https://docs.qq.com/aio/DTkFjZUxpUllKenps?nlc=1&p=x9LUSJfyjd53RtEzKp1RDZ",
        "https://docs.qq.com/aio/DTkVZdGdJWUxaWkFB?nlc=1&p=GzA45VsNmMMh0Rc94xPzIo",
        "https://docs.qq.com/aio/DTmp0T29VeUtHbFVZ?nlc=1&p=fNDLQfZ3fihfDsOiwWoel2",
        "https://docs.qq.com/aio/DTkxBaEdpaG9EVm1I?nlc=1&p=cPlEXWCOGEqJYgw9gVt16f",
        "https://docs.qq.com/aio/DTm5ZeU1keXVCQmdx?nlc=1&p=8syr21S6HCFlhc8tzVPhOp",
        "https://docs.qq.com/aio/DTnJ0dWtRdGNmUkhh?nlc=1&p=Lc0qJy2O2AP06aB47W3W8v",
        "https://docs.qq.com/aio/DTmJQQ1laaXpCdHhN?nlc=1&p=un9BS78iceROaUkDWca56A",
        "https://docs.qq.com/aio/DTk5idVJnTkRyVU9p?nlc=1&p=IqlDZ1B9MR1JHQhXZx3bF5",
        "https://docs.qq.com/aio/DTmdicERKcWNteHdH?nlc=1&p=4DBEYqRVPEECgqDGtWrbjS",
        "https://docs.qq.com/aio/DTmxnRmx5Y2JnWkN6?nlc=1&p=DbhoyBbfoduEcWKbsaG2LZ",
        "https://docs.qq.com/aio/DTmxnRmx5Y2JnWkN6?nlc=1&p=DbhoyBbfoduEcWKbsaG2LZ",
        "https://docs.qq.com/aio/DTnhqQU1rUmhGS3B4?nlc=1&p=kjyWYdJVFfsp5hSxlnBjuH"
    ]

    unique_urls = list(dict.fromkeys(urls))
    print(f"共有 {len(unique_urls)} 个文档需要下载")

    # output_format="pdf" 生成完整多页 PDF；"png" 生成完整长图
    downloader = TencentDocsDownloader(headless=False, output_format="pdf")
    asyncio.run(downloader.run(unique_urls))


if __name__ == "__main__":
    main()
