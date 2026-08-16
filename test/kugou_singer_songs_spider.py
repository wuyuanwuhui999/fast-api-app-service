# -*- coding: utf-8 -*-
"""
酷狗音乐 歌手歌曲补全爬虫 (独立新脚本, 不改动 kugou_music_spider.py)
复用 kugou_music_spider.py 中的 KuGouSpider 全部核心逻辑(数据库操作/cookie登录/
歌曲接口捕获/下载/反爬频率控制), 只新增"歌曲列表收集 + 查库打标志"流程。

流程:
  阶段A: 读取 singer_data.json(分类+歌手详情href) -> 逐个打开歌手详情页
         - 下载头像 + 插入 music_authors(带分类) [与原版相同]
         - 正则解析 songsdata 获取歌手全部歌曲 [与原版相同]
         - 歌曲关联歌手地址/分类, 存本地 singer_songs.json
           (断点续跑, 进度存 singer_songs_progress.json; 已收集歌手跳过)
  阶段B: 读取 singer_songs.json, 每首歌按 audio_id 查 music 表打"下载标志"
         - downloaded=true : 歌曲已在库(status=exists)或本次抓取入库成功(status=saved)
         - downloaded=false: 不在库且获取 songinfo 失败(status=failed)或无播放地址(status=no_url)
         - 不在库的歌曲: 打开歌曲播放页捕获 songinfo -> 下载mp3/封面 -> insert_music [与原版相同]
         - 所有 downloaded=false 的歌曲输出到 missing_songs.json, 便于查看哪些歌曲未获取到

启动交互与原版相同:
  询问"是否清除缓存? 1=清除缓存(默认, 重新扫码登录), 2=不清除缓存"
  - 选1: 删除 kugou_cookies.json, 用有头浏览器重新扫码登录
  - 选2: 无cookie用有头; 有cookie先无头探测有效性, 有效用无头, 失效用有头
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

# 复用原版脚本的全部常量与 KuGouSpider 类 (原文件未做任何改动)
from kugou_music_spider import (
    BASE_URL,
    COOKIE_FILE,
    IMAGE_DIR,
    MUSIC_DIR,
    SINGER_DATA_FILE,
    UA,
    KuGouSpider,
)

SCRIPT_DIR = Path(__file__).resolve().parent
SONGS_DATA_FILE = SCRIPT_DIR / 'singer_songs.json'           # 阶段A收集的歌曲列表(含下载标志)
COLLECT_PROGRESS_FILE = SCRIPT_DIR / 'singer_songs_progress.json'  # 阶段A断点续跑状态
MISSING_SONGS_FILE = SCRIPT_DIR / 'missing_songs.json'       # 阶段B未获取到的歌曲(不在库且抓取失败)


class SingerSongsSpider(KuGouSpider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.singer_songs = self.load_songs_data()

    # ================= 本地数据文件 =================

    def load_songs_data(self):
        if os.path.exists(SONGS_DATA_FILE):
            try:
                return json.load(open(SONGS_DATA_FILE, encoding='utf-8'))
            except Exception:
                return []
        return []

    def save_songs_data(self, data):
        with open(SONGS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_collect_progress(self):
        default = {'current': {}, 'done': {}}
        if os.path.exists(COLLECT_PROGRESS_FILE):
            try:
                p = json.load(open(COLLECT_PROGRESS_FILE, encoding='utf-8'))
                return {'current': p.get('current', {}), 'done': p.get('done', {})}
            except Exception:
                return default
        return default

    def save_collect_progress(self, progress):
        with open(COLLECT_PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def build_missing(self):
        """汇总所有 downloaded=false 的歌曲(未获取到)"""
        missing = []
        for item in self.singer_songs:
            for song in item['songs']:
                if not song.get('downloaded'):
                    missing.append({
                        'category': item['category'],
                        'singer_href': item['singer_href'],
                        'singer_name': item.get('singer_name', ''),
                        'singer_id': item.get('singer_id', ''),
                        'audio_id': song.get('audio_id'),
                        'audio_name': song.get('audio_name'),
                        'song_url': song.get('song_url'),
                        'status': song.get('status', ''),
                    })
        return missing

    def save_missing_songs(self):
        with open(MISSING_SONGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.build_missing(), f, ensure_ascii=False, indent=2)

    # ================= 阶段A: 收集歌手全部歌曲 =================

    async def collect_singer_songs(self, singer_page, href, category_name):
        """打开歌手详情页: 下载头像 + 插入歌手表(带分类) + 解析 songsdata 歌曲列表。
        逻辑与原版 process_singer 相同, 只是不打开歌曲播放页。
        返回: (singer_name, singer_id_str, songs) / 'blocked'(验证码未完成) / None(页面无数据)"""
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
                    return None
            singer_name, singer_id_str = m_name.group(1), m_id.group(1)
            print(f"  歌手: {singer_name} (ID: {singer_id_str})")

            # ---- 头像下载(与原版相同) ----
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

            # ---- 插入歌手(带分类, 与原版相同) ----
            category_id = self.get_category_id(category_name)
            try:
                author_id_int = int(singer_id_str)
            except ValueError:
                author_id_int = singer_id_str
            self.insert_author(author_id_int, singer_name, category_id, avatar)

            # ---- songsdata 歌曲列表(与原版相同) ----
            m_sd = re.search(r'songsdata\s*=\s*(\[.*?\]);', content, re.DOTALL)
            if not m_sd:
                print(f"  未找到歌曲数据: {singer_name}")
                return (singer_name, singer_id_str, [])
            try:
                songs = json.loads(m_sd.group(1))
            except json.JSONDecodeError as e:
                print(f"  songsdata 解析失败: {e}")
                return (singer_name, singer_id_str, [])
            print(f"  获取到 {len(songs)} 首歌曲")
            return (singer_name, singer_id_str, songs)
        except Exception as e:
            print(f"  处理歌手失败 {href}: {e}")
            return None

    async def stage_a(self, singer_page):
        """遍历 singer_data.json, 收集每个歌手的全部歌曲到 singer_songs.json"""
        singer_data = self.load_singer_data()
        if not singer_data:
            print(f"!! singer_data.json 为空或不存在: {SINGER_DATA_FILE}")
            print("!! 请先运行 kugou_music_spider.py 生成歌手数据(或确认文件存在)")
            return

        progress = self.load_collect_progress()
        done = progress.setdefault('done', {})
        # 复用本地已收集的歌曲列表(增量收集), 已收集过的歌手跳过
        singer_songs = self.load_songs_data()
        existing_hrefs = {item['singer_href'] for item in singer_songs}
        total_cats = len(singer_data)

        for ci, item in enumerate(singer_data):
            cat_name = item['category']
            if self.category_filter and cat_name != self.category_filter:
                continue
            hrefs = item['hrefs']
            done_hrefs = set(done.get(cat_name, []))
            processed = 0

            for hi, href in enumerate(hrefs):
                if href in done_hrefs or href in existing_hrefs:
                    continue
                if self.max_singers > 0 and processed >= self.max_singers:
                    break
                processed += 1

                progress['current'] = {'category': cat_name, 'href': href}
                self.save_collect_progress(progress)

                print(f"\n[{ci + 1}/{total_cats}] {cat_name} 歌手 [{hi + 1}/{len(hrefs)}]: {href}")
                result = await self.collect_singer_songs(singer_page, href, cat_name)

                # 验证码未完成不标记done(留待续跑); 其他情况标记done(与原版语义一致)
                if result == 'blocked':
                    print(f"  验证码未完成, 留待下次续跑: {href}")
                elif result is None:
                    print(f"  歌手页面无数据, 标记完成: {href}")
                    done.setdefault(cat_name, []).append(href)
                else:
                    singer_name, singer_id_str, songs = result
                    if self.max_songs > 0:
                        songs = songs[:self.max_songs]
                    singer_songs.append({
                        'category': cat_name,
                        'singer_href': href,
                        'singer_name': singer_name,
                        'singer_id': singer_id_str,
                        'songs': songs,
                    })
                    print(f"  收集到 {len(songs)} 首歌曲")
                    done.setdefault(cat_name, []).append(href)

                progress['current'] = {}
                self.save_collect_progress(progress)
                await singer_page.wait_for_timeout(random.randint(1000, 2000))

            # 每处理完一个分类保存一次歌曲列表(增量, 中断不丢)
            self.save_songs_data(singer_songs)

        self.singer_songs = singer_songs
        print(f"\n阶段A完成: 共收集 {len(singer_songs)} 个歌手的歌曲列表, 已保存到 {SONGS_DATA_FILE}")

    # ================= 阶段B: 查库打标志 + 抓取缺失歌曲入库 =================

    async def process_song(self, song_page, song, singer_name, singer_id, singer_href):
        """单首歌: 按 audio_id 查库打标志; 不在库则打开播放页获取 songinfo -> 下载 -> 入库。
        返回 (downloaded, status)"""
        audio_id = song.get('audio_id')
        song_url = song.get('song_url')
        if audio_id is None or not song_url:
            return False, 'no_url'

        # 先查库: 已存在的歌曲不打开页面、不等待(与原版相同)
        if self.music_exists(audio_id):
            return True, 'exists'

        print(f"  不在数据库, 打开歌曲播放页获取 songinfo...")
        info = await self.capture_song_info(song_page, song_url)
        # 已打开歌曲播放页: 无论是否获取到播放地址, 都睡眠10秒再处理下一首(与原版相同, 防IP封禁)
        await song_page.wait_for_timeout(10000)
        if not info:
            print(f"  获取 songinfo 失败, 标记 downloaded=false (status=failed)")
            return False, 'failed'

        # ---- 下载音乐(与原版相同) ----
        play_url = info.get('play_url') or info.get('play_backup_url')
        local_play_url = ''
        if play_url:
            fname = os.path.basename(urlsplit(play_url).path)
            if await self.download_file(play_url, os.path.join(MUSIC_DIR, fname)):
                local_play_url = f'/static/music/kugou/{fname}'

        # ---- 下载封面(与原版相同) ----
        cover = ''
        img_url = info.get('img')
        if img_url:
            fname = os.path.basename(urlsplit(img_url).path)
            if await self.download_file(img_url, os.path.join(IMAGE_DIR, fname)):
                cover = f'/static/music/images/{fname}'

        # ---- 插入歌曲(内部按audio_id去重, 与原版相同) ----
        inserted = self.insert_music(info, song, singer_id, singer_name, local_play_url, cover, singer_href)
        if inserted or self.music_exists(audio_id):
            print(f"  入库成功, 标记 downloaded=true (status=saved)")
            return True, 'saved'
        print(f"  入库失败, 标记 downloaded=false (status=failed)")
        return False, 'failed'

    async def stage_b(self, song_page):
        """读取 singer_songs.json, 逐首歌查库打标志, 缺失歌曲抓取入库, 输出 missing_songs.json"""
        singer_songs = self.singer_songs if self.singer_songs else self.load_songs_data()
        if not singer_songs:
            print("!! singer_songs.json 为空(阶段A未收集到歌曲), 跳过阶段B")
            return
        self.singer_songs = singer_songs

        total = sum(len(item['songs']) for item in singer_songs)
        print(f"阶段B: 共 {len(singer_songs)} 个歌手, {total} 首歌曲, 开始按 audio_id 查库打标志...")
        stats = {'exists': 0, 'saved': 0, 'failed': 0, 'no_url': 0, 'skipped': 0}
        processed = 0

        for item in singer_songs:
            cat_name = item['category']
            singer_href = item['singer_href']
            singer_name = item.get('singer_name', '')
            singer_id = item.get('singer_id', '')
            changed = False

            for song in item['songs']:
                processed += 1
                # 已打过下载标志(已入库)的歌曲直接跳过, 断点续跑
                if song.get('downloaded'):
                    stats['skipped'] += 1
                    continue

                print(f"\n[{processed}/{total}] {cat_name}/{singer_name}: "
                      f"{song.get('audio_name')} (audio_id={song.get('audio_id')})")
                downloaded, status = await self.process_song(
                    song_page, song, singer_name, singer_id, singer_href)
                song['downloaded'] = downloaded
                song['status'] = status
                stats[status] = stats.get(status, 0) + 1
                changed = True

            if changed:
                self.save_songs_data(singer_songs)
                self.save_missing_songs()
            print(f"  分类 {cat_name} 处理完成")

        # 最终落盘 + 汇总
        self.save_songs_data(singer_songs)
        self.save_missing_songs()
        print(f"\n阶段B完成: 已在库 {stats['exists']} / 本次入库 {stats['saved']} / "
              f"获取失败 {stats['failed']} / 无播放地址 {stats['no_url']} / 已标记跳过 {stats['skipped']}")
        missing = self.build_missing()
        print(f"未获取到的歌曲共 {len(missing)} 首, 已输出到 {MISSING_SONGS_FILE}")

    # ================= 主流程 =================

    async def run(self):
        async with async_playwright() as p:
            has_cookie = os.path.exists(COOKIE_FILE)

            # 启动交互(在main中完成): 选择1清除缓存 -> 必须用有头浏览器重新扫码登录;
            # 选择2不清除缓存 -> 有缓存且有效则用无头, 无缓存/缓存失效则用有头 (与原版相同)
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

            # 打开页面后检测登录状态: 未登录则自动弹出登录二维码, 等待15秒手动扫码 (与原版相同)
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

            # ---------- 阶段A: 收集歌手全部歌曲(存本地 json) ----------
            await self.stage_a(page)

            # ---------- 阶段B: 查库打标志 + 抓取缺失歌曲入库 ----------
            await self.stage_b(song_page)

            print(f"\n全部处理完成! 歌曲列表: {SONGS_DATA_FILE}  未获取到歌曲: {MISSING_SONGS_FILE}")
            await browser.close()


async def main():
    parser = argparse.ArgumentParser(description='酷狗音乐 歌手歌曲补全爬虫')
    parser.add_argument('--max-singers', type=int, default=0, help='每个分类最多处理N个歌手, 0=全部')
    parser.add_argument('--max-songs', type=int, default=0, help='每个歌手最多处理N首歌曲, 0=全部')
    parser.add_argument('--category', default=None, help='只处理指定分类名')
    parser.add_argument('--headless', action='store_true',
                        help='跳过缓存询问, 强制无头模式(不建议): 无法人工完成滑块验证码, 弹出验证码的歌手会被跳过')
    args = parser.parse_args()

    # 启动交互: 是否清除缓存 (默认1=清除缓存, 清除后用有头浏览器重新扫码登录;
    # 不清除则根据缓存有无/是否有效决定无头或有头) -- 与原版相同
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

    spider = SingerSongsSpider(
        max_singers=args.max_singers,
        max_songs=args.max_songs,
        category_filter=args.category,
        headless=args.headless,
        clear_cache=clear_cache,
    )
    await spider.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被中断, 进度已保存, 重新运行即可断点续跑")
        sys.exit(1)
