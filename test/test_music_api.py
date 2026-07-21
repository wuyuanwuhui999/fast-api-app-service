# test_insert_music_record.py
import requests
import hashlib
import json


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


def test_insert_music_record():
    """
    测试添加音乐播放记录
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    music_id = 64340  # 盛夏的果实

    # ==================== 登录 ====================
    print("=" * 60)
    print("第一步：用户登录")
    print("=" * 60)

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"\n✅ 登录成功！")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    # ==================== 添加播放记录 ====================
    print("\n" + "=" * 60)
    print(f"第二步：添加音乐播放记录 (musicId: {music_id})")
    print("=" * 60)

    insert_url = f"{base_url}/service/music/insertMusicRecord"

    # 测试数据1：完整参数
    payload1 = {
        "musicId": music_id,
        "platform": "Android",
        "version": "2.5.1",
        "device": "Xiaomi11"
    }

    print(f"\n请求URL: {insert_url}")
    print(f"请求方式: POST")
    print(f"请求体:")
    print(json.dumps(payload1, ensure_ascii=False, indent=2))

    try:
        response = requests.post(insert_url, headers=headers, json=payload1)
        response.raise_for_status()

        result = response.json()

        print("\n" + "=" * 60)
        print("📊 接口响应结果")
        print("=" * 60)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            record_id = result.get("data")
            print(f"\n✅ {result.get('msg')}")
            print(f"📝 新增记录ID: {record_id}")
        else:
            print(f"\n❌ {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")

    # ==================== 测试2：不同参数 ====================
    print("\n" + "=" * 60)
    print("测试2：添加播放记录（仅必填参数）")
    print("=" * 60)

    payload2 = {
        "musicId": 64342  # 分飞
    }

    try:
        response = requests.post(insert_url, headers=headers, json=payload2)
        result = response.json()

        if result.get("status") == "SUCCESS":
            print(f"✅ 添加成功，记录ID: {result.get('data')}")
        else:
            print(f"❌ {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 测试3：不存在的音乐 ====================
    print("\n" + "=" * 60)
    print("测试3：添加不存在的音乐（错误场景）")
    print("=" * 60)

    payload3 = {
        "musicId": 99999999
    }

    try:
        response = requests.post(insert_url, headers=headers, json=payload3)
        result = response.json()

        if result.get("status") != "SUCCESS":
            print(f"✅ 错误被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：不存在的音乐被添加成功")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 测试4：未认证 ====================
    print("\n" + "=" * 60)
    print("测试4：未认证请求（错误场景）")
    print("=" * 60)

    try:
        response = requests.post(insert_url, json=payload1)
        result = response.json()

        if response.status_code == 401:
            print(f"✅ 未认证请求被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：未认证请求未被拦截")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 测试5：验证插入成功（查询播放记录） ====================
    print("\n" + "=" * 60)
    print("测试5：验证插入成功（查询最新播放记录）")
    print("=" * 60)

    record_url = f"{base_url}/service/music/getMusicRecord"
    params = {
        "pageNum": 1,
        "pageSize": 5
    }

    try:
        response = requests.get(record_url, headers=headers, params=params)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            if data:
                print(f"\n📊 最新5条播放记录:")
                print("-" * 50)
                for idx, music in enumerate(data[:5], 1):
                    song_name = music.get('songName', '未知歌曲')
                    author_name = music.get('authorName', '未知歌手')
                    times = music.get('times', 0)
                    print(f"{idx}. 《{song_name}》- {author_name} (播放{times}次)")
        else:
            print(f"❌ 查询失败: {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🎵 测试添加音乐播放记录接口")
    print("=" * 60)
    print("\n提示：确保 music_id 在 music 表中存在")
    print()

    test_insert_music_record()

    print("\n" + "=" * 60)
    print("  ✅ 测试完成")
    print("=" * 60)