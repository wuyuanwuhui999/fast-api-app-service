import os


def collect_files_to_txt(source_dir, output_file, exclude_files=None, exclude_dirs=None, exclude_extensions=None):
    """
    读取指定目录下所有文件内容，写入到一个汇总的 txt 文件中。

    参数：
        source_dir (str): 要读取的源目录路径。
        output_file (str): 输出的汇总 txt 文件路径。
        exclude_files (list of str, optional): 要排除的文件名列表（含扩展名），例如 ["config.json"]。
        exclude_dirs (list of str, optional): 要排除的文件夹名称列表，例如 [".git", "__pycache__"]。
        exclude_extensions (list of str, optional): 要排除的文件扩展名列表，例如 [".png", ".jpg"]。
    """
    if exclude_files is None:
        exclude_files = []
    if exclude_dirs is None:
        exclude_dirs = []
    if exclude_extensions is None:
        exclude_extensions = []

    # 获取源目录的绝对路径，用于计算相对路径
    source_dir_abs = os.path.abspath(source_dir)
    # 获取源目录的父目录名，用于在路径中显示
    source_dir_name = os.path.basename(source_dir_abs)

    with open(output_file, 'w', encoding='utf-8') as out_f:
        for root, dirs, files in os.walk(source_dir):
            # 过滤掉要排除的目录（原地修改dirs会影响os.walk的行为）
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file in exclude_files:
                    continue

                # 检查文件扩展名是否在排除列表中
                file_ext = os.path.splitext(file)[1]  # 获取扩展名（包含点号）
                if file_ext in exclude_extensions:
                    continue

                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except (UnicodeDecodeError, IOError) as e:
                    # 如果无法读取（如二进制文件），跳过并可选打印警告
                    print(f"跳过文件（无法读取）: {file_path} - {e}")
                    continue

                # 计算相对于源目录的路径
                file_path_abs = os.path.abspath(file_path)
                relative_path = os.path.relpath(file_path_abs, source_dir_abs)

                # 写入完整的相对路径，格式为: // 源目录名/相对路径
                out_f.write(f"// {source_dir_name}/{relative_path}\n")
                out_f.write(content)
                out_f.write("\n\n")  # 内容结束后空出一行


# 示例用法
if __name__ == "__main__":
    # 示例1：过滤图片文件
    source_directory = "/Users/wuwenqiang/Documents/code/c++/qt-chat-desktop"
    output_txt = "qt项目源代码.txt"
    excluded_files = [".gitignore"]
    excluded_dirs = [".git", 'docs', "__pycache__", "node_modules", "res", '.qtcreator', 'build']
    excluded_extensions = ['.md','.bat','.pptx',".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",'.txt','.lock']  # 过滤图片文件

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs,
        exclude_extensions=excluded_extensions
    )
    print(f"已完成，结果保存在 {output_txt}")

    # 示例2：springboot项目
    source_directory = "/Users/wuwenqiang/Documents/code/java/springboot3-app-service/"
    output_txt = "springboot源代码.txt"
    excluded_files = [".gitignore",".DS_Store", ".gitattributes", ".gitignore", "mvnw", "mvnw.cmd"]
    excluded_dirs = ["agent", 'docs', "chat", "company", "prompt", "tenant", "user", "music", "movie", ".git",
                     "__pycache__", "node_modules", "res", '.qtcreator', 'build', "chat.xcodeproj", ".mvn", "test",
                     "target", ".idea"]
    excluded_extensions = ['.sh','.md','.sql','.bat','.pptx',".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",'.txt','.lock','.ttf','.sqlite3','.properties','.DS_Store']  # 过滤图片文件

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs,
        exclude_extensions=excluded_extensions
    )
    print(f"已完成，结果保存在 {output_txt}")

    # 示例3：swift项目
    source_directory = "/Users/wuwenqiang/Documents/code/swiftUI/swift-chat-app/chat"
    output_txt = "swift源代码.txt"
    excluded_files = [".gitignore",".DS_Store"]
    excluded_dirs = [".git", 'docs', "__pycache__", "node_modules", "res", '.qtcreator', 'build', "chat.xcodeproj"]
    excluded_extensions = ['.sh','.md','.sql','.bat','.pptx',".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",'.txt','.lock','.ttf','.sqlite3','.properties','.DS_Store']  # 过滤图片文件

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs,
        exclude_extensions=excluded_extensions
    )
    print(f"已完成，结果保存在 {output_txt}")

    # 示例4：uniapp项目
    source_directory = "/Users/wuwenqiang/Documents/code/uniapp/uniapp-vite-vue3-ts-chat-app-ui/src"
    output_txt = "uniapp源代码.txt"
    excluded_files = [".gitignore",".DS_Store"]
    excluded_dirs = [".git", 'docs', "__pycache__", "node_modules", "res", '.qtcreator', 'build', "chat.xcodeproj"]
    excluded_extensions = ['.sh','.md','.sql','.bat','.pptx',".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",'.txt','.lock','.ttf','.sqlite3','.properties','.DS_Store']  # 过滤图片文件

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs,
        exclude_extensions=excluded_extensions
    )
    print(f"已完成，结果保存在 {output_txt}")

    # 示例5：jetpack compose项目
    source_directory = "/Users/wuwenqiang/Documents/code/android/andriod-jetpack-compose-chat-app/app/src/main/java/com/player/chat"
    output_txt = "jetpack compose源代码.txt"
    excluded_files =  [".gitignore"]
    excluded_dirs = [".git", 'docs', "__pycache__", "test", "node_modules", "res", '.qtcreator', 'build', ".venv",
                     ".idea"]
    excluded_extensions = ['.sh','.md','.sql','.bat','.pptx',".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",'.txt','.lock','.ttf','.sqlite3','.properties','.DS_Store']  # 过滤图片文件

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs,
        exclude_extensions=excluded_extensions
    )
    print(f"已完成，结果保存在 {output_txt}")

    # 示例6：flutter项目
    source_directory = "/Users/wuwenqiang/Documents/code/flutter/flutter-chat-app-ui/lib"
    output_txt = "flutter项目源代码.txt"
    excluded_files = [".gitignore"]
    excluded_dirs = [".git", 'docs', "__pycache__", "test", "node_modules", "res", '.qtcreator', 'build', ".venv",
                     ".idea"]
    excluded_extensions = ['.sh','.md','.sql','.bat','.pptx',".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",'.txt','.lock','.ttf','.sqlite3','.properties','.DS_Store']  # 过滤图片文件

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs,
        exclude_extensions=excluded_extensions
    )
    print(f"已完成，结果保存在 {output_txt}")

    # 示例7：harmony项目
    source_directory = "/Users/wuwenqiang/Documents/code/harmony/harmony-arkts-chat-app-ui/entry/src/main/ets"
    output_txt = "harmony arkts鸿蒙原生源代码.txt"
    excluded_files = [".gitignore"]
    excluded_dirs = [".git", 'docs', "__pycache__", "test", "node_modules", "res", '.qtcreator', 'build', ".venv",
                     ".idea"]
    excluded_extensions = ['.sh','.md','.sql','.bat','.pptx',".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",'.txt','.lock','.ttf','.sqlite3','.properties','.DS_Store']  # 过滤图片文件

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs,
        exclude_extensions=excluded_extensions
    )
    print(f"已完成，结果保存在 {output_txt}")

    # 示例8：fastapi项目
    source_directory = "/Users/wuwenqiang/Documents/code/python/fast-api-app-service"
    output_txt = "fast api多模块项目源代码.txt"
    excluded_files = [".gitignore", "__init__.py","提示词.txt"]
    excluded_dirs = [".git", 'docs', "__pycache__", "test", "node_modules", "res", '.qtcreator', 'build', ".venv",
                     ".idea", "venv"]
    excluded_extensions = ['.sh','.md','.sql','.bat','.pptx',".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",'.txt','.lock','.ttf','.sqlite3','.properties','.DS_Store']  # 过滤图片文件

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs,
        exclude_extensions=excluded_extensions
    )
    print(f"已完成，结果保存在 {output_txt}")