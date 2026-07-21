# test_music_like.py
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


def test_insert_music_like():
    """
    测试添加音乐红心收藏
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

    # ==================== 1. 检查收藏状态 ====================
    print("\n" + "=" * 60)
    print(f"步骤1：检查音乐收藏状态 (musicId: {music_id})")
    print("=" * 60)

    check_url = f"{base_url}/service/music/checkMusicLike/{music_id}"

    try:
        response = requests.get(check_url, headers=headers)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", {})
            is_liked = data.get("isLiked", False)
            print(f"当前收藏状态: {'✅ 已收藏' if is_liked else '❌ 未收藏'}")
        else:
            print(f"❌ 查询失败: {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 2. 添加收藏 ====================
    print("\n" + "=" * 60)
    print(f"步骤2：添加音乐红心收藏 (musicId: {music_id})")
    print("=" * 60)

    insert_url = f"{base_url}/service/music/insertMusicLike/{music_id}"

    print(f"\n请求URL: {insert_url}")
    print(f"请求方式: POST")

    try:
        response = requests.post(insert_url, headers=headers)
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

    # ==================== 3. 再次检查收藏状态 ====================
    print("\n" + "=" * 60)
    print(f"步骤3：再次检查收藏状态（验证添加）")
    print("=" * 60)

    try:
        response = requests.get(check_url, headers=headers)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", {})
            is_liked = data.get("isLiked", False)
            print(f"当前收藏状态: {'✅ 已收藏' if is_liked else '❌ 未收藏'}")

            if is_liked:
                print("✅ 收藏添加成功！")
            else:
                print("❌ 收藏添加失败！")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 4. 重复添加（幂等性测试） ====================
    print("\n" + "=" * 60)
    print(f"步骤4：重复添加收藏（幂等性测试）")
    print("=" * 60)

    try:
        response = requests.post(insert_url, headers=headers)
        result = response.json()

        if result.get("status") != "SUCCESS":
            print(f"✅ 重复添加被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：重复添加被允许")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 5. 取消收藏 ====================
    print("\n" + "=" * 60)
    print(f"步骤5：取消音乐红心收藏 (musicId: {music_id})")
    print("=" * 60)

    cancel_url = f"{base_url}/service/music/deleteMusicLike/{music_id}"

    try:
        response = requests.delete(cancel_url, headers=headers)
        result = response.json()

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            print(f"\n✅ {result.get('msg')}")
        else:
            print(f"\n❌ {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 6. 最终检查收藏状态 ====================
    print("\n" + "=" * 60)
    print(f"步骤6：最终检查收藏状态（验证取消）")
    print("=" * 60)

    try:
        response = requests.get(check_url, headers=headers)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", {})
            is_liked = data.get("isLiked", False)
            print(f"当前收藏状态: {'✅ 已收藏' if is_liked else '❌ 未收藏'}")

            if not is_liked:
                print("✅ 取消收藏成功！")
            else:
                print("❌ 取消收藏失败！")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


def test_music_like_flow():
    """
    测试完整的收藏/取消收藏流程（使用不同音乐）
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    music_ids = [64340, 64342, 64344]  # 多首音乐

    # ==================== 登录 ====================
    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"\n✅ 登录成功！")
    headers = {'Authorization': f'Bearer {token}'}

    # ==================== 批量收藏 ====================
    print("\n" + "=" * 60)
    print("批量收藏音乐")
    print("=" * 60)

    liked_count = 0
    for music_id in music_ids:
        insert_url = f"{base_url}/service/music/insertMusicLike/{music_id}"
        response = requests.post(insert_url, headers=headers)
        result = response.json()

        if result.get("status") == "SUCCESS":
            liked_count += 1
            print(f"  ✅ 收藏音乐 {music_id} 成功")
        else:
            print(f"  ❌ 收藏音乐 {music_id} 失败: {result.get('msg')}")

    print(f"\n共成功收藏 {liked_count} 首音乐")

    # ==================== 查询播放记录（验证点赞状态） ====================
    print("\n" + "=" * 60)
    print("查询播放记录（验证 isLike 字段）")
    print("=" * 60)

    record_url = f"{base_url}/service/music/getMusicRecord"
    params = {"pageNum": 1, "pageSize": 10}

    try:
        response = requests.get(record_url, headers=headers, params=params)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            print(f"\n📊 前5首音乐的点赞状态:")
            print("-" * 50)

            for idx, music in enumerate(data[:5], 1):
                song_name = music.get('songName', '未知歌曲')
                is_like = music.get('isLike', 0)
                status = "❤️ 已点赞" if is_like == 1 else "🤍 未点赞"
                print(f"{idx}. 《{song_name}》- {status}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 批量取消收藏 ====================
    print("\n" + "=" * 60)
    print("批量取消收藏音乐")
    print("=" * 60)

    for music_id in music_ids:
        cancel_url = f"{base_url}/service/music/deleteMusicLike/{music_id}"
        response = requests.delete(cancel_url, headers=headers)
        result = response.json()

        if result.get("status") == "SUCCESS":
            print(f"  ✅ 取消收藏音乐 {music_id} 成功")
        else:
            print(f"  ❌ 取消收藏音乐 {music_id} 失败: {result.get('msg')}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🎵 测试音乐红心收藏接口")
    print("=" * 60)
    print("\n提示：确保 music_id 在 music 表中存在")
    print()

    # 运行完整测试
    test_insert_music_like()

    print("\n" + "=" * 60)

    # 批量测试
    test_music_like_flow()

    print("\n" + "=" * 60)
    print("  ✅ 所有测试完成")
    print("=" * 60)