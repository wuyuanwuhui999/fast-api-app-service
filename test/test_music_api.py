# test_music_record.py
import requests
import hashlib
import json
from datetime import datetime, timedelta


def md5_encrypt(text):
    """对字符串进行MD5加密"""
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()


def login(base_url, user_account, password):
    """登录并返回token"""
    login_url = f"{base_url}/service/user/login"
    encrypted_password = md5_encrypt(password)

    login_data = {
        "userAccount": user_account,
        "password": encrypted_password
    }

    try:
        response = requests.post(login_url, json=login_data)
        result = response.json()

        if result.get("status") == "SUCCESS":
            return result.get("token")
        else:
            print(f"登录失败: {result.get('msg')}")
            return None
    except Exception as e:
        print(f"登录请求异常: {e}")
        return None


def safe_get_value(data, key, default='N/A'):
    """安全获取字典值，处理None"""
    value = data.get(key)
    if value is None:
        return default
    return str(value)


def safe_get_int(data, key, default=0):
    """安全获取整数值"""
    value = data.get(key)
    if value is None:
        return default
    return int(value)


def test_get_music_record():
    """
    测试获取音乐播放记录接口
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    # 时间参数（可选）
    # 获取最近30天的数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # 分页参数
    page_num = 1
    page_size = 20

    # ==================== 登录 ====================
    print("=" * 70)
    print("第一步：用户登录")
    print("=" * 70)

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"\n✅ 登录成功！")
    headers = {'Authorization': f'Bearer {token}'}

    # ==================== 测试1：带时间范围查询 ====================
    print("\n" + "=" * 70)
    print("测试1：获取播放记录（带时间范围）")
    print("=" * 70)

    # 格式化时间参数
    start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    params = {
        "startDate": start_str,
        "endDate": end_str,
        "pageNum": page_num,
        "pageSize": page_size
    }

    record_url = f"{base_url}/service/music/getMusicRecord"

    print(f"\n请求URL: {record_url}")
    print(f"请求参数:")
    print(json.dumps(params, ensure_ascii=False, indent=2))

    try:
        response = requests.get(record_url, headers=headers, params=params)
        response.raise_for_status()

        result = response.json()

        print("\n" + "=" * 70)
        print("📊 接口响应结果")
        print("=" * 70)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 播放记录总数（去重后的音乐数）: {total}")
            print(f"📊 当前返回记录数: {len(data)}")

            if data:
                print("\n" + "-" * 70)
                print("🎵 播放记录列表:")
                print("-" * 70)

                for idx, music in enumerate(data, 1):
                    # 安全获取字段
                    song_name = safe_get_value(music, 'songName', '未知歌曲')
                    author_name = safe_get_value(music, 'authorName', '未知歌手')
                    album_name = safe_get_value(music, 'albumName', '未知专辑')
                    times = safe_get_int(music, 'times', 0)
                    music_id = safe_get_value(music, 'id', 'N/A')

                    print(f"{idx}. 🎶 {song_name}")
                    print(f"   - 歌手: {author_name}")
                    print(f"   - 专辑: {album_name}")
                    print(f"   - 音乐ID: {music_id}")
                    print(f"   - 播放次数: {times} 次")
                    print("-" * 50)
            else:
                print("\n💡 当前用户暂无播放记录")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")

    # ==================== 测试2：不带时间范围查询 ====================
    print("\n" + "=" * 70)
    print("测试2：获取播放记录（不带时间范围）")
    print("=" * 70)

    params_no_time = {
        "pageNum": page_num,
        "pageSize": page_size
    }

    print(f"\n请求URL: {record_url}")
    print(f"请求参数: {params_no_time}")

    try:
        response = requests.get(record_url, headers=headers, params=params_no_time)
        response.raise_for_status()

        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 全部播放记录总数（去重后的音乐数）: {total}")
            print(f"📊 当前返回记录数: {len(data)}")

            # 显示前5首
            if data:
                print("\n🎵 前5首播放记录:")
                for idx, music in enumerate(data[:5], 1):
                    song_name = safe_get_value(music, 'songName', '未知歌曲')
                    author_name = safe_get_value(music, 'authorName', '未知歌手')
                    times = safe_get_int(music, 'times', 0)
                    print(f"  {idx}. 《{song_name}》- {author_name} (播放{times}次)")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")

    # ==================== 测试3：分页测试 ====================
    print("\n" + "=" * 70)
    print("测试3：分页测试（查看第2页）")
    print("=" * 70)

    params_page2 = {
        "pageNum": 2,
        "pageSize": 5,
        "startDate": start_str,
        "endDate": end_str
    }

    try:
        response = requests.get(record_url, headers=headers, params=params_page2)
        response.raise_for_status()

        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 第2页返回记录数: {len(data)}")
            print(f"📊 总记录数: {total}")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")

    # ==================== 测试4：无效时间范围 ====================
    print("\n" + "=" * 70)
    print("测试4：无效时间范围（开始时间 > 结束时间）")
    print("=" * 70)

    invalid_params = {
        "startDate": "2025-12-31 23:59:59",
        "endDate": "2025-01-01 00:00:00",
        "pageNum": 1,
        "pageSize": 10
    }

    try:
        response = requests.get(record_url, headers=headers, params=invalid_params)
        response.raise_for_status()

        result = response.json()
        print(f"\n响应结果: {result.get('msg')}")
        print(f"状态: {result.get('status')}")

        if result.get("status") != "SUCCESS":
            print("✅ 无效时间范围被正确拦截")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")


def test_music_record_detail():
    """
    测试获取播放记录详情（打印更详细的信息）
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    # ==================== 登录 ====================
    print("=" * 70)
    print("用户登录")
    print("=" * 70)

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"✅ 登录成功！\n")
    headers = {'Authorization': f'Bearer {token}'}

    # ==================== 获取播放记录 ====================
    print("=" * 70)
    print("获取音乐播放记录（详细版）")
    print("=" * 70)

    record_url = f"{base_url}/service/music/getMusicRecord"
    params = {
        "pageNum": 1,
        "pageSize": 50
    }

    try:
        response = requests.get(record_url, headers=headers, params=params)
        response.raise_for_status()

        result = response.json()

        print("\n" + "=" * 70)
        print("📊 播放记录详情")
        print("=" * 70)

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 统计信息:")
            print(f"  - 总记录数: {total}")
            print(f"  - 当前返回: {len(data)}")

            if data:
                # 统计播放次数分布
                times_list = [safe_get_int(m, 'times', 0) for m in data]
                max_times = max(times_list) if times_list else 0
                min_times = min(times_list) if times_list else 0
                avg_times = sum(times_list) / len(times_list) if times_list else 0

                print(f"\n📊 播放次数统计:")
                print(f"  - 最高播放次数: {max_times}")
                print(f"  - 最低播放次数: {min_times}")
                print(f"  - 平均播放次数: {avg_times:.1f}")

                print("\n🎵 完整播放列表:")
                print("-" * 70)

                for idx, music in enumerate(data, 1):
                    # 获取所有字段
                    song_name = safe_get_value(music, 'songName', '未知歌曲')
                    author_name = safe_get_value(music, 'authorName', '未知歌手')
                    album_name = safe_get_value(music, 'albumName', '未知专辑')
                    times = safe_get_int(music, 'times', 0)
                    music_id = safe_get_value(music, 'id', 'N/A')
                    cover = safe_get_value(music, 'cover', '无')
                    play_url = safe_get_value(music, 'playUrl', '无')
                    label = safe_get_value(music, 'label', '无')
                    is_hot = safe_get_value(music, 'isHot', '0')

                    print(f"{idx}. 🎶 {song_name}")
                    print(f"   - 歌手: {author_name}")
                    print(f"   - 专辑: {album_name}")
                    print(f"   - 音乐ID: {music_id}")
                    print(f"   - 播放次数: {times} 次")
                    print(f"   - 标签: {label}")
                    print(f"   - 是否热门: {'是' if is_hot == '1' else '否'}")
                    print(f"   - 封面: {cover}")
                    print(f"   - 播放地址: {play_url[:50] + '...' if len(play_url) > 50 else play_url}")
                    print("-" * 50)
            else:
                print("\n💡 当前用户暂无播放记录")
                print("提示：请先播放几首音乐，然后再测试此接口")
        else:
            print(f"❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")


def test_non_existent_user():
    """
    测试不存在的用户
    """
    print("=" * 70)
    print("测试不存在的用户")
    print("=" * 70)

    base_url = "http://localhost:4009"
    record_url = f"{base_url}/service/music/getMusicRecord"

    params = {
        "pageNum": 1,
        "pageSize": 10
    }

    # 不提供认证头
    try:
        response = requests.get(record_url, params=params)
        result = response.json()

        print(f"\n响应状态: {response.status_code}")
        print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")

        if response.status_code == 401:
            print("✅ 未认证请求被正确拦截")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  🎵 测试获取音乐播放记录接口")
    print("=" * 70)
    print("\n提示：如果用户没有播放记录，请先在music_record表中插入一些测试数据")
    print("示例SQL：")
    print("  INSERT INTO music_record (user_id, music_id, create_time) VALUES")
    print("  ('your_user_id', 1, NOW()),")
    print("  ('your_user_id', 2, NOW()),")
    print("  ('your_user_id', 1, NOW() - INTERVAL 1 DAY);")
    print()

    # 运行测试
    test_get_music_record()

    print("\n" + "=" * 70)

    # 测试详情
    test_music_record_detail()

    print("\n" + "=" * 70)

    # 测试未认证
    test_non_existent_user()

    print("\n" + "=" * 70)
    print("  ✅ 所有测试完成")
    print("=" * 70)