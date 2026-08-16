# circle/utils/circle_util.py
import base64
import io
import os
import struct
from typing import Optional, Tuple


def get_image_size(image_bytes: bytes) -> Optional[Tuple[int, int]]:
    """解析图片字节流，返回 (width, height)，失败返回 None"""
    # 优先使用 Pillow（如果可用）
    try:
        from PIL import Image
        with Image.open(io.BytesIO(image_bytes)) as img:
            return img.size
    except Exception:
        pass

    # 兜底：使用标准库解析常见格式头
    try:
        return _get_image_size_stdlib(image_bytes)
    except Exception:
        return None


def _get_image_size_stdlib(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 24:
        return None
    # PNG: 89 50 4E 47 ..., width/height 位于偏移 16/20（大端）
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    # GIF
    if data[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    # JPEG
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + length
        return None
    # BMP
    if data[:2] == b"BM":
        w = struct.unpack("<I", data[18:22])[0]
        h = struct.unpack("<I", data[22:26])[0]
        return w, h
    return None


def generate_image(base64_str: str, save_path: str, url_prefix: str = "/static/circle/") -> Optional[str]:
    """
    保存 base64 图片，返回相对 URL 路径（带尺寸后缀）

    与 Spring 的 Common.generateImage 行为对齐：
    - 解码 base64
    - 读取图片尺寸，文件名追加 _{width}x{height}
    - 返回去除盘符后的相对路径（即 URL）
    """
    if not base64_str:
        return None

    try:
        image_bytes = base64.b64decode(base64_str)
    except Exception:
        return None

    try:
        size = get_image_size(image_bytes)
    except Exception:
        size = None

    dir_name = os.path.dirname(save_path)
    base_name = os.path.basename(save_path)

    dot = base_name.rfind(".")
    if dot != -1:
        if size and size[0] and size[1]:
            new_base = f"{base_name[:dot]}_{size[0]}x{size[1]}{base_name[dot:]}"
        else:
            new_base = base_name
    else:
        new_base = base_name

    new_path = os.path.join(dir_name, new_base)

    try:
        os.makedirs(dir_name, exist_ok=True)
        with open(new_path, "wb") as f:
            f.write(image_bytes)
    except Exception:
        return None

    return url_prefix + new_base
