import asyncio
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import aiohttp
import pymysql
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin


class KuGouSpider:
    def __init__(self):
        self.db_config = {
            'host': '127.0.0.1',
            'port': 3306,
            'user': 'root',
            'password': 'wwq_2021',
            'database': 'play2',
            'charset': 'utf8mb4'
        }
        self.base_url = 'https://www.kugou.com/yy/singer/index/1-all-2.html'
        self.cookie_file = 'kugou_cookies.json'
        self.progress_file = 'progress.json'
        self.result_file = 'singer_data.json'
        self.image_dir = '/Users/wuwenqiang/Documents/static/music/images'
        self.music_dir = '/Users/wuwenqiang/Documents/static/music/kugou'
        self.session = None

        # 确保目录存在
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.music_dir, exist_ok=True)

    def get_db_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.db_config)

    async def save_cookies(self, context):
        """保存cookies到文件"""
        cookies = await context.cookies()
        with open(self.cookie_file, 'w') as f:
            json.dump(cookies, f)

    async def load_cookies(self, context):
        """从文件加载cookies"""
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file, 'r') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            return True
        return False

    async def login(self, page):
        """登录操作"""
        try:
            # 等待登录按钮出现
            login_btn = page.locator('div.cmhead1_d5._login:has-text("登录")')
            if await login_btn.count() > 0:
                await login_btn.click()
                print("已点击登录按钮，等待15秒扫描二维码...")
                await page.wait_for_timeout(15000)
                return True
        except Exception as e:
            print(f"登录失败: {e}")
        return False

    async def get_categories(self, page):
        """获取所有分类名称"""
        categories = []
        # 获取左侧所有分类
        category_links = await page.locator('.l ul li a:not(.all)').all()

        for link in category_links:
            name = await link.get_attribute('title')
            href = await link.get_attribute('href')
            if name and href:
                categories.append({
                    'name': name,
                    'url': urljoin('https://www.kugou.com', href)
                })
                # 插入分类表
                await self.insert_category(name)

        return categories

    async def insert_category(self, category_name):
        """插入分类到数据库"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 检查分类是否存在
                cursor.execute(
                    "SELECT id FROM music_author_category WHERE category_name = %s",
                    (category_name,)
                )
                result = cursor.fetchone()
                if not result:
                    cursor.execute(
                        """INSERT INTO music_author_category
                               (category_name, create_time, update_time)
                           VALUES (%s, %s, %s)""",
                        (category_name, datetime.now(), datetime.now())
                    )
                    conn.commit()
        finally:
            conn.close()

    async def get_category_id(self, category_name):
        """获取分类ID"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM music_author_category WHERE category_name = %s",
                    (category_name,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        finally:
            conn.close()

    async def get_singer_links(self, page, category_name):
        """获取歌手链接"""
        hrefs = []

        while True:
            # 等待歌手列表加载
            await page.wait_for_selector('#list_head .pic', timeout=10000)

            # 获取当前页所有歌手链接
            singer_links = await page.locator('#list_head .pic').all()
            for link in singer_links:
                href = await link.get_attribute('href')
                if href:
                    hrefs.append(urljoin('https://www.kugou.com', href))

            # 检查是否有下一页
            next_btn = page.locator('#page_next_2')
            if await next_btn.count() > 0 and await next_btn.is_visible():
                await next_btn.click()
                await page.wait_for_timeout(2000)
            else:
                break

        return hrefs

    async def get_singer_info(self, page, url, category_id):
        """获取歌手信息和歌曲列表"""
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            # 获取页面内容
            content = await page.content()

            # 提取script中的数据
            script_pattern = r'var songsdata = (\[.*?\]);'
            match = re.search(script_pattern, content, re.DOTALL)

            # 提取歌手信息
            singer_name = re.search(r"singername = '([^']+)'", content)
            singer_id = re.search(r"singerID = '([^']+)'", content)

            if not singer_name or not singer_id:
                print(f"无法获取歌手信息: {url}")
                return

            singer_name = singer_name.group(1)
            singer_id = singer_id.group(1)

            # 获取头像
            avatar_img = page.locator('.top img')
            if await avatar_img.count() > 0:
                src = await avatar_img.get_attribute('_src')
                if src:
                    # 下载头像
                    avatar_filename = os.path.basename(src)
                    local_path = os.path.join(self.image_dir, avatar_filename)
                    await self.download_file(src, local_path)
                    avatar_url = f'/static/music/images/{avatar_filename}'
                else:
                    avatar_url = ''
            else:
                avatar_url = ''

            # 插入歌手信息
            await self.insert_author(singer_id, singer_name, category_id, avatar_url)

            # 处理歌曲数据
            if match:
                songs_data = json.loads(match.group(1))
                for song in songs_data:
                    await self.process_song(page, song, singer_id, singer_name, url)

        except Exception as e:
            print(f"获取歌手信息失败 {url}: {e}")

    async def insert_author(self, author_id, author_name, category_id, avatar):
        """插入歌手信息"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 检查歌手是否存在
                cursor.execute(
                    "SELECT id FROM music_authors WHERE author_id = %s",
                    (author_id,)
                )
                result = cursor.fetchone()
                if not result:
                    cursor.execute(
                        """INSERT INTO music_authors
                               (author_id, author_name, category_id, avatar, create_time, update_time)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (author_id, author_name, category_id, avatar, datetime.now(), datetime.now())
                    )
                    conn.commit()
        finally:
            conn.close()

    async def process_song(self, page, song, singer_id, singer_name, source_url):
        """处理歌曲信息"""
        try:
            song_url = song.get('song_url')
            if not song_url:
                return

            # 获取歌曲详情
            song_info = await self.get_song_info(song_url)
            if not song_info:
                return

            # 下载音乐文件
            play_url = song_info.get('play_url')
            local_play_url = ''
            if play_url:
                filename = os.path.basename(play_url.split('?')[0])
                local_path = os.path.join(self.music_dir, filename)
                await self.download_file(play_url, local_path)
                local_play_url = f'/static/music/kugou/{filename}'

            # 下载封面
            cover_url = song_info.get('img')
            cover_path = ''
            if cover_url:
                cover_filename = os.path.basename(cover_url)
                local_cover_path = os.path.join(self.image_dir, cover_filename)
                await self.download_file(cover_url, local_cover_path)
                cover_path = f'/static/music/images/{cover_filename}'

            # 插入歌曲信息
            await self.insert_music(song_info, singer_id, singer_name, local_play_url, cover_path, source_url)

        except Exception as e:
            print(f"处理歌曲失败: {e}")

    async def get_song_info(self, song_url):
        """获取歌曲详情"""
        try:
            async with aiohttp.ClientSession() as session:
                # 监听网络请求获取songinfo接口
                # 这里简化处理，直接请求接口
                song_id = song_url.split('/')[-1].replace('.html', '')
                api_url = f'https://wwwapi.kugou.com/play/songinfo?srcappid=2919&clientver=1000&clienttime={int(time.time())}&mid=0&uuid=0&dfid=0&appid=1005&platid=4&encode_album_audio_id={song_id}&token=&userid=0&signature='

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 1:
                            return data.get('data')
        except Exception as e:
            print(f"获取歌曲信息失败 {song_url}: {e}")
        return None

    async def insert_music(self, song_info, singer_id, singer_name, local_play_url, cover, source_url):
        """插入歌曲信息"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                audio_id = song_info.get('audio_id')
                # 检查歌曲是否存在
                cursor.execute(
                    "SELECT id FROM music WHERE audio_id = %s",
                    (audio_id,)
                )
                result = cursor.fetchone()
                if not result:
                    cursor.execute(
                        """INSERT INTO music
                           (album_id, song_name, author_id, author_name, album_name, language,
                            is_publish, audio_id, album_audio_id, cover, play_url, local_play_url,
                            source_name, source_url, lyrics, create_time, update_time)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            song_info.get('album_id'),
                            song_info.get('song_name'),
                            singer_id,
                            singer_name,
                            song_info.get('album_name'),
                            song_info.get('language'),
                            1,  # is_publish
                            audio_id,
                            song_info.get('album_audio_id'),
                            cover,
                            song_info.get('play_url'),
                            local_play_url,
                            '酷狗音乐',
                            source_url,
                            song_info.get('lyrics'),
                            datetime.now(),
                            datetime.now()
                        )
                    )
                    conn.commit()
        finally:
            conn.close()

    async def download_file(self, url, local_path):
        """下载文件"""
        try:
            if os.path.exists(local_path):
                return

            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        with open(local_path, 'wb') as f:
                            f.write(await response.read())
                        print(f"下载成功: {local_path}")
        except Exception as e:
            print(f"下载失败 {url}: {e}")

    async def run(self):
        """主运行方法"""
        async with async_playwright() as p:
            # 检查是否有cookie缓存
            has_cookie = os.path.exists(self.cookie_file)

            if has_cookie:
                # 有cookie使用无头浏览器
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                await self.load_cookies(context)
            else:
                # 无cookie使用有界面浏览器
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()

            page = await context.new_page()

            # 访问页面
            await page.goto(self.base_url)
            await page.wait_for_timeout(3000)

            # 如果没有cookie，进行登录
            if not has_cookie:
                await self.login(page)
                await self.save_cookies(context)

            # 获取分类列表
            categories = await self.get_categories(page)
            print(f"获取到 {len(categories)} 个分类")

            # 遍历分类获取歌手
            all_data = []

            for idx, category in enumerate(categories):
                print(f"正在处理分类 [{idx + 1}/{len(categories)}]: {category['name']}")

                # 点击分类
                category_link = page.locator(f'a[title="{category["name"]}"]')
                if await category_link.count() > 0:
                    await category_link.click()
                    await page.wait_for_timeout(3000)

                # 获取歌手链接
                hrefs = await self.get_singer_links(page, category['name'])
                category_id = await self.get_category_id(category['name'])

                category_data = {
                    'category': category['name'],
                    'hrefs': hrefs
                }
                all_data.append(category_data)

                # 保存进度
                self.save_progress(all_data)

                # 处理每个歌手
                for href in hrefs:
                    await self.get_singer_info(page, href, category_id)
                    await page.wait_for_timeout(1000)

            # 保存最终结果
            with open(self.result_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)

            await browser.close()

    def save_progress(self, data):
        """保存进度"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


async def main():
    spider = KuGouSpider()
    await spider.run()


if __name__ == '__main__':
    asyncio.run(main())