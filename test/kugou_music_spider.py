# -*- coding: utf-8 -*-
"""
酷狗音乐爬虫 (Playwright 实现，非 selenium)
流程:
  1. 打开酷狗音乐歌手页 https://www.kugou.com/yy/singer/index/1-all-2.html
  2. 无cookie -> 有界面浏览器, 点击登录按钮弹二维码, 等待15秒人工扫码; 有cookie -> 无头浏览器
  4-5. 左侧分类(排除"全部歌手") -> 插入 music_author_category
  6-8. 点击分类 -> 右侧歌手列表分页抓取所有歌手 href -> [{category, hrefs}]
  10. 结果写入本地 singer_data.json
  11. 处理进度写入 kugou_progress.json, 中断后可断点续跑
  12. 歌手详情页 script 中 songsdata 即歌曲列表; 逐个打开 song_url 歌曲详情页
  16. 捕获歌曲详情页网络请求 https://wwwapi.kugou.com/play/songinfo 的响应数据
  13/17/18. 下载头像 / 音乐mp3 / 歌曲封面 到本地 static 目录, 拼接 /static/... 访问地址
  14/15/19. 歌手插入 music_authors(author_id去重, 带category_id), 歌曲插入 music(audio_id去重)
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import aiohttp
import pymysql
from playwright.async_api import async_playwright

BASE = 'https://www.kugou.com'
BASE_URL = 'https://www.kugou.com/yy/singer/index/1-all-2.html'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

SCRIPT_DIR = Path(__file__).resolve().parent
COOKIE_FILE = SCRIPT_DIR / 'kugou_cookies.json'
SINGER_DATA_FILE = SCRIPT_DIR / 'singer_data.json'      # [{category, hrefs}] 点10
PROGRESS_FILE = SCRIPT_DIR / 'kugou_progress.json'      # 断点续跑状态 点11
IMAGE_DIR = '/Users/wuwenqiang/Documents/static/music/images'
MUSIC_DIR = '/Users/wuwenqiang/Documents/static/music/kugou'

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'wwq_2021',
    'database': 'play2',
    'charset': 'utf8mb4',
}


class KuGouSpider:
    def __init__(self, max_categories=0, max_singers=0, max_songs=0, category_filter=None, skip_collect=False):
        self.max_categories = max_categories
        self.max_singers = max_singers
        self.max_songs = max_songs
        self.category_filter = category_filter
        self.skip_collect = skip_collect

        os.makedirs(IMAGE_DIR, exist_ok=True)
        os.makedirs(MUSIC_DIR, exist_ok=True)

        # 歌曲详情接口捕获状态
        self._song_event = asyncio.Event()
        self._song_data = None

    # ================= 数据库 =================

    def get_conn(self):
        return pymysql.connect(**DB_CONFIG)

    def insert_category(self, name):
        """插入分类, 已存在则忽略, 返回分类id"""
        conn = self.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM music_author_category WHERE category_name = %s", (name,))
                r = cursor.fetchone()
                if r:
                    return r[0]
                now = datetime.now()
                cursor.execute(
                    "INSERT INTO music_author_category (category_name, create_time, update_time, disabled) "
                    "VALUES (%s, %s, %s, 0)",
                    (name, now, now))
                conn.commit()
                print(f"  插入分类成功: {name}")
                return cursor.lastrowid
        except Exception as e:
            print(f"  插入分类失败 {name}: {e}")
            return None
        finally:
            conn.close()

    def get_category_id(self, name):
        conn = self.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM music_author_category WHERE category_name = %s", (name,))
                r = cursor.fetchone()
                return r[0] if r else None
        finally:
            conn.close()

    def insert_author(self, author_id, author_name, category_id, avatar):
        """插入歌手, 根据 author_id 去重; 已存在且 category_id 为空则补上分类"""
        if author_id is None:
            return
        conn = self.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, category_id FROM music_authors WHERE author_id = %s", (author_id,))
                r = cursor.fetchone()
                if r:
                    if r[1] is None and category_id:
                        cursor.execute("UPDATE music_authors SET category_id = %s WHERE id = %s", (category_id, r[0]))
                        conn.commit()
                        print(f"  歌手已存在, 补全分类: {author_name}")
                    else:
                        print(f"  歌手已存在, 跳过: {author_name}")
                    return
                now = datetime.now()
                cursor.execute(
                    "INSERT INTO music_authors (author_id, author_name, category_id, avatar, create_time, update_time) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (author_id, author_name, category_id, avatar, now, now))
                conn.commit()
                print(f"  插入歌手成功: {author_name}")
        except Exception as e:
            print(f"  插入歌手失败 {author_name}: {e}")
        finally:
            conn.close()

    def insert_music(self, info, song, singer_id, singer_name, local_play_url, cover, source_url):
        """插入歌曲, 根据 audio_id 去重"""
        audio_id = info.get('audio_id')
        if audio_id is None:
            print("      songinfo 无 audio_id, 跳过")
            return
        conn = self.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM music WHERE audio_id = %s", (int(audio_id),))
                if cursor.fetchone():
                    print(f"      歌曲已存在, 跳过: {info.get('song_name')} (audio_id={audio_id})")
                    return

                publish_date = None
                pd = song.get('publish_date')
                if pd:
                    try:
                        publish_date = datetime.strptime(str(pd)[:10], '%Y-%m-%d')
                    except Exception:
                        publish_date = None

                language = (info.get('trans_param') or {}).get('language') or info.get('language')
                version = song.get('version')
                album_id = int(info['album_id']) if info.get('album_id') else None
                album_audio_id = int(info['album_audio_id']) if info.get('album_audio_id') else None

                cursor.execute(
                    """INSERT INTO music
                       (album_id, song_name, author_id, author_name, album_name, version, language,
                        publish_date, is_publish, audio_id, album_audio_id, cover, play_url,
                        local_play_url, source_name, source_url, lyrics, create_time, update_time)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (album_id,
                     info.get('song_name'),
                     str(info.get('author_id') or singer_id),
                     info.get('author_name') or singer_name,
                     info.get('album_name'),
                     str(version) if version is not None else None,
                     language,
                     publish_date,
                     int(info.get('is_publish', 1) or 1),
                     int(audio_id),
                     album_audio_id,
                     cover,
                     info.get('play_url') or info.get('play_backup_url'),
                     local_play_url,
                     '酷狗音乐',
                     source_url,
                     info.get('lyrics'),
                     datetime.now(), datetime.now()))
                conn.commit()
                print(f"      插入歌曲成功: {info.get('song_name')}")
        except Exception as e:
            print(f"      插入歌曲失败: {e}")
        finally:
            conn.close()

    # ================= cookie / 登录 =================

    async def save_cookies(self, context):
        cookies = await context.cookies()
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookies, f)
        print(f"cookie 已保存: {COOKIE_FILE}")

    async def load_cookies(self, context):
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE) as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print(f"已加载 cookie: {len(cookies)} 条")
            return True
        return False

    async def do_login(self, page):
        """无cookie时: 有界面浏览器, 点击登录按钮弹出二维码, 等待15秒人工扫码"""
        try:
            login_btn = page.locator('div.cmhead1_d5._login:has-text("登录")')
            await login_btn.first.wait_for(state='attached', timeout=15000)
            await login_btn.first.click()
            print("已点击登录按钮，请在弹出的窗口中扫描二维码登录（等待15秒）...")
            await page.wait_for_timeout(15000)
            return True
        except Exception as e:
            print(f"登录流程异常: {e}")
            return False

    # ================= 分类 =================

    async def get_categories(self, page):
        """获取左侧分类列表, 排除"全部歌手", 并写入分类表"""
        await page.wait_for_selector('.l ul li a', timeout=15000)
        links = page.locator('.l ul li a')
        categories = []
        seen = set()
        for i in range(await links.count()):
            name = await links.nth(i).get_attribute('title')
            href = await links.nth(i).get_attribute('href')
            if not name or not href:
                continue
            if name in ('全部歌手', '全部') or name in seen:
                continue
            if '/yy/singer/index/' not in href:
                continue
            seen.add(name)
            m = re.search(r'/singer/index/1-all-(\d+)\.html', href)
            cat_id = m.group(1) if m else ''
            self.insert_category(name)
            categories.append({'name': name, 'url': urljoin(BASE, href), 'cat_id': cat_id})
        return categories

    # ================= 歌手列表采集(分页) =================

    async def collect_singer_hrefs(self, page, cat):
        """
        抓取某分类下所有歌手 href。
        分页规律: 第n页 URL 为 /yy/singer/index/{n}-all-{cat_id}.html
        访问不存在的页码会"钳制"到最后一页(内容与最后一页相同), 因此用内容签名判断是否到最后一页。
        """
        hrefs = []
        prev_sig = None
        n = 1
        while n <= 100:
            url = cat['url'] if n == 1 else f"{BASE}/yy/singer/index/{n}-all-{cat['cat_id']}.html"
            try:
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            except Exception as e:
                print(f"  访问分页失败 {url}: {e}")
                break
            try:
                await page.wait_for_selector(
                    '#list_head a[href*="/singer/info/"], #list1 a[href*="/singer/info/"]',
                    state='attached', timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(1500)

            links = await page.locator(
                '#list_head a[href*="/singer/info/"], #list1 a[href*="/singer/info/"]'
            ).evaluate_all("els => els.map(e => e.href)")
            links = list(dict.fromkeys(links))  # 去重保序

            if not links:
                print(f"  第 {n} 页无歌手链接, 停止翻页")
                break
            sig = links[:5]
            if sig == prev_sig:
                print(f"  第 {n} 页与上一页内容相同(已到最后一页), 停止翻页")
                break
            prev_sig = sig
            hrefs.extend(links)
            print(f"  第 {n} 页获取到 {len(links)} 个歌手")
            n += 1

        return list(dict.fromkeys(hrefs))

    # ================= 歌手详情 + 歌曲 =================

    async def process_singer(self, singer_page, song_page, href, category_name):
        try:
            await singer_page.goto(href, timeout=30000, wait_until='domcontentloaded')
            await singer_page.wait_for_timeout(2500)
            content = await singer_page.content()

            m_name = re.search(r"singername = '([^']+)'", content)
            m_id = re.search(r"singerID = '([^']+)'", content)
            if not m_name or not m_id:
                print(f"  未找到歌手信息, 跳过: {href}")
                return
            singer_name, singer_id_str = m_name.group(1), m_id.group(1)
            print(f"  歌手: {singer_name} (ID: {singer_id_str})")

            # ---- 头像下载(点13) ----
            avatar = ''
            try:
                img = singer_page.locator('.top img').first
                candidates = [await img.get_attribute('_src'), await img.get_attribute('src')]
                for u in candidates:
                    if u and ('uploadpic' in u or 'singerimg' in u or 'softhead' in u):
                        fname = os.path.basename(urlsplit(u).path)
                        if await self.download_file(u, os.path.join(IMAGE_DIR, fname)):
                            avatar = f'/static/music/images/{fname}'
                        break
            except Exception as e:
                print(f"  获取头像失败: {e}")

            # ---- 插入歌手(点14/15) ----
            category_id = self.get_category_id(category_name)
            try:
                author_id_int = int(singer_id_str)
            except ValueError:
                author_id_int = singer_id_str
            self.insert_author(author_id_int, singer_name, category_id, avatar)

            # ---- songsdata 歌曲列表(点12) ----
            m_sd = re.search(r'songsdata\s*=\s*(\[.*?\]);', content, re.DOTALL)
            if not m_sd:
                print(f"  未找到歌曲数据: {singer_name}")
                return
            try:
                songs = json.loads(m_sd.group(1))
            except json.JSONDecodeError as e:
                print(f"  songsdata 解析失败: {e}")
                return
            print(f"  获取到 {len(songs)} 首歌曲")

            if self.max_songs > 0:
                songs = songs[:self.max_songs]

            for idx, song in enumerate(songs):
                song_url = song.get('song_url')
                if not song_url:
                    continue
                print(f"    歌曲 [{idx + 1}/{len(songs)}]: {song.get('audio_name')} -> {song_url}")
                # 点16: 打开歌曲详情页, 捕获 songinfo 接口
                info = await self.capture_song_info(song_page, song_url)
                if not info:
                    print(f"    未捕获到歌曲信息, 跳过: {song_url}")
                    continue

                # 点17: 下载音乐
                play_url = info.get('play_url') or info.get('play_backup_url')
                local_play_url = ''
                if play_url:
                    fname = os.path.basename(urlsplit(play_url).path)
                    if await self.download_file(play_url, os.path.join(MUSIC_DIR, fname)):
                        local_play_url = f'/static/music/kugou/{fname}'

                # 点18: 下载封面
                cover = ''
                img_url = info.get('img')
                if img_url:
                    fname = os.path.basename(urlsplit(img_url).path)
                    if await self.download_file(img_url, os.path.join(IMAGE_DIR, fname)):
                        cover = f'/static/music/images/{fname}'

                # 点19/20: 插入歌曲
                self.insert_music(info, song, singer_id_str, singer_name, local_play_url, cover, href)
        except Exception as e:
            print(f"  处理歌手失败 {href}: {e}")

    async def capture_song_info(self, song_page, song_url):
        """打开歌曲详情页, 捕获 wwwapi.kugou.com/play/songinfo 网络请求响应"""
        self._song_data = None
        self._song_event.clear()
        try:
            await song_page.goto(song_url, timeout=30000, wait_until='domcontentloaded')
        except Exception as e:
            print(f"    打开歌曲页失败: {e}")
            return None
        try:
            await asyncio.wait_for(self._song_event.wait(), timeout=25)
        except asyncio.TimeoutError:
            print(f"    等待 songinfo 接口超时: {song_url}")
        await song_page.wait_for_timeout(500)
        return self._song_data

    async def _on_song_response(self, response):
        try:
            if 'wwwapi.kugou.com/play/songinfo' in response.url:
                data = await response.json()
                if data.get('status') == 1 and data.get('err_code') == 0:
                    self._song_data = data.get('data')
                    self._song_event.set()
        except Exception:
            pass

    # ================= 下载 =================

    async def download_file(self, url, local_path):
        if os.path.exists(local_path):
            return True
        headers = {'User-Agent': UA, 'Referer': 'https://www.kugou.com/'}
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=60)) as resp:
                        if resp.status == 200:
                            os.makedirs(os.path.dirname(local_path), exist_ok=True)
                            with open(local_path, 'wb') as f:
                                f.write(await resp.read())
                            print(f"    下载成功: {os.path.basename(local_path)}")
                            return True
                        print(f"    下载失败 status={resp.status}: {url[:90]}")
            except Exception as e:
                print(f"    下载异常: {e}")
            await asyncio.sleep(1)
        return False

    # ================= 本地进度(点10/11) =================

    def load_singer_data(self):
        if os.path.exists(SINGER_DATA_FILE):
            try:
                return json.load(open(SINGER_DATA_FILE, encoding='utf-8'))
            except Exception:
                return []
        return []

    def save_singer_data(self, data):
        with open(SINGER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_progress(self):
        default = {'current': {}, 'done': {}}
        if os.path.exists(PROGRESS_FILE):
            try:
                p = json.load(open(PROGRESS_FILE, encoding='utf-8'))
                return {'current': p.get('current', {}), 'done': p.get('done', {})}
            except Exception:
                return default
        return default

    def save_progress(self, progress):
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    # ================= 主流程 =================

    async def run(self):
        async with async_playwright() as p:
            has_cookie = os.path.exists(COOKIE_FILE)

            # 点2/3: 有cookie无头浏览器, 无cookie有界面浏览器+扫码登录
            browser = await p.chromium.launch(headless=has_cookie)
            context = await browser.new_context(viewport={'width': 1280, 'height': 800}, user_agent=UA)
            if has_cookie:
                await self.load_cookies(context)

            page = await context.new_page()
            song_page = await context.new_page()
            song_page.on('response', self._on_song_response)

            print("正在访问页面...")
            await page.goto(BASE_URL, timeout=30000)
            await page.wait_for_timeout(5000)

            if not has_cookie:
                await self.do_login(page)
                await self.save_cookies(context)
                await page.goto(BASE_URL, timeout=30000)
                await page.wait_for_timeout(5000)

            # ---------- 阶段一: 分类 + 歌手href收集(点4-10) ----------
            singer_data = self.load_singer_data()
            if not self.skip_collect or not singer_data:
                categories = await self.get_categories(page)
                print(f"获取到 {len(categories)} 个分类")
                if self.max_categories > 0:
                    categories = categories[:self.max_categories]

                singer_data = []
                for idx, cat in enumerate(categories):
                    print(f"\n正在处理分类 [{idx + 1}/{len(categories)}]: {cat['name']}")
                    hrefs = await self.collect_singer_hrefs(page, cat)
                    print(f"分类 {cat['name']} 共获取到 {len(hrefs)} 个歌手")
                    singer_data.append({'category': cat['name'], 'hrefs': hrefs})
                    self.save_singer_data(singer_data)
            else:
                print(f"复用已有 singer_data.json: {len(singer_data)} 个分类")

            # ---------- 阶段二: 歌手详情 + 歌曲处理(点11-20) ----------
            progress = self.load_progress()
            done = progress.setdefault('done', {})
            total_cats = len(singer_data)

            for ci, item in enumerate(singer_data):
                cat_name = item['category']
                if self.category_filter and cat_name != self.category_filter:
                    continue
                hrefs = item['hrefs']
                done_hrefs = set(done.get(cat_name, []))
                processed = 0

                for hi, href in enumerate(hrefs):
                    if href in done_hrefs:
                        continue
                    if self.max_singers > 0 and processed >= self.max_singers:
                        break
                    processed += 1

                    # 点11: 记录当前正在处理的分类和href
                    progress['current'] = {'category': cat_name, 'href': href}
                    self.save_progress(progress)

                    print(f"\n[{ci + 1}/{total_cats}] {cat_name} 歌手 [{hi + 1}/{len(hrefs)}]: {href}")
                    await self.process_singer(page, song_page, href, cat_name)

                    done.setdefault(cat_name, []).append(href)
                    progress['current'] = {}
                    self.save_progress(progress)
                    await page.wait_for_timeout(800)

            print("\n全部处理完成！")
            await browser.close()


async def main():
    parser = argparse.ArgumentParser(description='酷狗音乐爬虫')
    parser.add_argument('--max-categories', type=int, default=0, help='最多处理前N个分类, 0=全部')
    parser.add_argument('--max-singers', type=int, default=0, help='每个分类最多处理N个歌手, 0=全部')
    parser.add_argument('--max-songs', type=int, default=0, help='每个歌手最多处理N首歌曲, 0=全部')
    parser.add_argument('--category', default=None, help='只处理指定分类名')
    parser.add_argument('--skip-collect', action='store_true', help='复用 singer_data.json, 跳过分类收集')
    args = parser.parse_args()

    spider = KuGouSpider(
        max_categories=args.max_categories,
        max_singers=args.max_singers,
        max_songs=args.max_songs,
        category_filter=args.category,
        skip_collect=args.skip_collect,
    )
    await spider.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被中断, 进度已保存, 重新运行即可断点续跑")
        sys.exit(1)
