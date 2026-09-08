import asyncio
import json
import os
from playwright.async_api import async_playwright


class QQDocsCollector:
    def __init__(self):
        self.cookie_file = "qq_docs_cookies.json"
        self.result_file = "collected_data.json"
        self.results = []  # 存储所有结果

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
            # 检查是否存在登录相关元素
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

            # 检查是否有用户信息（已登录的标志）
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

            # 如果既没有登录元素也没有用户信息，可能已登录
            return True

        except Exception as e:
            print(f"检查登录状态异常: {e}")
            return False

    async def login_if_needed(self, page, context):
        """如果需要登录则等待手动扫码"""
        print("🔐 检测到需要登录，请使用微信或QQ扫码登录...")
        print("📱 请在60秒内完成扫码登录")

        try:
            # 等待登录成功（等待URL不包含登录相关路径）
            await page.wait_for_url(
                lambda url: "login" not in url.lower() and "auth" not in url.lower(),
                timeout=60000
            )
            await page.wait_for_timeout(3000)

            print("✅ 登录成功！")
            await self.save_cookies(context)
            return True

        except Exception as e:
            print(f"⚠️ 登录超时或失败: {e}")
            return False

    async def get_page_title(self, page):
        """获取页面标题"""
        try:
            # 尝试获取页面标题
            title = await page.title()
            if title and title.strip():
                return title.strip()

            # 如果页面标题为空，尝试获取h1或其他标题元素
            title_selectors = [
                'h1',
                '.title',
                '[class*="title"]',
                'header h1',
                '.doc-title'
            ]

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

    async def collect_data_from_url(self, context, url, index):
        """处理单个URL的数据采集"""
        print(f"\n{'=' * 60}")
        print(f"📄 处理第 {index} 个页面: {url}")
        print(f"{'=' * 60}")

        # 创建新页面
        page = await context.new_page()

        try:
            # 访问目标页面
            print("⏳ 正在加载页面...")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)  # 等待页面稳定

            # 获取页面标题
            page_title = await self.get_page_title(page)
            print(f"📝 页面标题: {page_title}")

            # 等待li元素加载
            print("⏳ 等待li元素加载...")
            try:
                await page.wait_for_selector('li.css-1iabehw.emy3zzt12', timeout=15000)
            except:
                print("⚠️ 未找到li元素，可能页面结构已变化")
                # 尝试查找其他可能的类名
                try:
                    await page.wait_for_selector('li[class*="css-"], li[class*="emy3zzt"]', timeout=10000)
                except:
                    print("❌ 未找到任何li元素，跳过此页面")
                    return

            # 获取所有匹配的li元素
            li_elements = await page.locator('li.css-1iabehw.emy3zzt12').all()
            print(f"🔍 找到 {len(li_elements)} 个li元素")

            if len(li_elements) == 0:
                print("⚠️ 没有找到任何li元素")
                # 尝试使用更宽松的选择器
                li_elements = await page.locator('li[class*="css-"]').all()
                print(f"🔍 使用宽松选择器找到 {len(li_elements)} 个li元素")

            # 存储当前页面采集的数据
            collected_urls = []

            # 处理每个li元素
            for i, li in enumerate(li_elements, 1):
                try:
                    print(f"\n  🔄 点击第 {i} 个li元素...")

                    # 点击li元素，触发新窗口
                    async with context.expect_page() as new_page_info:
                        await li.click()

                    # 获取新打开的页面
                    new_page = await new_page_info.value
                    print(f"  ⏳ 等待新窗口加载...")

                    # 等待新页面加载完成
                    await new_page.wait_for_load_state("networkidle", timeout=30000)
                    await new_page.wait_for_timeout(3000)

                    # 获取新页面URL
                    new_url = new_page.url
                    print(f"  ✅ 新窗口URL: {new_url}")

                    # 获取新窗口的标题
                    new_title = await self.get_page_title(new_page)
                    print(f"  📝 新窗口标题: {new_title}")

                    # 收集URL
                    collected_urls.append(new_url)

                    # 关闭新页面
                    await new_page.close()
                    print(f"  ✅ 已关闭新窗口")

                except Exception as e:
                    print(f"  ❌ 处理第 {i} 个li时出错: {e}")
                    continue

            # 将结果添加到总结果中
            if collected_urls:
                self.results.append({
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
            # 关闭当前页面
            await page.close()
            print(f"✅ 已关闭页面")

    async def save_results(self):
        """保存采集结果到JSON文件"""
        if not self.results:
            print("⚠️ 没有采集到任何数据")
            return

        # 保存结果
        with open(self.result_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"✅ 结果已保存到 {self.result_file}")
        print(f"{'=' * 60}")

        # 打印摘要
        print(f"\n📊 采集摘要:")
        total_links = 0
        for item in self.results:
            link_count = len(item['data'])
            total_links += link_count
            print(f"  📄 {item['title']}: {link_count} 个链接")
            for i, url in enumerate(item['data'], 1):
                print(f"      {i}. {url}")
            print()

        print(f"📈 总计: {len(self.results)} 个页面, {total_links} 个链接")

    async def main(self, urls):
        """主执行函数"""
        print("🚀 启动腾讯文档采集工具...")
        print("=" * 60)

        async with async_playwright() as p:
            # 启动浏览器（有头模式，方便扫码）
            print("🌐 启动浏览器...")
            browser = await p.chromium.launch(
                headless=False,  # 有头模式
                args=['--start-maximized']  # 最大化窗口
            )

            # 创建上下文
            context = await browser.new_context(
                viewport=None,  # 使用窗口大小
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # 尝试加载cookies
            cookies_loaded = await self.load_cookies(context)

            # 创建新页面进行登录检查
            page = await context.new_page()

            # 检查登录状态
            if not cookies_loaded:
                print("📱 未找到cookies，需要登录...")
                await page.goto("https://docs.qq.com/", wait_until="domcontentloaded")
                await self.login_if_needed(page, context)
            else:
                # 验证cookies是否有效
                print("🔍 验证cookies是否有效...")
                await page.goto("https://docs.qq.com/", wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                is_logged_in = await self.check_login_status(page)
                if is_logged_in:
                    print("✅ Cookies有效，已自动登录")
                else:
                    print("⚠️ Cookies可能已过期，需要重新登录")
                    await self.login_if_needed(page, context)

            # 关闭验证页面
            await page.close()

            # 处理所有URL
            for idx, url in enumerate(urls, 1):
                await self.collect_data_from_url(context, url, idx)
                await asyncio.sleep(3)  # 间隔等待

            # 保存结果
            await self.save_results()

            # 关闭浏览器
            await browser.close()
            print("\n🎉 所有任务完成！")


# 使用示例
async def run():
    urls = [
        "https://docs.qq.com/aio/DTmRFVW1mV0RmS0Rj?from_wiki_space=1&nlc=1"
    ]

    collector = QQDocsCollector()
    await collector.main(urls)


if __name__ == "__main__":
    # 在Windows上运行需要设置事件循环策略
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())