import cairosvg
from PIL import Image


def convert_svg_to_png(svg_path, png_path):
    # 使用cairosvg将svg转换为png
    cairosvg.svg2png(url=svg_path, write_to=png_path)

    print(f"转换完成: {png_path}")


# 示例：将'sample.svg'转换为'sample.png'
svg_file = 'F:/android/icon_email.svg'
png_file = 'F:/android/icon_email.png'

convert_svg_to_png(svg_file, png_file)

# 如果你想检查生成的PNG文件，可以加载并显示它
img = Image.open(png_file)
img.show()  # 这行代码将会在默认的图片查看器中打开转换后的PNG图片