# -*- coding: utf-8 -*-
"""
校验数据库中的相对地址对应的本地文件是否存在:
  - music.local_play_url     (相对路径 /static/music/kugou/xxx.mp3)
  - music.cover              (相对路径 /static/music/images/xxx.jpg)
  - music_authors.avatar     (相对路径 /static/music/images/xxx.jpg)

拼接规则: 相对路径前加 /Users/wuwenqiang/Documents
兼容: 老数据里存的完整绝对路径(/Users/...开头)直接使用; http链接/空值跳过
输出: 汇总统计 + 缺失文件清单(check_music_files_report.txt)
"""
import os
from datetime import datetime

import pymysql

DOCS_ROOT = '/Users/wuwenqiang/Documents'
REPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_music_files_report.txt')

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'wwq_2021',
    'database': 'play2',
    'charset': 'utf8mb4',
}


def resolve_full_path(path):
    """把相对地址拼接成绝对路径; 无法处理的返回 None"""
    if not path or not isinstance(path, str):
        return None
    p = path.strip()
    if not p:
        return None
    if p.startswith('/static/'):
        return DOCS_ROOT + p
    if p.startswith('/Users/'):
        return p
    return None  # http/https 链接或异常值, 跳过


def main():
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    missing = []      # (表名, id, 名称, 字段, 相对地址, 拼接后的绝对路径)
    checked = 0       # 参与校验的字段数
    exists_cnt = 0
    skipped = 0       # 空值/http链接跳过的字段数

    def check_row(table, row_id, name, field, value):
        nonlocal checked, exists_cnt, skipped
        full = resolve_full_path(value)
        if full is None:
            skipped += 1
            return
        checked += 1
        if os.path.exists(full):
            exists_cnt += 1
        else:
            missing.append((table, row_id, name, field, value, full))

    # ---- music 表: local_play_url / cover ----
    cur.execute("SELECT id, song_name, local_play_url, cover FROM music")
    rows = cur.fetchall()
    print(f"music 表共 {len(rows)} 行")
    for mid, song_name, lp, cover in rows:
        check_row('music', mid, song_name, 'local_play_url', lp)
        check_row('music', mid, song_name, 'cover', cover)

    # ---- music_authors 表: avatar ----
    cur.execute("SELECT id, author_name, avatar FROM music_authors")
    rows = cur.fetchall()
    print(f"music_authors 表共 {len(rows)} 行")
    for aid, author_name, avatar in rows:
        check_row('music_authors', aid, author_name, 'avatar', avatar)

    conn.close()

    # ---- 输出汇总 ----
    print()
    print("=" * 60)
    print(f"参与校验的字段数 : {checked}")
    print(f"文件存在         : {exists_cnt}")
    print(f"文件缺失         : {len(missing)}")
    print(f"跳过(空/http)    : {skipped}")
    print("=" * 60)

    if missing:
        # 控制台只打印前 30 条
        print(f"\n缺失清单(前30条, 完整清单见 {REPORT_FILE}):")
        for table, row_id, name, field, rel, full in missing[:30]:
            print(f"  [{table}] id={row_id} {name} | {field} -> {full}")

    # 写完整报告
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"文件校验报告 {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write(f"校验字段: {checked} | 存在: {exists_cnt} | 缺失: {len(missing)} | 跳过: {skipped}\n")
        f.write("=" * 70 + "\n")
        for table, row_id, name, field, rel, full in missing:
            f.write(f"[{table}] id={row_id} | {name} | {field} | {rel} | 绝对路径: {full}\n")
    print(f"\n完整缺失清单已写入: {REPORT_FILE}")

    return 0 if not missing else 1


if __name__ == '__main__':
    raise SystemExit(main())
