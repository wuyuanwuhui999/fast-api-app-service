import os


def collect_files_to_txt(source_dir, output_file, exclude_files=None, exclude_dirs=None):
    """
    读取指定目录下所有文件内容，写入到一个汇总的 txt 文件中。

    参数：
        source_dir (str): 要读取的源目录路径。
        output_file (str): 输出的汇总 txt 文件路径。
        exclude_files (list of str, optional): 要排除的文件名列表（含扩展名），例如 ["config.json"]。
        exclude_dirs (list of str, optional): 要排除的文件夹名称列表，例如 [".git", "__pycache__"]。
    """
    if exclude_files is None:
        exclude_files = []
    if exclude_dirs is None:
        exclude_dirs = []

    with open(output_file, 'w', encoding='utf-8') as out_f:
        for root, dirs, files in os.walk(source_dir):
            # 过滤掉要排除的目录（原地修改dirs会影响os.walk的行为）
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file in exclude_files:
                    continue

                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except (UnicodeDecodeError, IOError) as e:
                    # 如果无法读取（如二进制文件），跳过并可选打印警告
                    print(f"跳过文件（无法读取）: {file_path} - {e}")
                    continue

                # 只写入文件名（含后缀），不带路径
                out_f.write(f"// {file}\n")
                out_f.write(content)
                out_f.write("\n\n")  # 内容结束后空出一行


# 示例用法
if __name__ == "__main__":
    source_directory = "F:/android/andriod-jetpack-compose-chat-app/app/src/main"
    output_txt = "collected_files.txt"
    excluded_files = ["README.md", ".gitignore"]
    excluded_dirs = [".git", "__pycache__", "node_modules","res"]

    collect_files_to_txt(
        source_dir=source_directory,
        output_file=output_txt,
        exclude_files=excluded_files,
        exclude_dirs=excluded_dirs
    )
    print(f"已完成，结果保存在 {output_txt}")