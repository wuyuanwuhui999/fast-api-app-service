import os
import re
import fnmatch
from pathlib import Path


def generate_directory_tree(root_dir, exclude_dirs=None, exclude_files=None, max_depth=None):
    """
    生成目录树形结构，支持排除文件和文件夹

    :param root_dir: 根目录路径
    :param exclude_dirs: 要排除的目录列表（支持通配符，如['*.git', 'temp*']）
    :param exclude_files: 要排除的文件列表（支持通配符，如['*.log', '*.tmp']）
    :param max_depth: 最大遍历深度（None表示不限制）
    :return: 树状结构字符串
    """
    if exclude_dirs is None:
        exclude_dirs = []
    if exclude_files is None:
        exclude_files = []

    # 转换为正则表达式模式
    def compile_patterns(patterns):
        return [re.compile(fnmatch.translate(p)) for p in patterns]

    exclude_dir_patterns = compile_patterns(exclude_dirs)
    exclude_file_patterns = compile_patterns(exclude_files)

    tree = []

    def _build_tree(current_dir, prefix='', depth=0):
        if max_depth is not None and depth > max_depth:
            return

        # 获取当前目录下的所有文件和子目录
        try:
            entries = sorted(os.listdir(current_dir))
        except (PermissionError, FileNotFoundError):
            return

        dirs = []
        files = []
        for entry in entries:
            full_path = os.path.join(current_dir, entry)
            if os.path.isdir(full_path):
                # 检查是否需要排除该目录
                if any(p.search(entry) for p in exclude_dir_patterns) or \
                        any(os.path.normpath(full_path).startswith(os.path.normpath(p)) for p in exclude_dirs):
                    continue
                dirs.append(entry)
            else:
                # 检查是否需要排除该文件
                if any(p.search(entry) for p in exclude_file_patterns):
                    continue
                files.append(entry)

        # 添加当前目录到树中
        if depth == 0:
            tree.append(f"{os.path.basename(current_dir)}/")
        else:
            tree.append(f"{prefix}├── {os.path.basename(current_dir)}/")

        # 递归处理子目录
        for i, dir_name in enumerate(dirs):
            is_last = (i == len(dirs) - 1) and (len(files) == 0)
            new_prefix = prefix + ('    ' if is_last else '│   ')
            _build_tree(os.path.join(current_dir, dir_name), new_prefix, depth + 1)

        # 添加文件到树中
        for i, file_name in enumerate(files):
            is_last = (i == len(files) - 1)
            new_prefix = prefix + ('    ' if is_last else '│   ')
            tree.append(f"{new_prefix}└── {file_name}")

    _build_tree(root_dir)
    return '\n'.join(tree)


if __name__ == "__main__":
    tree = generate_directory_tree(
        "F:/python/fast-api-app-service",
        exclude_dirs=["env","__pycache__",".idea",".git"],
        exclude_files=["read_file.py","read_tree.py",".gitignore","README.md","一键启动项目.bat","一键提交到gitee.bat","一键提交到github.bat"]
    )

    print(tree)
