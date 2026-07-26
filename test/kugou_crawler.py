"""
酷狗音乐爬虫 - 完善版本
功能：扫码登录、记住cookie、获取榜单分类、获取歌曲列表、通过浏览器监听请求获取歌曲信息、下载歌曲和封面、存储到数据库
"""

import asyncio
import pickle
import time
import re
import os
import requests
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import pymysql
import json
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright, Browser, Page, BrowserContext


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

        # 下载目录配置
        self.music_dir = Path("/Users/wuwenqiang/Documents/static/music/kugou")
        self.image_dir = Path("/Users/wuwenqiang/Documents/static/music/images")
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)

        # 数据库配置
        self.db_config = {
            'host': '127.0.0.1',
            'port': 3306,
            'user': 'root',
            'password': 'wwq_2021',
            'database': 'play2',
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

        # 存储捕获的歌曲信息
        self.song_info_data = None
        self.song_info_event = asyncio.Event()

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

        self.browser = self.context.browser

        if self.cookie_file.exists():
            await self.load_cookies()

        self.page = await self.context.new_page()
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
        await self.page.wait_for_timeout(3000)

        if await self.check_login_status():
            print("✅ 您已登录（通过持久化上下文）")
            await self.save_cookies()
            return True

        print("📱 请点击右上角'登录'按钮进行扫码登录...")
        print("💡 提示: 如果登录按钮未自动点击，请手动点击")

        login_clicked = False

        try:
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

        print("\n⏳ 等待扫码登录... (请勿关闭浏览器)")
        print("📱 使用酷狗音乐APP扫描二维码")
        print("⏰ 等待时间: 2分钟\n")

        login_success = False
        start_time = time.time()

        while time.time() - start_time < 120:
            try:
                if await self.check_login_status():
                    login_success = True
                    break

                await self.page.wait_for_timeout(2000)

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

    def get_db_connection(self):
        """获取数据库连接"""
        try:
            connection = pymysql.connect(**self.db_config)
            return connection
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return None

    def check_audio_exists(self, audio_id: str) -> bool:
        """检查歌曲是否已存在"""
        connection = self.get_db_connection()
        if not connection:
            return False

        try:
            with connection.cursor() as cursor:
                sql = "SELECT COUNT(*) FROM music WHERE audio_id = %s"
                cursor.execute(sql, (audio_id,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            print(f"❌ 检查歌曲存在失败: {e}")
            return False
        finally:
            connection.close()

    def check_author_exists(self, author_id: str) -> bool:
        """检查歌手是否已存在"""
        connection = self.get_db_connection()
        if not connection:
            return False

        try:
            with connection.cursor() as cursor:
                sql = "SELECT COUNT(*) FROM music_authors WHERE author_id = %s"
                cursor.execute(sql, (author_id,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            print(f"❌ 检查歌手存在失败: {e}")
            return False
        finally:
            connection.close()

    def insert_author(self, author_id: str, author_name: str, avatar: str):
        """插入歌手数据"""
        if self.check_author_exists(author_id):
            return True

        connection = self.get_db_connection()
        if not connection:
            return False

        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO music_authors (author_id, author_name, avatar, create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (author_id, author_name, avatar, current_time, current_time))
                connection.commit()
                print(f"  ✅ 歌手插入成功: {author_name} ({author_id})")
                return True
        except Exception as e:
            print(f"  ❌ 歌手插入失败: {e}")
            return False
        finally:
            connection.close()

    def insert_music(self, music_data: Dict):
        """插入歌曲数据"""
        connection = self.get_db_connection()
        if not connection:
            return False

        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO music (
                        album_id, song_name, author_id, author_name, 
                        album_name, audio_id, album_audio_id, 
                        cover, play_url, local_play_url, 
                        source_name, source_url, lyrics,
                        create_time, update_time
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    music_data.get('album_id'),
                    music_data.get('song_name'),
                    music_data.get('author_id'),
                    music_data.get('author_name'),
                    music_data.get('album_name'),
                    music_data.get('audio_id'),
                    music_data.get('album_audio_id'),
                    music_data.get('cover'),
                    music_data.get('play_url'),
                    music_data.get('local_play_url'),
                    '酷狗音乐',
                    'https://www.kugou.com',
                    music_data.get('lyrics'),
                    current_time,
                    current_time
                ))
                connection.commit()
                print(f"  ✅ 歌曲插入成功: {music_data.get('song_name')}")
                return True
        except Exception as e:
            print(f"  ❌ 歌曲插入失败: {e}")
            return False
        finally:
            connection.close()

    async def download_file(self, url: str, save_path: Path) -> bool:
        """异步下载文件"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        async with aiofiles.open(save_path, 'wb') as f:
                            await f.write(await response.read())
                        return True
                    else:
                        print(f"  ⚠️ 下载失败，状态码: {response.status}")
                        return False
        except Exception as e:
            print(f"  ❌ 下载文件失败: {e}")
            return False

    async def capture_song_info(self, page: Page):
        """监听页面网络请求，捕获歌曲信息接口"""
        self.song_info_data = None
        self.song_info_event.clear()

        # 监听响应
        def handle_response(response):
            try:
                url = response.url
                if 'wwwapi.kugou.com/play/songinfo' in url:
                    # 异步处理响应
                    asyncio.create_task(self.process_song_info_response(response))
            except Exception as e:
                print(f"  ⚠️ 处理响应失败: {e}")

        # 监听请求
        def handle_request(request):
            try:
                url = request.url
                if 'wwwapi.kugou.com/play/songinfo' in url:
                    print(f"  🔍 检测到歌曲信息API请求: {url}")
            except Exception as e:
                pass

        page.on('response', handle_response)
        page.on('request', handle_request)

        # 等待歌曲信息加载完成
        try:
            await self.song_info_event.wait()
        except Exception as e:
            print(f"  ⚠️ 等待歌曲信息超时: {e}")

        # 移除监听器
        page.remove_listener('response', handle_response)
        page.remove_listener('request', handle_request)

    async def process_song_info_response(self, response):
        """处理歌曲信息响应"""
        try:
            if response.status == 200:
                data = await response.json()
                if data.get('status') == 1 and data.get('err_code') == 0:
                    self.song_info_data = data.get('data')
                    self.song_info_event.set()
                    print(f"  ✅ 成功捕获歌曲信息")
                else:
                    print(f"  ⚠️ API返回错误: {data}")
            else:
                print(f"  ⚠️ API响应状态码异常: {response.status}")
        except Exception as e:
            print(f"  ❌ 处理响应数据失败: {e}")

    async def get_song_info_from_page(self, song_url: str, timeout: int = 30) -> Optional[Dict]:
        """通过打开新页面获取歌曲信息"""
        try:
            # 创建新页面
            new_page = await self.context.new_page()

            # 设置监听器捕获歌曲信息
            capture_task = asyncio.create_task(self.capture_song_info(new_page))

            # 打开歌曲页面
            print(f"  📄 打开歌曲页面: {song_url}")
            await new_page.goto(song_url, wait_until='networkidle', timeout=timeout * 1000)

            # 等待页面加载完成
            await new_page.wait_for_timeout(3000)

            # 等待歌曲信息捕获完成
            try:
                await asyncio.wait_for(self.song_info_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print(f"  ⚠️ 等待歌曲信息超时")

            # 关闭新页面
            await new_page.close()

            # 取消捕获任务
            capture_task.cancel()

            return self.song_info_data

        except Exception as e:
            print(f"  ❌ 获取歌曲信息失败: {e}")
            try:
                await new_page.close()
            except:
                pass
            return None

    async def process_song(self, song_url: str, song_title: str = ""):
        """处理单首歌曲：获取信息、下载、存储"""
        print(f"\n🎵 处理歌曲: {song_title}")
        print(f"   URL: {song_url}")

        # 通过浏览器页面获取歌曲信息
        song_info = await self.get_song_info_from_page(song_url)
        if not song_info:
            print(f"  ❌ 获取歌曲信息失败")
            return

        # 检查歌曲是否已存在
        audio_id = song_info.get('audio_id')
        if not audio_id:
            print(f"  ❌ 没有audio_id，跳过")
            return

        if self.check_audio_exists(str(audio_id)):
            print(f"  ⏭️ 歌曲已存在，跳过: {song_info.get('song_name')}")
            return

        # 下载音乐文件
        play_url = song_info.get('play_url')
        local_play_url = ''
        if play_url:
            # 提取文件名
            filename = os.path.basename(urlparse(play_url).path)
            if not filename:
                filename = f"{audio_id}.mp3"

            save_path = self.music_dir / filename
            print(f"  📥 下载音乐: {filename}")
            if await self.download_file(play_url, save_path):
                local_play_url = str(save_path)
                print(f"  ✅ 音乐下载完成: {local_play_url}")
            else:
                print(f"  ❌ 音乐下载失败")

        # 下载封面图片
        img_url = song_info.get('img')
        cover = ''
        if img_url:
            # 提取文件名
            filename = os.path.basename(urlparse(img_url).path)
            if filename:
                save_path = self.image_dir / filename
                print(f"  📥 下载封面: {filename}")
                if await self.download_file(img_url, save_path):
                    cover = str(save_path)
                    print(f"  ✅ 封面下载完成: {cover}")
                else:
                    print(f"  ❌ 封面下载失败")

        # 处理作者信息
        authors = song_info.get('authors', [])
        author_ids = []
        author_names = []

        for author in authors:
            author_id = author.get('author_id')
            author_name = author.get('author_name')
            avatar = author.get('avatar')

            if author_id and author_name:
                author_ids.append(str(author_id))
                author_names.append(author_name)
                # 插入歌手表
                await asyncio.to_thread(self.insert_author, str(author_id), author_name, avatar or '')

        # 准备歌曲数据
        music_data = {
            'album_id': song_info.get('album_id'),
            'song_name': song_info.get('song_name'),
            'author_id': ','.join(author_ids) if author_ids else '',
            'author_name': ','.join(author_names) if author_names else '',
            'album_name': song_info.get('album_name'),
            'audio_id': str(audio_id),
            'album_audio_id': song_info.get('album_audio_id'),
            'cover': cover,
            'play_url': play_url,
            'local_play_url': local_play_url,
            'lyrics': song_info.get('lyrics', '')
        }

        # 插入歌曲表
        await asyncio.to_thread(self.insert_music, music_data)

    async def get_songs_from_page(self, page_url: str, category_name: str):
        """从榜单页面获取歌曲列表"""
        print(f"\n📊 正在处理榜单: {category_name}")
        print(f"   URL: {page_url}")

        try:
            # 打开榜单页面
            await self.page.goto(page_url, wait_until='networkidle')
            await self.page.wait_for_timeout(3000)

            # 等待歌曲列表加载
            await self.page.wait_for_selector('.pc_temp_songlist', timeout=10000)

            # 获取所有歌曲项
            song_items = await self.page.query_selector_all('.pc_temp_songlist li')

            if not song_items:
                print(f"  ⚠️ 没有找到歌曲")
                return

            print(f"  📋 找到 {len(song_items)} 首歌曲")

            # 处理每首歌曲
            for idx, item in enumerate(song_items, 1):
                try:
                    # 获取歌曲链接
                    a_tag = await item.query_selector('a.pc_temp_songname')
                    if not a_tag:
                        continue

                    song_url = await a_tag.get_attribute('href')
                    if not song_url:
                        continue

                    # 确保URL完整
                    if not song_url.startswith('http'):
                        song_url = 'https://www.kugou.com' + song_url

                    # 获取歌曲标题
                    title = await a_tag.get_attribute('title') or f"歌曲_{idx}"

                    # 处理歌曲
                    await self.process_song(song_url, title)

                    # 添加延迟，避免请求过快
                    await self.page.wait_for_timeout(1000)

                except Exception as e:
                    print(f"  ⚠️ 处理歌曲 {idx} 失败: {e}")
                    continue

        except Exception as e:
            print(f"  ❌ 处理榜单失败: {e}")

    async def get_all_rank_categories(self):
        """获取所有榜单分类并处理"""
        print("\n📊 开始获取榜单分类...")

        # 确保在榜单页面
        if 'rank' not in self.page.url:
            await self.page.goto('https://www.kugou.com/yy/html/rank.html?from=homepage', wait_until='networkidle')
            await self.page.wait_for_timeout(3000)

        # 等待榜单容器加载
        await self.page.wait_for_selector('.pc_temp_side', timeout=10000)

        # 获取所有榜单分类容器
        rank_containers = await self.page.query_selector_all('.pc_rank_sidebar')

        classify_names = ['热门榜单', '特色音乐榜', '全球榜']

        for idx, container in enumerate(rank_containers):
            if idx >= len(classify_names):
                break

            classify = classify_names[idx]
            print(f"\n📌 正在处理大分类: {classify}")

            # 获取该分类下的所有榜单项
            items = await container.query_selector_all('li')

            for item in items:
                try:
                    a_tag = await item.query_selector('a')
                    if not a_tag:
                        continue

                    # 获取category名称
                    category = await a_tag.get_attribute('title')
                    if not category:
                        category = await a_tag.text_content()
                        if category:
                            category = category.strip()

                    if not category:
                        continue

                    # 获取榜单链接
                    href = await a_tag.get_attribute('href')
                    if not href:
                        continue

                    # 确保URL完整
                    if not href.startswith('http'):
                        href = 'https://www.kugou.com' + href

                    print(f"\n  🎯 处理小分类: {category}")

                    # 处理该榜单的歌曲
                    await self.get_songs_from_page(href, category)

                    # 添加延迟
                    await self.page.wait_for_timeout(2000)

                except Exception as e:
                    print(f"  ⚠️ 处理分类项失败: {e}")
                    continue

    async def keep_browser_open(self):
        """保持浏览器打开，等待用户手动关闭"""
        print("\n" + "=" * 50)
        print("🔓 浏览器保持打开状态，请手动关闭浏览器窗口")
        print("💡 提示: 按 Ctrl+C 可以中断程序")
        print("=" * 50 + "\n")

        try:
            while True:
                try:
                    await self.page.evaluate('() => 1')
                    await asyncio.sleep(2)
                except Exception as e:
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
        """运行爬虫"""
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

            # 获取所有榜单分类的歌曲
            await self.get_all_rank_categories()

            print("\n" + "=" * 50)
            print("✅ 所有任务执行完成！")
            print("=" * 50 + "\n")

            # 保持浏览器打开
            if not self.auto_close:
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
            if self.auto_close:
                await self.close()


async def main():
    """主函数"""
    # auto_close=True 表示执行完成后自动关闭浏览器
    crawler = KugouCrawler(headless=False, auto_close=True)
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())