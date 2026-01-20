import re
import os
from tqdm import tqdm


def split_sql_file(input_file, output_dir='output'):
    """
    分割超大SQL文件为按表名命名的多个小文件

    Args:
        input_file (str): 输入的SQL文件路径
        output_dir (str): 输出目录
    """

    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 正则表达式匹配表名
    table_pattern = re.compile(r'CREATE TABLE (?:IF NOT EXISTS )?`?(\w+)`?', re.IGNORECASE)
    insert_pattern = re.compile(r'INSERT INTO `?(\w+)`?', re.IGNORECASE)

    current_table = None
    current_file = None
    buffer = []

    # 用于跟踪已处理的表
    processed_tables = {}

    try:
        # 使用进度条显示处理进度
        file_size = os.path.getsize(input_file)
        progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc="处理SQL文件")

        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                progress_bar.update(len(line.encode('utf-8')))

                # 检查是否是CREATE TABLE语句
                create_match = table_pattern.search(line)
                if create_match:
                    # 如果之前有打开的文件，先保存
                    if current_file:
                        current_file.writelines(buffer)
                        current_file.close()
                        buffer = []

                    table_name = create_match.group(1)
                    current_table = table_name

                    # 创建新文件
                    output_file = os.path.join(output_dir, f"{table_name}.sql")

                    # 如果表已经存在，使用追加模式，否则创建新文件
                    if table_name in processed_tables:
                        current_file = open(output_file, 'a', encoding='utf-8')
                    else:
                        current_file = open(output_file, 'w', encoding='utf-8')
                        processed_tables[table_name] = True

                # 检查是否是INSERT语句
                insert_match = insert_pattern.search(line)
                if insert_match:
                    table_name = insert_match.group(1)

                    # 如果INSERT的表与当前处理的表不同，需要切换文件
                    if table_name != current_table:
                        # 如果之前有打开的文件，先保存
                        if current_file:
                            current_file.writelines(buffer)
                            current_file.close()
                            buffer = []

                        current_table = table_name
                        output_file = os.path.join(output_dir, f"{table_name}.sql")

                        # 如果表已经存在，使用追加模式，否则创建新文件
                        if table_name in processed_tables:
                            current_file = open(output_file, 'a', encoding='utf-8')
                        else:
                            current_file = open(output_file, 'w', encoding='utf-8')
                            processed_tables[table_name] = True

                # 将行添加到缓冲区
                buffer.append(line)

                # 定期写入文件以避免内存占用过高
                if len(buffer) >= 1000 and current_file:
                    current_file.writelines(buffer)
                    buffer = []

            # 写入剩余的缓冲区内容
            if current_file and buffer:
                current_file.writelines(buffer)

        progress_bar.close()

    except Exception as e:
        print(f"处理文件时出错: {e}")
    finally:
        # 确保文件被关闭
        if current_file:
            current_file.close()


def split_sql_file_advanced(input_file, output_dir='output', chunk_size=10000):
    """
    高级版本：更精确地处理SQL语句

    Args:
        input_file (str): 输入的SQL文件路径
        output_dir (str): 输出目录
        chunk_size (int): 缓冲区大小
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 更精确的正则表达式
    patterns = {
        'create_table': re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?', re.IGNORECASE),
        'insert_into': re.compile(r'INSERT\s+INTO\s+[`"]?(\w+)[`"]?', re.IGNORECASE),
        'drop_table': re.compile(r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?[`"]?(\w+)[`"]?', re.IGNORECASE)
    }

    current_table = None
    current_file = None
    file_handles = {}

    try:
        file_size = os.path.getsize(input_file)
        progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc="处理SQL文件")

        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                progress_bar.update(len(line.encode('utf-8')))

                # 检查各种SQL语句类型
                matched = False
                for stmt_type, pattern in patterns.items():
                    match = pattern.search(line)
                    if match:
                        table_name = match.group(1)
                        matched = True

                        # 获取或创建文件句柄
                        if table_name not in file_handles:
                            output_file = os.path.join(output_dir, f"{table_name}.sql")
                            file_handles[table_name] = open(output_file, 'w', encoding='utf-8')

                        # 写入到对应的文件
                        file_handles[table_name].write(line)
                        break

                # 如果没有匹配到表名，但当前有活跃的表，写入到当前表文件
                if not matched and current_table and current_table in file_handles:
                    file_handles[current_table].write(line)

        progress_bar.close()

    except Exception as e:
        print(f"处理文件时出错: {e}")
    finally:
        # 关闭所有文件句柄
        for fh in file_handles.values():
            fh.close()


def analyze_sql_file(input_file, sample_size=10):
    """
    分析SQL文件结构，帮助了解文件格式

    Args:
        input_file (str): SQL文件路径
        sample_size (int): 采样行数
    """
    print("分析SQL文件结构...")

    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= sample_size:
                    break
                lines.append(line.strip())

            print("文件前{}行样本:".format(sample_size))
            for i, line in enumerate(lines):
                print(f"{i + 1}: {line}")

    except Exception as e:
        print(f"分析文件时出错: {e}")


if __name__ == "__main__":
    input_sql_file = "F:\\sql\\play.sql"  # 替换为你的SQL文件路径
    output_dir = "F:\\sql\\sql_file"  # 替换为你的SQL文件路径
    # 先分析文件结构
    analyze_sql_file(input_sql_file,output_dir)

    print("\n开始分割SQL文件...")

    # 使用基础版本
    split_sql_file(input_sql_file, "split_tables")

    # 或者使用高级版本（如果需要更精确的处理）
    # split_sql_file_advanced(input_sql_file, "split_tables_advanced")

    print("文件分割完成！")