import os
from pathlib import Path


def save_files_content_to_txt(directory, extensions, exclude_files=None, output_filename="file_contents.txt"):
    """
    读取指定目录下的文件（支持多个文件格式），排除指定文件名，并将文件路径和内容保存到桌面上的txt文件中

    :param directory: 要搜索的目录路径
    :param extensions: 要包含的文件扩展名列表，如 ['.txt', '.py']
    :param exclude_files: 要排除的文件名列表（不包含路径），如 ['test.txt', 'temp.py']
    :param output_filename: 输出的txt文件名
    """
    # 获取Windows桌面路径
    desktop_path = Path.home() / "Desktop"
    output_path = desktop_path / output_filename

    # 确保扩展名以点开头且小写
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]

    # 如果exclude_files为None，初始化为空列表
    if exclude_files is None:
        exclude_files = []

    # 收集所有匹配的文件
    matched_files = []
    for root, dirs, files in os.walk(directory):
        # 从遍历中移除要排除的文件夹
        dirs[:] = [d for d in dirs if d not in exclude_files]

        for file in files:
            # 检查文件扩展名是否匹配且文件名不在排除列表中
            if (file.lower().endswith(ext) for ext in extensions) and (file not in exclude_files):
                file_path = os.path.join(root, file).replace('\\', '/')
                matched_files.append(file_path)

    # 将文件内容和路径写入输出文件
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for file_path in matched_files:
            try:
                # 写入文件路径
                outfile.write(f"文件路径: {file_path}\n")

                # 写入文件内容
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    outfile.write(f"文件内容:\n{content}\n")

                # 写入两个换行符作为分隔
                outfile.write("\n\n")

            except Exception as e:
                outfile.write(f"处理文件 {file_path} 时出错: {str(e)}\n\n\n")

    print(f"处理完成！结果已保存到: {output_path}")


# 使用示例
if __name__ == "__main__":

    # # 调用函数
    save_files_content_to_txt(
        directory= "F:/java/springboot3-user-service/ai",
        extensions=[".java",".pom",".xml"],
        exclude_files=["AiApplicationTests.java"],
        output_filename="springboot ai模块代码.txt"
    )

    # 调用函数
    save_files_content_to_txt(
        directory="F:/python/fast-api-user-service",
        extensions=[".py"],
        exclude_files=["env",".gitignore",".env","README.md","read_file.py"],
        output_filename="fast-api代码.txt"
    )