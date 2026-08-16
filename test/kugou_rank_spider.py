# -*- coding: utf-8 -*-
"""
酷狗音乐 排行榜爬虫 (独立新脚本, 不改动 kugou_music_spider.py)
复用 kugou_music_spider.py 中的 KuGouSpider 全部核心逻辑(cookie登录/歌曲接口捕获/
下载/入库/反爬频率控制), 只新增"排行榜分类解析 + 歌曲列表收集"流程。

页面:
  榜单首页 https://www.kugou.com/yy/rank/home/1-6666.html?from=rank (酷狗飙升榜)
  左侧分类: div.pc_rank_sidebar(大分类容器) > h3 a[title](大分类名)
            > ul > li > a[title][href*="/yy/rank/home/"](小分类: 榜名+地址)
  歌曲列表: div.pc_temp_songlist li[data-eid](eid=mixsong hash)
            > a.pc_temp_songname[href](mixsong播放页) title="歌手 - 歌名"
            > span.pc_temp_time(时长)
  分页: URL 页码替换 {page}-{rank_id}.html (如 2-6666.html), 每页22首;
        总页数从分页器按钮 id="page_last_{n}" 读取

流程:
  阶段A: 解析左侧大分类->小分类, 逐个打开小分类榜页, 分页收集全部歌曲列表
         (eid/歌名/歌手/时长/播放页地址), 关联大分类/榜名存本地 rank_songs.json
         (断点续跑, 进度存 rank_progress.json; 已收集的榜跳过)
  阶段B: 读取 rank_songs.json, 逐首歌打开播放页捕获 songinfo(wwwapi.kugou.com/play/songinfo):
         - 从 songinfo 取 audio_id 查 music 表: 已存在 -> 跳过
         - 不存在 -> 下载mp3/封面到本地 -> 拼接 /static/music/... -> insert_music 入库 [与原版相同]
         - 获取失败的歌曲记入 rank_failed_songs.json(仅记录, 下次重新获取)
         已打标志(downloaded=true)的歌曲重跑时直接跳过

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
    BASE,
    BASE_URL,
    COOKIE_FILE,
    IMAGE_DIR,
    MUSIC_DIR,
    UA,
    KuGouSpider,
)

SCRIPT_DIR = Path(__file__).resolve().parent
RANK_HOME_URL = 'https://www.kugou.com/yy/rank/home/1-6666.html?from=rank'   # 榜单首页(酷狗飙升榜)
SONGS_DATA_FILE = SCRIPT_DIR / 'rank_songs.json'           # 阶段A收集的榜+歌曲列表(含下载标志)
COLLECT_PROGRESS_FILE = SCRIPT_DIR / 'rank_progress.json'  # 阶段A断点续跑状态
FAILED_SONGS_FILE = SCRIPT_DIR / 'rank_failed_songs.json'  # 阶段B获取失败歌曲记录(仅记录, 下次重新获取)


class KuGouRankSpider(KuGouSpider):
    def __init__(self, max_ranks=0, max_songs=0, category_filter=None, rank_filter=None,
                 headless=False, clear_cache=None, **kwargs):
        super().__init__(max_categories=0, max_singers=0, max_songs=max_songs,
                         category_filter=category_filter, headless=headless,
                         clear_cache=clear_cache, **kwargs)
        self.max_ranks = max_ranks        # 最多处理前N个榜单, 0=全部
        self.rank_filter = rank_filter    # 只处理指定榜单名(小分类)
        self.rank_songs = self.load_songs_data()
        self.rank_failed = self.load_failed_rank_songs()

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
        default = {'current': {}, 'done': []}
        if os.path.exists(COLLECT_PROGRESS_FILE):
            try:
                p = json.load(open(COLLECT_PROGRESS_FILE, encoding='utf-8'))
                return {'current': p.get('current', {}), 'done': p.get('done', [])}
            except Exception:
                return default
        return default

    def save_collect_progress(self, progress):
        with open(COLLECT_PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def load_failed_rank_songs(self):
        if os.path.exists(FAILED_SONGS_FILE):
            try:
                return set(json.load(open(FAILED_SONGS_FILE, encoding='utf-8')))
            except Exception:
                return set()
        return set()

    def save_failed_rank_songs(self):
        with open(FAILED_SONGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(self.rank_failed), f, ensure_ascii=False, indent=2)

    # ================= 阶段A: 分类 + 歌曲列表收集 =================

    async def collect_categories(self, page):
        """解析左侧分类: 大分类(h3 a[title]) -> 小分类列表(ul a[title][href])"""
        await page.wait_for_selector('div.pc_rank_sidebar', timeout=15000)
        sidebars = page.locator('div.pc_rank_sidebar')
        categories = []
        for i in range(await sidebars.count()):
            sb = sidebars.nth(i)
            big_name = ''
            try:
                big_name = (await sb.locator('h3 a[title]').first.get_attribute('title')) or ''
            except Exception:
                pass
            links = sb.locator('ul a[title][href*="/yy/rank/home/"]')
            smalls = []
            for j in range(await links.count()):
                name = await links.nth(j).get_attribute('title')
                href = await links.nth(j).get_attribute('href')
                if name and href:
                    smalls.append({'name': name, 'url': href})
            categories.append({'big': big_name, 'smalls': smalls})
            print(f"  大分类[{i + 1}]: {big_name} -> {len(smalls)} 个小分类")
        return categories

    async def collect_rank_songs(self, page, rank):
        """打开榜页, 分页收集全部歌曲列表。返回歌曲列表 [(eid, songname, artist, duration, song_url)]"""
        rank_url = rank['url']
        m = re.search(r'/rank/home/1-(\d+)\.html', rank_url)
        rank_id = m.group(1) if m else ''
        print(f"  打开榜单: {rank['name']} ({rank_url})")

        # 打开第1页
        await page.goto(rank_url, timeout=30000, wait_until='domcontentloaded')
        await page.wait_for_timeout(2500)

        # 读取总页数(分页器按钮 id="page_last_{n}"); 若解析不到歌曲列表且弹滑块, 提示人工
        total_pages = 1
        try:
            last_btn = page.locator('[id^="page_last_"]').first
            btn_id = await last_btn.get_attribute('id')
            if btn_id:
                total_pages = int(btn_id.replace('page_last_', ''))
        except Exception:
            pass

        songs = []
        for page_no in range(1, total_pages + 1):
            if page_no > 1:
                url = f"{BASE}/yy/rank/home/{page_no}-{rank_id}.html?from=rank"
                try:
                    await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                except Exception as e:
                    print(f"    分页 {page_no} 访问失败: {e}")
                    break
                await page.wait_for_timeout(2000)

            # 解析当前页歌曲
            page_songs = await self.parse_rank_songlist(page)
            if not page_songs:
                if await self.has_captcha(page):
                    print(f"    !! 榜页弹出滑块验证码, 请在浏览器中拖动滑块完成拼图 (最多等待180秒)...")
                    resolved = False
                    for _ in range(36):
                        await page.wait_for_timeout(5000)
                        page_songs = await self.parse_rank_songlist(page)
                        if page_songs:
                            resolved = True
                            break
                    if not resolved:
                        print(f"    人工验证超时, 本榜留待下次续跑: {rank['name']}")
                        break
                else:
                    print(f"    第 {page_no} 页无歌曲数据, 停止")
                    break
            print(f"    第 {page_no}/{total_pages} 页: {len(page_songs)} 首")
            songs.extend(page_songs)

        # 去重(按 eid)保序
        seen = set()
        uniq = []
        for s in songs:
            if s['eid'] and s['eid'] in seen:
                continue
            seen.add(s['eid'])
            uniq.append(s)
        return uniq

    async def parse_rank_songlist(self, page):
        """解析 div.pc_temp_songlist li[data-eid] 歌曲列表
        (用 page.evaluate 而非 locator.evaluate_all: playwright 1.61 下 evaluate_all 有 bug)"""
        try:
            return await page.evaluate(
                """() => [...document.querySelectorAll('div.pc_temp_songlist li[data-eid]')].map(li => {
                    const a = li.querySelector('a.pc_temp_songname');
                    const t = li.querySelector('.pc_temp_time');
                    const title = a ? (a.getAttribute('title') || '') : '';
                    const parts = title.split(' - ');
                    const artist = parts.length > 1 ? parts[0].trim() : '';
                    const songname = parts.length > 1 ? parts.slice(1).join(' - ').trim() : title;
                    return {
                        eid: li.getAttribute('data-eid'),
                        songname: songname,
                        artist: artist,
                        duration: t ? t.textContent.trim() : '',
                        song_url: a ? a.href : '',
                    };
                })""")
        except Exception:
            return []

    async def stage_a(self, page):
        """解析分类, 逐个榜收集歌曲列表到 rank_songs.json"""
        print(f"正在打开榜单首页: {RANK_HOME_URL}")
        await page.goto(RANK_HOME_URL, timeout=30000, wait_until='domcontentloaded')
        await page.wait_for_timeout(4000)

        print("解析左侧分类...")
        categories = await self.collect_categories(page)
        if not categories:
            print("!! 未解析到左侧分类, 请检查页面是否被滑块验证码拦截")
            return

        progress = self.load_collect_progress()
        done = set(progress.get('done', []))
        rank_songs = self.load_songs_data()
        existing_ranks = {item['rank_name'] for item in rank_songs}

        # 展平: (大分类, 小分类)
        flat = []
        for cat in categories:
            for small in cat['smalls']:
                flat.append({'big': cat['big'], 'rank': small})

        total = len(flat)
        processed = 0
        for idx, item in enumerate(flat):
            big_name, rank = item['big'], item['rank']
            if self.category_filter and big_name != self.category_filter:
                continue
            if self.rank_filter and rank['name'] != self.rank_filter:
                continue
            if rank['name'] in done or rank['name'] in existing_ranks:
                continue
            if self.max_ranks > 0 and processed >= self.max_ranks:
                break
            processed += 1

            progress['current'] = {'big': big_name, 'rank': rank['name']}
            self.save_collect_progress(progress)

            print(f"\n[{idx + 1}/{total}] 大分类: {big_name} | 榜单: {rank['name']}")
            songs = await self.collect_rank_songs(page, rank)
            if not songs:
                print(f"  榜单 {rank['name']} 未收集到歌曲(可能验证码超时), 留待下次续跑")
                progress['current'] = {}
                self.save_collect_progress(progress)
                continue

            if self.max_songs > 0:
                songs = songs[:self.max_songs]
            rank_songs.append({
                'big_category': big_name,
                'rank_name': rank['name'],
                'rank_url': rank['url'],
                'songs': songs,
            })
            print(f"  榜单 {rank['name']} 共收集 {len(songs)} 首歌曲")
            done.add(rank['name'])
            progress['done'] = sorted(done)
            progress['current'] = {}
            self.save_collect_progress(progress)
            self.save_songs_data(rank_songs)
            await page.wait_for_timeout(random.randint(1000, 2000))

        self.rank_songs = rank_songs
        print(f"\n阶段A完成: 共收集 {len(rank_songs)} 个榜单的歌曲列表, 已保存到 {SONGS_DATA_FILE}")

    # ================= 阶段B: 查库入库 =================

    async def process_rank_song(self, song_page, song, rank_name, big_category):
        """单首榜歌: 打开播放页捕获 songinfo -> 按 audio_id 查库 -> 不存在则下载mp3/封面 -> 入库。
        返回 (downloaded, status): exists/saved/failed/no_url/no_audio_id"""
        song_url = song.get('song_url')
        if not song_url:
            return False, 'no_url'

        # 打开歌曲播放页, 捕获 songinfo 接口 (与原版相同)
        info = await self.capture_song_info(song_page, song_url)
        # 已打开播放页: 无论是否获取到播放地址, 都睡眠10秒再处理下一首(与原版相同, 防IP封禁)
        await song_page.wait_for_timeout(10000)
        if not info:
            print(f"  获取 songinfo 失败: {song.get('songname')} ({song_url})")
            self.rank_failed.add(song_url)
            self.save_failed_rank_songs()
            return False, 'failed'

        audio_id = info.get('audio_id')
        if audio_id is None:
            print(f"  songinfo 无 audio_id, 跳过: {song.get('songname')}")
            return False, 'no_audio_id'

        # 按 audio_id 查库, 已存在直接跳过(与原版 music_exists 逻辑相同)
        if self.music_exists(audio_id):
            return True, 'exists'

        # 下载音乐(与原版相同)
        play_url = info.get('play_url') or info.get('play_backup_url')
        local_play_url = ''
        if play_url:
            fname = os.path.basename(urlsplit(play_url).path)
            if await self.download_file(play_url, os.path.join(MUSIC_DIR, fname)):
                local_play_url = f'/static/music/kugou/{fname}'

        # 下载封面(与原版相同)
        cover = ''
        img_url = info.get('img')
        if img_url:
            fname = os.path.basename(urlsplit(img_url).path)
            if await self.download_file(img_url, os.path.join(IMAGE_DIR, fname)):
                cover = f'/static/music/images/{fname}'

        # 构造与原版 songsdata 兼容的 song 字段(榜单无 songsdata, 从 songinfo 取)
        song_data = {
            'publish_date': info.get('publish_date'),
            'version': info.get('version'),
        }
        # 插入歌曲(内部按audio_id去重, 与原版相同)
        inserted = self.insert_music(info, song_data, song.get('artist') or '',
                                     song.get('artist') or '', local_play_url, cover, song_url)
        if inserted or self.music_exists(audio_id):
            print(f"  入库成功: {song.get('songname')} (audio_id={audio_id})")
            return True, 'saved'
        print(f"  入库失败: {song.get('songname')}")
        return False, 'failed'

    async def stage_b(self, song_page):
        """读取 rank_songs.json, 逐首歌捕获 songinfo -> 查库 -> 下载入库, 输出汇总"""
        rank_songs = self.rank_songs if self.rank_songs else self.load_songs_data()
        if not rank_songs:
            print("!! rank_songs.json 为空(阶段A未收集到歌曲), 跳过阶段B")
            return
        self.rank_songs = rank_songs

        total = sum(len(item['songs']) for item in rank_songs)
        print(f"阶段B: 共 {len(rank_songs)} 个榜单, {total} 首歌曲, 开始捕获 songinfo 并入库...")
        stats = {'exists': 0, 'saved': 0, 'failed': 0, 'no_url': 0, 'no_audio_id': 0, 'skipped': 0}
        processed = 0

        for item in rank_songs:
            rank_name = item['rank_name']
            big_category = item['big_category']
            changed = False
            for song in item['songs']:
                processed += 1
                # 已打过下载标志(已入库)的歌曲直接跳过, 断点续跑
                if song.get('downloaded'):
                    stats['skipped'] += 1
                    continue

                print(f"\n[{processed}/{total}] {big_category}/{rank_name}: "
                      f"{song.get('songname')} - {song.get('artist')} (eid={song.get('eid')})")
                downloaded, status = await self.process_rank_song(
                    song_page, song, rank_name, big_category)
                song['downloaded'] = downloaded
                song['status'] = status
                stats[status] = stats.get(status, 0) + 1
                changed = True

            if changed:
                self.save_songs_data(rank_songs)
            print(f"  榜单 {rank_name} 处理完成")

        self.save_songs_data(rank_songs)
        failed = sum(1 for item in rank_songs for s in item['songs'] if not s.get('downloaded'))
        print(f"\n阶段B完成: 已在库 {stats['exists']} / 本次入库 {stats['saved']} / "
              f"获取失败 {stats['failed']} / 无地址 {stats['no_url']} / 无audio_id {stats['no_audio_id']} / "
              f"已标记跳过 {stats['skipped']}")
        print(f"未入库歌曲共 {failed} 首; 获取失败记录: {FAILED_SONGS_FILE} (仅记录, 下次重新获取)")

    # ================= 主流程 =================

    async def run(self):
        async with async_playwright() as p:
            has_cookie = os.path.exists(COOKIE_FILE)

            # 启动交互(在main中完成), 浏览器模式决策与原版相同
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
                print("--headless 已指定, 使用无头浏览器")
            else:
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

            # 登录检测与原版相同
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

            # ---------- 阶段A: 收集榜单分类 + 歌曲列表(存本地 json) ----------
            await self.stage_a(page)

            # ---------- 阶段B: 捕获 songinfo + 查库 + 下载入库 ----------
            await self.stage_b(song_page)

            print(f"\n全部处理完成! 歌曲列表: {SONGS_DATA_FILE}  失败记录: {FAILED_SONGS_FILE}")
            await browser.close()


async def main():
    parser = argparse.ArgumentParser(description='酷狗音乐 排行榜爬虫')
    parser.add_argument('--max-ranks', type=int, default=0, help='最多处理前N个榜单, 0=全部')
    parser.add_argument('--max-songs', type=int, default=0, help='每个榜单最多处理N首歌曲, 0=全部')
    parser.add_argument('--category', default=None, help='只处理指定大分类(如: 热门榜单/特色音乐榜/全球榜)')
    parser.add_argument('--rank', default=None, help='只处理指定榜单名(小分类, 如: 酷狗飙升榜)')
    parser.add_argument('--headless', action='store_true',
                        help='跳过缓存询问, 强制无头模式(不建议): 无法人工完成滑块验证码, 弹出验证码的榜会被跳过')
    args = parser.parse_args()

    # 启动交互与原版相同: 是否清除缓存 (默认1=清除缓存, 清除后用有头浏览器重新扫码登录)
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

    spider = KuGouRankSpider(
        max_ranks=args.max_ranks,
        max_songs=args.max_songs,
        category_filter=args.category,
        rank_filter=args.rank,
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
