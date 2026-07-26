"""
酷狗音乐爬虫 - 完善版本
功能：扫码登录、记住cookie、提供浏览器实例、获取榜单分类并存入数据库
"""

import asyncio
import pickle
import time
from pathlib import Path
from typing import Optional
from datetime import datetime
import pymysql
import re

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import requests


class KugouCrawler:
    """酷狗音乐爬虫基础类"""

    def __init__(self, headless: bool = False, auto_close: bool = False):
        """
        初始化爬虫

        Args:
            headless: 是否使用无头模式，默认False（显示浏览器）
            auto_close: 是否自动关闭浏览器，默认False（保持打开）
        """
        self.headless = headless
        self.auto_close = auto_close
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.cookie_file = Path("kugou_cookies.pkl")
        self.user_data_dir = Path("/Users/wuwenqiang/Documents/kugou_user_data")
        self.user_data_dir.mkdir(exist_ok=True)
        self.playwright = None

        # 数据库配置
        self.db_config = {
            'host': '127.0.0.1',
            'port': 3306,
            'user': 'root',
            'password': 'wwq_2021',
            'database': 'play',
            'charset': 'utf8mb4'
        }

        # 请求头，模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://www.kugou.com',
            'Referer': 'https://www.kugou.com/',
        }
        self.session = requests.Session()

    async def init_browser(self):
        """初始化浏览器 - 使用持久化上下文"""
        self.playwright = await async_playwright().start()

        # 使用持久化上下文
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        # 从持久化上下文中获取浏览器实例
        self.browser = self.context.browser

        # 如果存在cookie文件，加载额外的cookie
        if self.cookie_file.exists():
            await self.load_cookies()

        self.page = await self.context.new_page()

        # 设置默认超时
        self.page.set_default_timeout(30000)

        print(f"✅ 浏览器已初始化，用户数据目录: {self.user_data_dir}")

    async def load_cookies(self):
        """加载保存的cookie"""
        try:
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            await self.context.add_cookies(cookies)
            print("✅ 已加载Cookie")
            return True
        except Exception as e:
            print(f"⚠️ 加载Cookie失败: {e}")
            return False

    async def save_cookies(self):
        """保存当前cookie到文件"""
        try:
            cookies = await self.context.cookies()
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            print("✅ Cookie已保存")
            return True
        except Exception as e:
            print(f"⚠️ 保存Cookie失败: {e}")
            return False

    async def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            # 检查是否存在用户相关元素
            user_selectors = [
                '.user_avatar',
                '.user_name',
                '.user-info',
                '[class*="user-avatar"]',
                '.login-avatar',
                '.header-user'
            ]

            for selector in user_selectors:
                if await self.page.locator(selector).count() > 0:
                    return True

            # 检查cookie中是否有登录信息
            cookies = await self.context.cookies()
            for cookie in cookies:
                if 'user' in cookie.get('name', '').lower() or 'token' in cookie.get('name', '').lower():
                    return True

            return False
        except:
            return False

    async def login(self):
        """登录酷狗音乐"""
        print("🚀 正在打开酷狗音乐榜单页面...")
        await self.page.goto('https://www.kugou.com/yy/html/rank.html?from=homepage', wait_until='networkidle')

        # 等待页面加载
        await self.page.wait_for_timeout(3000)

        # 检查是否已登录
        if await self.check_login_status():
            print("✅ 您已登录（通过持久化上下文）")
            await self.save_cookies()
            return True

        print("📱 请点击右上角'登录'按钮进行扫码登录...")
        print("💡 提示: 如果登录按钮未自动点击，请手动点击")

        # 尝试多种方式点击登录按钮
        login_clicked = False

        try:
            # 尝试多种选择器
            login_selectors = [
                'button:has-text("登录")',
                '.login_btn',
                '.login-btn',
                '[class*="login"]',
                'text="登录"',
                'a:has-text("登录")',
                '.header-login'
            ]

            for selector in login_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.click(selector, timeout=3000)
                        login_clicked = True
                        print(f"✅ 已点击登录按钮")
                        break
                except:
                    continue

            if not login_clicked:
                print("⚠️ 未找到登录按钮，请手动点击")

        except Exception as e:
            print(f"⚠️ 点击登录按钮失败: {e}")
            print("📱 请手动点击登录按钮...")

        # 等待用户扫码登录
        print("\n⏳ 等待扫码登录... (请勿关闭浏览器)")
        print("📱 使用酷狗音乐APP扫描二维码")
        print("⏰ 等待时间: 2分钟\n")

        # 等待登录成功的标志
        login_success = False
        start_time = time.time()

        while time.time() - start_time < 120:  # 2分钟超时
            try:
                if await self.check_login_status():
                    login_success = True
                    break

                await self.page.wait_for_timeout(2000)

                # 显示等待进度
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"⏳ 已等待 {elapsed} 秒...")

            except Exception as e:
                await self.page.wait_for_timeout(1000)

        if login_success:
            print("✅ 登录成功！")
            await self.save_cookies()
            return True
        else:
            print("❌ 登录超时或失败")
            return False

    async def get_cookies(self) -> list:
        """获取当前cookies"""
        return await self.context.cookies()

    async def get_cookie_string(self) -> str:
        """获取cookie字符串"""
        cookies = await self.get_cookies()
        return '; '.join([f"{c['name']}={c['value']}" for c in cookies])

    async def request_api(self, url: str, params: dict = None, method: str = 'GET') -> dict:
        """
        发送API请求（带cookie）

        Args:
            url: API地址
            params: 请求参数
            method: 请求方法

        Returns:
            API响应数据
        """
        try:
            cookies = await self.get_cookies()
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])

            headers = self.headers.copy()
            headers['Cookie'] = cookie_str

            if method.upper() == 'GET':
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            else:
                response = self.session.post(url, data=params, headers=headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API请求失败: {response.status_code}")
                return {}

        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return {}

    def get_db_connection(self):
        """获取数据库连接"""
        try:
            connection = pymysql.connect(**self.db_config)
            return connection
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return None

    def clear_category_table(self):
        """清空music_category表数据"""
        connection = self.get_db_connection()
        if not connection:
            return False

        try:
            with connection.cursor() as cursor:
                sql = "DELETE FROM music_category"
                cursor.execute(sql)
                connection.commit()
                print("✅ 已清空music_category表数据")
                return True
        except Exception as e:
            print(f"❌ 清空表数据失败: {e}")
            return False
        finally:
            connection.close()

    def insert_category(self, classify: str, category: str, img: str):
        """插入分类数据到数据库"""
        connection = self.get_db_connection()
        if not connection:
            return False

        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO music_category (classify, category, img, create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (classify, category, img, current_time, current_time))
                connection.commit()
                return True
        except Exception as e:
            print(f"❌ 插入数据失败: {e}")
            return False
        finally:
            connection.close()

    async def get_rank_categories(self):
        """
        获取榜单分类信息
        从页面中提取热门榜单、特色音乐榜、全球榜的分类数据
        """
        print("\n📊 开始获取榜单分类信息...")

        # 清空旧数据
        self.clear_category_table()

        # 等待榜单容器加载
        await self.page.wait_for_selector('.pc_temp_side', timeout=10000)

        # 获取所有榜单分类容器
        rank_containers = await self.page.query_selector_all('.pc_rank_sidebar')

        classify_names = ['热门榜单', '特色音乐榜', '全球榜']
        total_count = 0

        for idx, container in enumerate(rank_containers):
            if idx >= len(classify_names):
                break

            classify = classify_names[idx]
            print(f"\n📌 正在处理: {classify}")

            # 获取该分类下的所有榜单项
            items = await container.query_selector_all('li')

            for item in items:
                try:
                    # 获取a标签
                    a_tag = await item.query_selector('a')
                    if not a_tag:
                        continue

                    # 获取category名称（小分类）
                    category = await a_tag.get_attribute('title')
                    if not category:
                        # 如果没有title属性，获取文本内容
                        category = await a_tag.text_content()
                        if category:
                            category = category.strip()

                    if not category:
                        continue

                    # 获取图片URL
                    span = await item.query_selector('span')
                    img_url = ''
                    if span:
                        style = await span.get_attribute('style')
                        if style:
                            # 使用正则表达式提取background-image中的URL
                            match = re.search(r'background-image:url\(([^)]+)\)', style)
                            if match:
                                img_url = match.group(1)
                                # 清理URL中的引号
                                img_url = img_url.strip("'\"")

                    # 插入数据库
                    if self.insert_category(classify, category, img_url):
                        total_count += 1
                        print(f"  ✅ 插入成功: {category} ({classify})")
                    else:
                        print(f"  ❌ 插入失败: {category}")

                except Exception as e:
                    print(f"  ⚠️ 处理条目出错: {e}")
                    continue

        print(f"\n✅ 榜单分类信息获取完成，共插入 {total_count} 条记录")

    async def keep_browser_open(self):
        """保持浏览器打开，等待用户手动关闭"""
        print("\n" + "=" * 50)
        print("🔓 浏览器保持打开状态，请手动关闭浏览器窗口")
        print("💡 提示: 按 Ctrl+C 可以中断程序")
        print("=" * 50 + "\n")

        try:
            # 无限等待，直到用户手动关闭浏览器或按Ctrl+C
            while True:
                # 检查浏览器是否仍然打开
                try:
                    # 尝试执行简单操作来检查浏览器状态
                    await self.page.evaluate('() => 1')
                    await asyncio.sleep(2)
                except Exception as e:
                    # 浏览器已关闭
                    print("🔄 检测到浏览器已关闭")
                    break
        except asyncio.CancelledError:
            print("\n👋 用户中断程序")
        except KeyboardInterrupt:
            print("\n👋 用户中断程序")

    async def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            print("✅ 浏览器已关闭")
        except Exception as e:
            print(f"⚠️ 关闭浏览器时出错: {e}")

    async def run(self):
        """
        运行爬虫 - 获取榜单分类信息
        """
        try:
            # 初始化浏览器
            await self.init_browser()

            # 登录
            login_success = await self.login()
            if not login_success:
                print("❌ 登录失败，退出程序")
                await self.close()
                return

            print("\n" + "=" * 50)
            print("🎵 酷狗音乐爬虫已启动，登录成功！")
            print("=" * 50 + "\n")

            # ============================================
            # 获取榜单分类信息
            # ============================================

            # 确保在榜单页面
            if 'rank' not in self.page.url:
                print("📄 正在跳转到榜单页面...")
                await self.page.goto('https://www.kugou.com/yy/html/rank.html?from=homepage', wait_until='networkidle')
                await self.page.wait_for_timeout(2000)

            # 获取榜单分类
            await self.get_rank_categories()

            print("\n" + "=" * 50)
            print("✅ 所有任务执行完成！")
            print("=" * 50 + "\n")

            # ============================================
            # 你的代码结束
            # ============================================

            # 根据配置决定是否保持浏览器打开
            if not self.auto_close:
                # 保持浏览器打开
                await self.keep_browser_open()
            else:
                print("\n" + "=" * 50)
                print("✅ 程序执行完成，自动关闭浏览器")

        except KeyboardInterrupt:
            print("\n👋 用户中断程序")
        except Exception as e:
            print(f"❌ 程序运行出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 只有在 auto_close 为 True 时才自动关闭
            if self.auto_close:
                await self.close()
            else:
                # 如果浏览器还在运行，尝试关闭
                try:
                    if self.context and self.context.is_closed() == False:
                        await self.close()
                except:
                    pass


async def main():
    """主函数"""
    # auto_close=False 表示不自动关闭浏览器
    crawler = KugouCrawler(headless=False, auto_close=True)
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())