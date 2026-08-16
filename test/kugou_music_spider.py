# -*- coding: utf-8 -*-
"""
酷狗音乐爬虫 (Playwright 实现，非 selenium)
流程:
  1. 打开酷狗音乐歌手页 https://www.kugou.com/yy/singer/index/1-all-2.html
  2. 启动时提示是否清除缓存(默认1清除): 清除->有头浏览器重新扫码登录; 不清除->缓存有效用无头, 无缓存/缓存失效用有头; 滑块验证码需手动拖动完成(程序会提示并等待)
  4-5. 左侧分类(排除"全部歌手") -> 插入 music_author_category
  6-8. 点击分类 -> 右侧歌手列表分页抓取所有歌手 href -> [{category, hrefs}]
  10. 结果写入本地 singer_data.json, 再次运行默认直接复用本地文件不再重复抓取(可用 --refresh-collect 强制重新获取)
  11. 处理进度写入 kugou_progress.json, 中断后可断点续跑; 歌曲页提示"获取数据失败"的歌曲记入 failed_songs.json 作记录, 下次运行重新获取(失败可能因IP被封)
  12. 歌手详情页 script 中 songsdata 即歌曲列表; 逐个打开 song_url 歌曲详情页
  16. 捕获歌曲详情页网络请求 https://wwwapi.kugou.com/play/songinfo 的响应数据
  13/17/18. 下载头像 / 音乐mp3 / 歌曲封面 到本地 static 目录, 拼接 /static/... 访问地址
  14/15/19. 歌手插入 music_authors(author_id去重, 带category_id), 歌曲插入 music(audio_id去重)
"""

import argparse
import asyncio
import json
import os
import random
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
FAILED_SONGS_FILE = SCRIPT_DIR / 'failed_songs.json'    # 歌曲页提示"获取数据失败"的记录, 下次运行重新获取

# 全部歌手分类名 (本地 singer_data.json 完整性校验用)
EXPECTED_CATEGORIES = ['华语男歌手', '华语女歌手', '华语组合', '日韩男歌手', '日韩女歌手', '日韩组合',
                       '欧美男歌手', '欧美女歌手', '欧美组合', '其他歌手']

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'wwq_2021',
    'database': 'play2',
    'charset': 'utf8mb4',
}


class KuGouSpider:
    def __init__(self, max_categories=0, max_singers=0, max_songs=0, category_filter=None, skip_collect=False,
                 headless=False, refresh_collect=False, clear_cache=None):
        self.max_categories = max_categories
        self.max_singers = max_singers
        self.max_songs = max_songs
        self.category_filter = category_filter
        self.skip_collect = skip_collect
        self.headless = headless
        self.refresh_collect = refresh_collect
        self.clear_cache = clear_cache  # True=清除cookie缓存(有头登录), False=不清除, None=未交互(兜底按清除)

        os.makedirs(IMAGE_DIR, exist_ok=True)
        os.makedirs(MUSIC_DIR, exist_ok=True)

        # 歌曲详情接口捕获状态
        self._song_event = asyncio.Event()
        self._song_data = None
        self._song_api_error = False   # 接口返回了错误(status!=1/err_code!=0)
        self._last_capture_datafail = False  # 本次捕获是否因"获取数据失败"弹窗而跳过

        # "获取数据失败"记录(持久化到本地; 失败可能因IP被封, 下次运行重新获取)
        self.failed_songs = self.load_failed_songs()

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

    def music_exists(self, audio_id):
        """按 audio_id 查询歌曲是否已入库 (供入库前快速判断, 已存在则跳过)"""
        try:
            conn = self.get_conn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM music WHERE audio_id = %s", (int(audio_id),))
                    return cursor.fetchone() is not None
            finally:
                conn.close()
        except Exception:
            return False

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
        """插入歌曲, 根据 audio_id 去重; 返回 True=真正插入 / False=已存在或失败"""
        audio_id = info.get('audio_id')
        if audio_id is None:
            print("      songinfo 无 audio_id, 跳过")
            return False
        conn = self.get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM music WHERE audio_id = %s", (int(audio_id),))
                if cursor.fetchone():
                    print(f"      歌曲已存在, 跳过: {info.get('song_name')} (audio_id={audio_id})")
                    return False

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
                return True
        except Exception as e:
            print(f"      插入歌曲失败: {e}")
            return False
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
        """点击登录按钮弹出二维码, 等待15秒手动扫码登录"""
        try:
            login_btn = page.locator('div.cmhead1_d5._login:has-text("登录")')
            await login_btn.first.wait_for(state='attached', timeout=15000)
            await login_btn.first.click()
            print("已点击登录按钮，登录二维码已弹出，请扫码登录（等待15秒）...")
            print("提示: 登录后若页面弹出滑块验证码，请手动拖动滑块完成拼图")
            await page.wait_for_timeout(15000)
            return True
        except Exception as e:
            print(f"登录流程异常: {e}")
            return False

    async def is_logged_in(self, page):
        """判断当前是否已登录: 页面顶部可见的"登录"按钮存在即视为未登录"""
        try:
            login_btn = page.locator('div.cmhead1_d5._login:has-text("登录")')
            if await login_btn.count() > 0 and await login_btn.first.is_visible():
                return False
            return True
        except Exception:
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
    # 返回值: True=成功 / False=页面无数据(标记done) / 'blocked'=验证码未完成(留待下次重试)

    async def process_singer(self, singer_page, song_page, href, category_name):
        try:
            await singer_page.goto(href, timeout=30000, wait_until='domcontentloaded')
            await singer_page.wait_for_timeout(2500)
            content = await singer_page.content()

            m_name = re.search(r"singername = '([^']+)'", content)
            m_id = re.search(r"singerID = '([^']+)'", content)
            if not m_name or not m_id:
                # 歌手页可能被滑块验证码挡住, 提示人工完成后等待页面自行加载
                if await self.has_captcha(singer_page):
                    print(f"  !! 歌手页弹出滑块验证码, 请在浏览器中拖动滑块完成拼图 (最多等待180秒)...")
                    resolved = False
                    for _ in range(36):  # 36 * 5s = 180s
                        await singer_page.wait_for_timeout(5000)
                        content = await singer_page.content()
                        m_name = re.search(r"singername = '([^']+)'", content)
                        m_id = re.search(r"singerID = '([^']+)'", content)
                        if m_name and m_id:
                            resolved = True
                            break
                    if not resolved:
                        print(f"  人工验证超时, 留待下次续跑重试: {href}")
                        return 'blocked'
                else:
                    print(f"  未找到歌手信息, 跳过: {href}")
                    return False
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
                return True
            try:
                songs = json.loads(m_sd.group(1))
            except json.JSONDecodeError as e:
                print(f"  songsdata 解析失败: {e}")
                return True
            print(f"  获取到 {len(songs)} 首歌曲")

            if self.max_songs > 0:
                songs = songs[:self.max_songs]

            for idx, song in enumerate(songs):
                song_url = song.get('song_url')
                if not song_url:
                    continue

                # failed_songs.json 仅作记录: 上次"获取数据失败"的歌曲可能因IP被封导致,
                # 下次运行重新获取, 不跳过

                # 需求3: 先查数据库, 已存在的歌曲直接查下一首, 不打开页面也不等待10秒
                audio_id = song.get('audio_id')
                if audio_id is not None and self.music_exists(audio_id):
                    print(f"    歌曲已存在数据库, 跳过: {song.get('audio_name')} (audio_id={audio_id})")
                    continue

                print(f"    歌曲 [{idx + 1}/{len(songs)}]: {song.get('audio_name')} -> {song_url}")
                # 点16: 打开歌曲详情页, 捕获 songinfo 接口
                info = await self.capture_song_info(song_page, song_url)
                # 已打开歌曲播放页: 无论是否获取到播放地址, 都睡眠10秒再处理下一首,
                # 降低页面打开频率, 防止IP被封禁 (已存在数据库的歌曲不打开页面, 不等待)
                await song_page.wait_for_timeout(10000)
                if not info:
                    # "获取数据失败"(无法获取播放地址)的歌曲记入 failed_songs.json 作记录,
                    # 失败可能因IP被封, 下次运行会重新获取
                    if self._last_capture_datafail or await self.has_datafail_dialog(song_page):
                        print(f"    该歌曲无法获取播放地址, 已记录到 failed_songs.json(下次运行重新获取): {song_url}")
                        self.failed_songs.add(song_url)
                        self.save_failed_songs(self.failed_songs)
                    else:
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

                # 点19/20: 插入歌曲 (内部按audio_id去重)
                self.insert_music(info, song, singer_id_str, singer_name, local_play_url, cover, href)
            return True
        except Exception as e:
            print(f"  处理歌手失败 {href}: {e}")
            return False

    async def has_captcha(self, page):
        """检测页面是否弹出滑块验证码 (扫描所有frame的可见文本)"""
        markers = ('拖动滑块', '拖动下面滑块', '拖动下方滑块', '向右拖动', '完成拼图', '滑块验证', '请完成验证')
        try:
            for frame in page.frames:
                try:
                    text = await frame.evaluate(
                        "() => document.body ? document.body.innerText.slice(0, 3000) : ''")
                except Exception:
                    continue
                if text and any(m in text for m in markers):
                    return True
        except Exception:
            pass
        return False

    async def has_datafail_dialog(self, page):
        """检测歌曲页是否弹出"获取数据失败"提示框 (div.ui-dialog.getdatafail)"""
        try:
            dlg = page.locator('div.ui-dialog.getdatafail')
            if await dlg.count() > 0 and await dlg.first.is_visible():
                return True
            # 兜底: 扫描所有frame可见文本
            for frame in page.frames:
                try:
                    text = await frame.evaluate(
                        "() => document.body ? document.body.innerText.slice(0, 3000) : ''")
                except Exception:
                    continue
                if text and '获取数据失败' in text:
                    return True
        except Exception:
            pass
        return False

    async def wait_for_datafail_dialog(self, page, timeout=25):
        """接口无响应时轮询等待"获取数据失败"弹窗出现(该弹窗渲染较慢, 约20-30秒)"""
        loop = asyncio.get_event_loop()
        end = loop.time() + timeout
        while loop.time() < end:
            if await self.has_datafail_dialog(page):
                return True
            await page.wait_for_timeout(2000)
        return False

    async def capture_song_info(self, song_page, song_url):
        """打开歌曲详情页, 捕获 wwwapi.kugou.com/play/songinfo 网络请求响应。
        - 页面弹"获取数据失败"(div.ui-dialog.getdatafail): 该歌曲无法获取播放地址,
          直接跳过并标记, 不重试也不提示"接口无响应"
        - 滑块验证码: 提示人工完成并等待(最多180秒)
        - 其余无响应: 最多重试3次"""
        for attempt in range(1, 4):
            self._song_data = None
            self._song_event.clear()
            self._song_api_error = False
            self._last_capture_datafail = False
            try:
                await song_page.goto(song_url, timeout=30000, wait_until='domcontentloaded')
            except Exception as e:
                print(f"    打开歌曲页失败: {e}")
                return None

            # 页面已弹出"获取数据失败"弹窗(接口报错后立即渲染), 直接跳过
            if await self.has_datafail_dialog(song_page):
                self._last_capture_datafail = True
                return None

            try:
                # 接口响应到达即继续
                await asyncio.wait_for(self._song_event.wait(), timeout=15)
            except asyncio.TimeoutError:
                pass

            await song_page.wait_for_timeout(500)

            if self._song_data:
                return self._song_data

            # 接口明确返回错误(status!=1/err_code!=0): 该歌曲无法获取播放地址, 直接跳过并标记
            if self._song_api_error:
                self._last_capture_datafail = True
                return None

            # 接口无响应时, 页面可能稍后才弹"获取数据失败"弹窗, 轮询等待(最多25秒)
            if await self.wait_for_datafail_dialog(song_page, timeout=25):
                self._last_capture_datafail = True
                return None

            if await self.has_captcha(song_page):
                print(f"    !! 歌曲页弹出滑块验证码, 请在浏览器中拖动滑块完成拼图 (最多等待180秒)...")
                try:
                    await asyncio.wait_for(self._song_event.wait(), timeout=180)
                except asyncio.TimeoutError:
                    print(f"    等待人工验证超时 [{attempt}/3], 重试: {song_url}")
                    continue
                if self._song_data:
                    return self._song_data
                print(f"    验证后接口仍未返回数据 [{attempt}/3], 重试: {song_url}")
            else:
                # 只有接口完全无响应时才会走到这里; "获取数据失败"的歌曲在弹窗检测处直接返回
                print(f"    歌曲接口无响应 [{attempt}/3], 15秒后重试: {song_url}")
                await song_page.wait_for_timeout(15000)
        return None

    async def _on_song_response(self, response):
        try:
            if 'wwwapi.kugou.com/play/songinfo' in response.url:
                data = await response.json()
                if data.get('status') == 1 and data.get('err_code') == 0:
                    self._song_data = data.get('data')
                else:
                    self._song_api_error = True
                # 无论成败都唤醒等待, 由上层判断(失败时页面通常弹"获取数据失败"提示框)
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

    def load_failed_songs(self):
        """读取"获取数据失败"歌曲记录(仅作记录, 不再用于跳过)"""
        if os.path.exists(FAILED_SONGS_FILE):
            try:
                return set(json.load(open(FAILED_SONGS_FILE, encoding='utf-8')))
            except Exception:
                return set()
        return set()

    def save_failed_songs(self, failed_songs):
        """保存"获取数据失败"歌曲记录"""
        with open(FAILED_SONGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(failed_songs), f, ensure_ascii=False, indent=2)

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

    def is_singer_data_complete(self, data):
        """本地 singer_data.json 是否完整(覆盖全部10个分类且每类都有歌手href)"""
        if not data:
            return False
        names = {d.get('category') for d in data if isinstance(d, dict)}
        if not all(c in names for c in EXPECTED_CATEGORIES):
            return False
        return all(isinstance(d.get('hrefs'), list) and d['hrefs'] for d in data if isinstance(d, dict))

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

    async def probe_cookie_valid(self, p):
        """用缓存的cookie启动一次无头浏览器访问首页, 检查登录状态, 判断缓存是否有效"""
        try:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(viewport={'width': 1280, 'height': 800}, user_agent=UA)
                await self.load_cookies(context)
                page = await context.new_page()
                await page.goto(BASE_URL, timeout=30000)
                await page.wait_for_timeout(4000)
                return await self.is_logged_in(page)
            finally:
                await browser.close()
        except Exception:
            return False

    async def run(self):
        async with async_playwright() as p:
            has_cookie = os.path.exists(COOKIE_FILE)

            # 启动交互(在main中完成): 选择1清除缓存 -> 必须用有头浏览器重新扫码登录;
            # 选择2不清除缓存 -> 有缓存且有效则用无头, 无缓存/缓存失效则用有头
            clear_cache = True if self.clear_cache is None else self.clear_cache
            headless = self.headless
            if clear_cache:
                if has_cookie:
                    os.remove(COOKIE_FILE)
                    print(f"已清除 cookie 缓存: {COOKIE_FILE}")
                    has_cookie = False
                else:
                    print("无 cookie 缓存可清除")
                headless = False  # 清除缓存后需扫码登录, 必须有头浏览器
            elif not has_cookie:
                print("无 cookie 缓存, 使用有头浏览器扫码登录")
                headless = False
            elif self.headless:
                # --headless 显式指定: 直接用无头, 不探测
                print("--headless 已指定, 使用无头浏览器")
            else:
                # 交互选择不清除缓存: 探测缓存是否有效, 决定无头/有头
                if await self.probe_cookie_valid(p):
                    print("cookie 缓存有效, 使用无头浏览器")
                    headless = True
                else:
                    print("!! cookie 缓存已失效, 改用有头浏览器重新扫码登录")
                    headless = False
            print(f"浏览器模式: {'无头' if headless else '有头'}")

            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1280, 'height': 800}, user_agent=UA)
            if has_cookie:
                await self.load_cookies(context)

            page = await context.new_page()
            song_page = await context.new_page()
            song_page.on('response', self._on_song_response)

            print("正在访问页面...")
            await page.goto(BASE_URL, timeout=30000)
            await page.wait_for_timeout(5000)

            # 打开页面后检测登录状态: 未登录则自动弹出登录二维码, 等待15秒手动扫码后再进行操作
            if await self.is_logged_in(page):
                print("检测到已登录状态, 跳过登录")
            elif headless:
                print("!! 无头模式下检测到未登录(cookie已失效), 无法弹出二维码扫码; 继续以未登录状态运行")
                print("!! 如需重新登录, 请退出后重新运行并选择 1=清除缓存")
            else:
                print("未检测到登录状态, 自动弹出登录二维码...")
                await self.do_login(page)
                await self.save_cookies(context)
                await page.goto(BASE_URL, timeout=30000)
                await page.wait_for_timeout(5000)
                if not await self.is_logged_in(page):
                    print("!! 提示: 未检测到登录成功(可能扫码超时), 继续执行; 若后续页面受限请重新运行")

            # ---------- 阶段一: 分类 + 歌手href收集(点4-10) ----------
            # 默认复用本地 singer_data.json(获取完所有分类歌手后保存), 不再重复抓取;
            # --refresh-collect 强制重新获取, --skip-collect 为兼容旧参数的强制复用
            singer_data = self.load_singer_data()
            use_cache = not self.refresh_collect and (self.skip_collect or self.is_singer_data_complete(singer_data))
            if not use_cache:
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
                print(f"全部分类歌手已保存到本地: {SINGER_DATA_FILE}")
            else:
                print(f"复用本地 singer_data.json: {len(singer_data)} 个分类, 跳过分类歌手收集 (重新获取请加 --refresh-collect)")

            # ---------- 阶段二: 歌手详情 + 歌曲处理(点11-20) ----------
            progress = self.load_progress()
            done = progress.setdefault('done', {})
            total_cats = len(singer_data)
            success_cnt = 0
            blocked_cnt = 0
            missing_cnt = 0

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
                    result = await self.process_singer(page, song_page, href, cat_name)

                    # 只有真正处理成功(或页面确实无数据)才标记done; 验证码未完成的不标记, 下次续跑重试
                    if result == 'blocked':
                        blocked_cnt += 1
                    else:
                        done.setdefault(cat_name, []).append(href)
                        if result is True:
                            success_cnt += 1
                        else:
                            missing_cnt += 1

                    progress['current'] = {}
                    self.save_progress(progress)
                    await page.wait_for_timeout(random.randint(1000, 2000))

            print(f"\n全部处理完成！ 本次运行: 成功 {success_cnt} / 验证码未完成 {blocked_cnt} / 无数据跳过 {missing_cnt}")
            await browser.close()


async def main():
    parser = argparse.ArgumentParser(description='酷狗音乐爬虫')
    parser.add_argument('--max-categories', type=int, default=0, help='最多处理前N个分类, 0=全部')
    parser.add_argument('--max-singers', type=int, default=0, help='每个分类最多处理N个歌手, 0=全部')
    parser.add_argument('--max-songs', type=int, default=0, help='每个歌手最多处理N首歌曲, 0=全部')
    parser.add_argument('--category', default=None, help='只处理指定分类名')
    parser.add_argument('--skip-collect', action='store_true',
                        help='(兼容旧参数) 强制复用本地 singer_data.json')
    parser.add_argument('--refresh-collect', action='store_true',
                        help='强制重新获取所有分类的歌手列表并覆盖本地 singer_data.json')
    parser.add_argument('--headless', action='store_true',
                        help='跳过缓存询问, 强制无头模式(不建议): 无法人工完成滑块验证码, 弹出验证码的歌曲/歌手会被跳过')
    args = parser.parse_args()

    # 启动交互: 是否清除缓存 (默认1=清除缓存, 清除后用有头浏览器重新扫码登录;
    # 不清除则根据缓存有无/是否有效决定无头或有头)
    clear_cache = None
    if args.headless:
        print("--headless 已指定, 跳过缓存询问")
    else:
        choice = input("是否清除缓存? 1=清除缓存(默认, 重新扫码登录), 2=不清除缓存: ").strip() or '1'
        if choice == '1':
            clear_cache = True
        elif choice == '2':
            clear_cache = False
        else:
            print("无效输入, 按默认处理: 清除缓存")
            clear_cache = True

    spider = KuGouSpider(
        max_categories=args.max_categories,
        max_singers=args.max_singers,
        max_songs=args.max_songs,
        category_filter=args.category,
        skip_collect=args.skip_collect,
        headless=args.headless,
        refresh_collect=args.refresh_collect,
        clear_cache=clear_cache,
    )
    await spider.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被中断, 进度已保存, 重新运行即可断点续跑")
        sys.exit(1)
