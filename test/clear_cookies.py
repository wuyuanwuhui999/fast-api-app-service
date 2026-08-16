# -*- coding: utf-8 -*-
"""清除酷狗音乐爬虫的 cookie 缓存 (kugou_cookies.json)

运行方式:  python clear_cookies.py

删除后下次运行 kugou_music_spider.py 时, 会检测到未登录状态,
自动弹出登录二维码, 手动扫码后自动生成新的 cookie 缓存。
"""
import os

# 与爬虫脚本同目录下的 cookie 缓存文件
COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kugou_cookies.json')


def main():
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)
        print(f"已删除 cookie 缓存: {COOKIE_FILE}")
        print("下次运行 kugou_music_spider.py 时会重新弹出登录二维码, 扫码登录后自动生成新的 cookie 缓存")
    else:
        print(f"未找到 cookie 缓存文件: {COOKIE_FILE}")
        print("无需清除, 爬虫下次运行时会直接弹出登录二维码")


if __name__ == '__main__':
    main()
