# requirements.txt
"""
playwright==1.40.0
requests==2.31.0
"""

# kugou_crawler.py
"""
酷狗音乐爬虫 - 基于Playwright框架
功能：扫码登录、记住cookie、获取接口数据
"""

import asyncio
import json
import os
import pickle
import time
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import requests


class KugouCrawler:
    """酷狗音乐爬虫类"""

    def __init__(self, headless: bool = False):
        """
        初始化爬虫

        Args:
            headless: 是否使用无头模式，默认False（显示浏览器）
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.cookie_file = Path("kugou_cookies.pkl")
        self.user_data_dir = Path("./kugou_user_data")
        self.user_data_dir.mkdir(exist_ok=True)

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
        """初始化浏览器"""
        playwright = await async_playwright().start()

        # 使用持久化上下文保存登录状态
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        # 创建带持久化存储的上下文
        self.context = await self.browser.new_context(
            user_data_dir=str(self.user_data_dir),
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 如果存在cookie文件，加载cookie
        if self.cookie_file.exists():
            await self.load_cookies()

        self.page = await self.context.new_page()

        # 设置默认超时
        self.page.set_default_timeout(30000)

    async def load_cookies(self):
        """加载保存的cookie"""
        try:
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            await self.context.add_cookies(cookies)
            print("✅ 已加载保存的Cookie")
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

    async def login(self):
        """登录酷狗音乐"""
        print("🚀 正在打开酷狗音乐首页...")
        await self.page.goto('https://www.kugou.com/', wait_until='networkidle')

        # 等待页面加载
        await self.page.wait_for_timeout(2000)

        # 检查是否已登录（通过检测用户头像或用户名元素）
        try:
            # 查找登录状态指示器
            is_logged_in = await self.page.locator('.user_avatar, .user_name, .user-info').count() > 0
            if is_logged_in:
                print("✅ 您已登录")
                await self.save_cookies()
                return True
        except:
            pass

        print("📱 请点击右上角'登录'按钮进行扫码登录...")

        try:
            # 点击登录按钮
            login_btn = await self.page.wait_for_selector(
                'button:has-text("登录"), .login_btn, .login-btn, [class*="login"]',
                timeout=5000
            )
            if login_btn:
                await login_btn.click()
                print("✅ 已点击登录按钮，请扫码...")
            else:
                # 尝试点击其他可能的登录元素
                await self.page.click('text="登录"')
        except Exception as e:
            print(f"⚠️ 点击登录按钮失败: {e}")
            # 直接打开登录页面
            await self.page.goto('https://www.kugou.com/login/', wait_until='networkidle')
            print("📱 请扫描二维码登录...")

        # 等待用户扫码登录
        print("⏳ 等待扫码登录... (请勿关闭浏览器)")
        print("💡 提示: 使用酷狗音乐APP扫描二维码")

        # 等待登录成功的标志
        try:
            # 等待URL变化或用户元素出现
            await self.page.wait_for_selector(
                '.user_avatar, .user_name, .user-info, [class*="user-avatar"]',
                timeout=120000  # 2分钟超时
            )
            print("✅ 登录成功！")
            await self.save_cookies()
            return True
        except Exception as e:
            print(f"❌ 登录超时或失败: {e}")
            return False

    async def get_api_data(self, api_url: str, params: Dict = None) -> Dict:
        """
        获取酷狗音乐API数据

        Args:
            api_url: API接口URL
            params: 请求参数

        Returns:
            API返回的JSON数据
        """
        try:
            # 获取当前cookie
            cookies = await self.context.cookies()
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])

            # 构建请求头
            headers = self.headers.copy()
            headers['Cookie'] = cookie_str

            # 发送请求
            response = self.session.get(
                api_url,
                params=params,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API请求失败: {response.status_code}")
                return {}

        except Exception as e:
            print(f"❌ 获取API数据失败: {e}")
            return {}

    async def get_search_song(self, keyword: str, page: int = 1, pagesize: int = 30) -> Dict:
        """
        搜索歌曲

        Args:
            keyword: 搜索关键词
            page: 页码
            pagesize: 每页数量

        Returns:
            搜索结果
        """
        api_url = 'https://www.kugou.com/yy/index.php'
        params = {
            'r': 'search/get',
            'callback': 'callback123',
            'keyword': keyword,
            'page': page,
            'pagesize': pagesize,
            'platform': 'WebFilter',
            'ver': '1.0',
            'timestamp': int(time.time() * 1000),
        }

        # 实际接口可能需要调整，这里使用搜索页面获取数据
        search_url = f'https://www.kugou.com/yy/search/index.html?keyword={keyword}'
        await self.page.goto(search_url, wait_until='networkidle')
        await self.page.wait_for_timeout(2000)

        # 提取歌曲列表数据
        try:
            # 等待歌曲列表加载
            await self.page.wait_for_selector('.song-list, .search-song-list, .music-list', timeout=5000)

            # 获取页面数据（这里可以从页面提取，也可以拦截API请求）
            # 方式1: 从页面提取
            songs = await self.page.evaluate('''
                () => {
                    const items = document.querySelectorAll('.song-item, .music-item, .search-item');
                    return Array.from(items).map(item => ({
                        title: item.querySelector('.song-name, .title')?.innerText || '',
                        singer: item.querySelector('.singer, .artist')?.innerText || '',
                        album: item.querySelector('.album')?.innerText || '',
                    }));
                }
            ''')
            return {'songs': songs, 'total': len(songs)}

        except Exception as e:
            print(f"❌ 获取搜索数据失败: {e}")
            return {}

    async def get_hot_songs(self) -> Dict:
        """获取热门歌曲"""
        api_url = 'https://www.kugou.com/yy/rank/home/'
        await self.page.goto(api_url, wait_until='networkidle')

        try:
            await self.page.wait_for_selector('.rank-list, .hot-list', timeout=5000)

            songs = await self.page.evaluate('''
                () => {
                    const items = document.querySelectorAll('.rank-item, .hot-item');
                    return Array.from(items).slice(0, 20).map(item => ({
                        title: item.querySelector('.song-name')?.innerText || '',
                        singer: item.querySelector('.singer')?.innerText || '',
                        rank: item.querySelector('.rank-num')?.innerText || '',
                    }));
                }
            ''')
            return {'songs': songs}

        except Exception as e:
            print(f"❌ 获取热门歌曲失败: {e}")
            return {}

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()

    async def run(self):
        """运行爬虫主流程"""
        try:
            # 初始化浏览器
            await self.init_browser()

            # 登录
            login_success = await self.login()
            if not login_success:
                print("❌ 登录失败，退出程序")
                return

            print("\n" + "=" * 50)
            print("🎵 酷狗音乐爬虫已启动")
            print("=" * 50 + "\n")

            while True:
                print("\n请选择操作:")
                print("1. 🔍 搜索歌曲")
                print("2. 🔥 获取热门歌曲")
                print("3. 📊 获取推荐歌单")
                print("4. ❌ 退出")

                choice = input("请输入选择 (1-4): ").strip()

                if choice == '1':
                    keyword = input("请输入搜索关键词: ").strip()
                    if keyword:
                        result = await self.get_search_song(keyword)
                        if result and 'songs' in result:
                            print(f"\n✅ 找到 {len(result['songs'])} 首歌曲:")
                            for i, song in enumerate(result['songs'], 1):
                                print(f"{i}. {song.get('title', '未知')} - {song.get('singer', '未知')}")
                        else:
                            print("❌ 未找到歌曲")

                elif choice == '2':
                    result = await self.get_hot_songs()
                    if result and 'songs' in result:
                        print(f"\n🔥 热门歌曲 (TOP {len(result['songs'])}):")
                        for i, song in enumerate(result['songs'], 1):
                            print(f"{i}. {song.get('title', '未知')} - {song.get('singer', '未知')}")
                    else:
                        print("❌ 获取热门歌曲失败")

                elif choice == '3':
                    # 获取推荐歌单
                    await self.page.goto('https://www.kugou.com/yy/recommend/', wait_until='networkidle')
                    await self.page.wait_for_timeout(2000)
                    print("📊 推荐歌单页面已加载")

                elif choice == '4':
                    print("👋 退出程序")
                    break

        except Exception as e:
            print(f"❌ 程序运行出错: {e}")
        finally:
            await self.close()
            print("✅ 浏览器已关闭")


async def main():
    """主函数"""
    crawler = KugouCrawler(headless=False)
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())