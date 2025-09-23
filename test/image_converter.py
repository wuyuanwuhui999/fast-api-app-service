from PIL import Image
import os


def convert_to_png(input_path, output_path=None, width=360):
    """
    将图片转换为PNG格式，并可按比例缩放

    Args:
        input_path (str): 输入图片的路径
        output_path (str, optional): 输出PNG图片的完整路径。如果为None，则在同一目录下生成
        width (int, optional): 输出图片的宽度。如果为None，则保持原始尺寸

    Returns:
        str: 输出文件的路径

    Raises:
        FileNotFoundError: 当输入文件不存在时
        ValueError: 当参数无效时
        Exception: 图片处理过程中的其他错误
    """
    # 检查输入文件是否存在
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 打开原始图片
    try:
        with Image.open(input_path) as img:
            # 转换为RGB模式（处理带有透明通道的图片）
            if img.mode in ('RGBA', 'LA'):
                # 创建一个白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                # 合并图像
                background.paste(img, mask=img.split()[-1])  # 使用alpha通道作为掩码
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 计算新尺寸（如果需要缩放）
            if width is not None:
                if width <= 0:
                    raise ValueError("宽度必须大于0")

                # 计算高度（保持宽高比）
                original_width, original_height = img.size
                ratio = width / original_width
                height = int(original_height * ratio)

                # 调整图片大小
                img = img.resize((width, height), Image.Resampling.LANCZOS)

            # 确定输出路径
            if output_path is None:
                # 在同一目录下生成，使用原文件名但改为png扩展名
                directory = os.path.dirname(input_path)
                filename = os.path.splitext(os.path.basename(input_path))[0] + '.png'
                output_path = os.path.join(directory, filename)
            else:
                # 确保输出路径以.png结尾
                if not output_path.lower().endswith('.png'):
                    output_path += '.png'

            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 保存为PNG格式
            img.save(output_path, 'PNG')

            return output_path

    except Exception as e:
        raise Exception(f"图片处理失败: {str(e)}")


# 使用示例
if __name__ == "__main__":
    try:
        result1 = convert_to_png("C:/Users/27501/Desktop/添加用户.png","F:/flutter/flutter-chat-app-ui/添加用户.png",360)
        print(f"图片已保存到: {result1}")

        result2 = convert_to_png("C:/Users/27501/Desktop/添加用户.png","F:/uniapp/uniapp-chat-app-ui/添加用户.png",360)
        print(f"图片已保存到: {result2}")

        # 示例2: 转换格式并调整宽度为800px
        result2 = convert_to_png("C:/Users/27501/Desktop/添加用户.png", "F:/Harmony/harmony-arkTs-chat-ui/添加用户.png",
                                 360)
        print(f"图片已保存到: {result2}")

    except Exception as e:
        print(f"错误: {e}")