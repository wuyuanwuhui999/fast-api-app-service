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
    def __init__(self, headless=False, render_delay=5, output_format="png", base_dir=None):
        self.headless = headless
        # 生成 PDF 前额外等待的秒数（仅 PDF 模式使用）
        self.render_delay = render_delay
        # 输出格式: "png"（默认，分段截图拼接成长图）或 "pdf"
        self.output_format = output_format.lower()

        # 基础下载目录
        if base_dir is None:
            base_dir = os.path.join(os.path.expanduser("~"), "Downloads", "tencent_docs")
        self.base_dir = base_dir

        # 当前使用的下载目录（会在下载时动态设置）
        self.download_dir = self.base_dir

        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

        if self.output_format == "png" and not HAS_PIL:
            print("提示: 未安装 Pillow，PNG 长图将按片段分别保存。")
            print("      安装后即可自动拼接为一张完整长图: pip install Pillow")

    async def download_document(self, page, url, title):
        """下载单个文档"""
        try:
            # 设置当前下载目录为标题对应的子文件夹
            self.download_dir = os.path.join(self.base_dir, title)
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)

            print(f"正在处理: {url} (标题: {title})")

            # 访问文档页面
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # 等待页面内容加载
            await page.wait_for_selector("#sc-page-content", timeout=30000)

            # 等待初始渲染
            await page.wait_for_timeout(2000)

            # 获取页面标题
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

    # ------------------------------------------------------------------
    # PDF 模式
    # ------------------------------------------------------------------
    async def _save_pdf(self, page, safe_title):
        # 滚动触发懒加载
        await self._scroll_to_load_all(page)
        print(f"等待 {self.render_delay} 秒后生成 PDF...")
        await page.wait_for_timeout(self.render_delay * 1000)

        pdf_path = os.path.join(self.download_dir, f"{safe_title}.pdf")
        await page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={
                "top": "20mm",
                "bottom": "20mm",
                "left": "20mm",
                "right": "20mm"
            }
        )
        return f"{safe_title}.pdf"

    async def _scroll_to_load_all(self, page):
        """滚动页面以触发懒加载（PDF 模式用）"""
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
                        const reachedBottom =
                            target.scrollTop + target.clientHeight >= target.scrollHeight - 50;
                        if (reachedBottom && after === before) break;
                    }
                    target.scrollTop = 0;
                }"""
            )
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"滚动加载内容时出错: {e}")

    # ------------------------------------------------------------------
    # PNG 模式：分段滚动截图 + 拼接，应对虚拟滚动只渲染可视区域的问题
    # ------------------------------------------------------------------
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
        """把 [(scrollTop, png_bytes), ...] 垂直拼接成一张长图"""
        images = [(top, Image.open(io.BytesIO(buf)).convert("RGB")) for top, buf in segments]
        width = images[0][1].width
        total_height = max(top + im.height for top, im in images)
        canvas = Image.new("RGB", (width, total_height), "white")
        for top, im in images:
            canvas.paste(im, (0, top))
        canvas.save(png_path)
        return total_height

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
        overlap = 20  # 段与段之间重叠 20px，避免拼接出缝隙
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

    async def run(self, docs_list):
        """主运行函数
        docs_list: 列表，每个元素为 {"title": "标题", "data": ["url1", "url2", ...]}
        """
        # 收集所有 URL 用于登录检测
        all_urls = []
        for doc_group in docs_list:
            all_urls.extend(doc_group.get("data", []))

        if not all_urls:
            print("没有文档需要下载")
            return

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

            # 访问第一个文档进行登录
            print("访问第一个文档...")
            await page.goto(all_urls[0], wait_until="networkidle", timeout=60000)
            await self.login_if_needed(page)

            success_count = 0
            total_count = len(all_urls)

            # 遍历每个文档组
            for doc_group in docs_list:
                title = doc_group.get("title", "未命名")
                urls = doc_group.get("data", [])

                for i, url in enumerate(urls, 1):
                    print(f"\n[{success_count + 1}/{total_count}] 处理文档... (分组: {title})")

                    new_page = await context.new_page()
                    try:
                        if await self.download_document(new_page, url, title):
                            success_count += 1
                    finally:
                        await new_page.close()

                    if success_count < total_count:
                        await page.wait_for_timeout(2000)

            print(f"\n完成！成功下载 {success_count}/{total_count} 个文档")
            print(f"文件保存在: {self.base_dir}")

            await browser.close()


def main():
    # 新的数据格式
    docs_list = [
  {
    "title": "LangSmith使用",
    "data": [
      "https://docs.qq.com/aio/DTkFHZ1hMb3VIV2ZN?nlc=1&p=igqxlk4gjrEye0ciB2xkZk",
      "https://docs.qq.com/aio/DTmtZckZ2eUFhTnVk?nlc=1&p=Pn1rNpRYCCR9jPMQBQWq3I"
    ]
  }
]

    # 去重：如果标题相同，合并 data 列表
    merged = {}
    for item in docs_list:
        title = item.get("title", "未命名")
        if title not in merged:
            merged[title] = []
        merged[title].extend(item.get("data", []))

    # 转换回去重后的格式
    unique_docs_list = [{"title": title, "data": data} for title, data in merged.items()]

    print(
        f"共有 {len(unique_docs_list)} 个分组，总计 {sum(len(item['data']) for item in unique_docs_list)} 个文档需要下载")

    # output_format="png" 分段截图拼接成长图；改成 "pdf" 则走原 PDF 导出
    downloader = TencentDocsDownloader(headless=False, output_format="png", render_delay=5)
    asyncio.run(downloader.run(unique_docs_list))


if __name__ == "__main__":
    main()