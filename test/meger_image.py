import os
from PIL import Image, ImageDraw
import math


def create_image_collage(folder_path, output_path, columns=4, margin=10, corner_radius=10, background_color='#CCCCCC'):
    """
    将指定文件夹下的所有图片拼接成一张大图

    参数:
    folder_path: 图片文件夹路径
    output_path: 输出图片路径
    columns: 列数，默认为4
    margin: 图片之间的边距，默认为10像素
    corner_radius: 圆角半径，默认为10像素
    background_color: 背景颜色，默认为灰色 '#CCCCCC'
    """

    # 支持的图片格式
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')

    # 获取文件夹中所有图片文件
    image_files = []
    for file in os.listdir(folder_path):
        if file.lower().endswith(supported_formats):
            image_files.append(os.path.join(folder_path, file))

    if not image_files:
        print("未找到图片文件")
        return

    # 按文件名排序
    image_files.sort()

    print(f"找到 {len(image_files)} 张图片")

    # 计算行数
    rows = math.ceil(len(image_files) / columns)

    # 打开第一张图片获取尺寸（假设所有图片尺寸相同）
    first_image = Image.open(image_files[0])
    img_width, img_height = first_image.size

    # 计算每个小图在画布上的尺寸（包含边距）
    cell_width = img_width + 2 * margin
    cell_height = img_height + 2 * margin

    # 计算大图尺寸
    collage_width = columns * cell_width
    collage_height = rows * cell_height

    # 创建大图画布
    collage = Image.new('RGB', (collage_width, collage_height), background_color)

    # 创建圆角矩形蒙版
    def create_rounded_rectangle_mask(size, radius):
        """创建圆角矩形蒙版"""
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)

        # 绘制圆角矩形
        draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)

        return mask

    # 处理每张图片
    for index, image_path in enumerate(image_files):
        try:
            # 打开图片
            img = Image.open(image_path).convert('RGB')

            # 调整图片尺寸（如果需要统一尺寸）
            if img.size != (img_width, img_height):
                img = img.resize((img_width, img_height), Image.Resampling.LANCZOS)

            # 创建带透明背景的新图片
            cell_img = Image.new('RGBA', (cell_width, cell_height), (0, 0, 0, 0))

            # 计算图片在cell中的位置（居中）
            x_offset = (cell_width - img_width) // 2
            y_offset = (cell_height - img_height) // 2

            # 创建圆角蒙版
            mask = create_rounded_rectangle_mask((img_width, img_height), corner_radius)

            # 将原图转换为RGBA以便应用蒙版
            img_rgba = img.convert('RGBA')

            # 应用圆角蒙版
            img_with_rounded_corners = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            img_with_rounded_corners.paste(img_rgba, (0, 0), mask)

            # 将圆角图片粘贴到cell中
            cell_img.paste(img_with_rounded_corners, (x_offset, y_offset), img_with_rounded_corners)

            # 计算在大图中的位置
            row = index // columns
            col = index % columns

            x_pos = col * cell_width
            y_pos = row * cell_height

            # 将cell粘贴到大图上
            collage.paste(cell_img, (x_pos, y_pos), cell_img)

            print(f"已处理图片 {index + 1}/{len(image_files)}: {os.path.basename(image_path)}")

        except Exception as e:
            print(f"处理图片 {image_path} 时出错: {e}")
            continue

    # 保存大图
    collage.save(output_path, 'PNG')
    print(f"拼接完成！大图已保存至: {output_path}")

    return collage


# 使用示例
if __name__ == "__main__":
    # 指定图片文件夹路径和输出路径
    input_folder = "F:/uniapp/新建文件夹"  # 请替换为您的图片文件夹路径
    output_file = "collage_result.png"  # 输出文件名

    # 创建图片拼接
    result = create_image_collage(
        folder_path=input_folder,
        output_path=output_file,
        columns=4,  # 4列
        margin=10,  # 10像素边距
        corner_radius=10,  # 10像素圆角
        background_color='#CCCCCC'  # 灰色背景
    )

    # 如果需要显示图片（可选）
    if result:
        result.show()