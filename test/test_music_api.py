# test_search_music.py
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


def safe_get_value(data, key, default='N/A'):
    """安全获取字典值"""
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


def test_search_music():
    """
    测试关键词搜索音乐
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    keyword = "黄昏"  # 搜索关键词

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

    # ==================== 测试1：搜索音乐 ====================
    print("\n" + "=" * 60)
    print(f"测试1：搜索音乐 (keyword: {keyword})")
    print("=" * 60)

    search_url = f"{base_url}/service/music/searchMusic"
    params = {
        "keyword": keyword,
        "pageNum": 1,
        "pageSize": 20
    }

    print(f"\n请求URL: {search_url}")
    print(f"请求参数: {params}")

    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()

        result = response.json()

        print("\n" + "=" * 60)
        print("📊 接口响应结果")
        print("=" * 60)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 搜索结果总数: {total}")
            print(f"📊 当前返回记录数: {len(data)}")

            if data:
                print("\n" + "-" * 60)
                print(f"🎵 搜索 \"{keyword}\" 的结果:")
                print("-" * 60)

                for idx, music in enumerate(data, 1):
                    song_name = safe_get_value(music, 'songName', '未知歌曲')
                    author_name = safe_get_value(music, 'authorName', '未知歌手')
                    album_name = safe_get_value(music, 'albumName', '未知专辑')
                    music_id = safe_get_value(music, 'id', 'N/A')
                    is_favorite = safe_get_int(music, 'isFavorite', 0)
                    is_hot = safe_get_int(music, 'isHot', 0)

                    # 匹配的字段标记
                    matched_fields = []
                    if keyword.lower() in song_name.lower():
                        matched_fields.append("歌曲名")
                    if keyword.lower() in author_name.lower():
                        matched_fields.append("歌手名")
                    if keyword.lower() in album_name.lower():
                        matched_fields.append("专辑名")

                    print(f"{idx}. 🎶 {song_name}")
                    print(f"   - 歌手: {author_name}")
                    print(f"   - 专辑: {album_name}")
                    print(f"   - 音乐ID: {music_id}")
                    print(f"   - 匹配字段: {', '.join(matched_fields) if matched_fields else '未知'}")
                    print(f"   - 收藏状态: {'❤️ 已收藏' if is_favorite == 1 else '🤍 未收藏'}")
                    print(f"   - 是否热门: {'🔥 热门' if is_hot == 1 else '普通'}")
                    print("-" * 50)
            else:
                print(f"\n💡 未找到与 \"{keyword}\" 相关的音乐")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")

    # ==================== 测试2：多关键词搜索 ====================
    print("\n" + "=" * 60)
    print("测试2：多关键词搜索 (keyword: 周杰伦)")
    print("=" * 60)

    params2 = {
        "keyword": "周杰伦",
        "pageNum": 1,
        "pageSize": 10
    }

    try:
        response = requests.get(search_url, headers=headers, params=params2)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 搜索 \"周杰伦\" 结果总数: {total}")

            if data:
                print("\n前5首搜索结果:")
                for idx, music in enumerate(data[:5], 1):
                    song_name = safe_get_value(music, 'songName', '未知歌曲')
                    author_name = safe_get_value(music, 'authorName', '未知歌手')
                    is_favorite = safe_get_int(music, 'isFavorite', 0)
                    fav_icon = "❤️" if is_favorite == 1 else "🤍"
                    print(f"  {idx}. {fav_icon} 《{song_name}》- {author_name}")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 测试3：空关键词（错误场景） ====================
    print("\n" + "=" * 60)
    print("测试3：空关键词（错误场景）")
    print("=" * 60)

    params3 = {
        "keyword": "",
        "pageNum": 1,
        "pageSize": 10
    }

    try:
        response = requests.get(search_url, headers=headers, params=params3)
        result = response.json()

        if result.get("status") != "SUCCESS":
            print(f"✅ 空关键词被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：空关键词未被拦截")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 测试4：分页测试 ====================
    print("\n" + "=" * 60)
    print("测试4：分页测试（第2页）")
    print("=" * 60)

    params4 = {
        "keyword": keyword,
        "pageNum": 2,
        "pageSize": 5
    }

    try:
        response = requests.get(search_url, headers=headers, params=params4)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 第2页返回记录数: {len(data)}")
            print(f"📊 总记录数: {total}")

            if data:
                print("\n第2页音乐列表:")
                for idx, music in enumerate(data, 1):
                    song_name = safe_get_value(music, 'songName', '未知歌曲')
                    print(f"  {idx}. 《{song_name}》")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 测试5：未认证请求 ====================
    print("\n" + "=" * 60)
    print("测试5：未认证请求（错误场景）")
    print("=" * 60)

    try:
        response = requests.get(search_url, params=params)
        result = response.json()

        if response.status_code == 401:
            print(f"✅ 未认证请求被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：未认证请求未被拦截")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


def test_search_suggestions():
    """
    测试搜索建议（展示不同关键词的搜索结果）
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    keywords = ["爱", "梦", "心", "夜", "风", "雨", "月", "阳光", "春天", "大海"]

    # ==================== 登录 ====================
    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"\n✅ 登录成功！")
    headers = {'Authorization': f'Bearer {token}'}

    search_url = f"{base_url}/service/music/searchMusic"

    print("\n" + "=" * 60)
    print("📊 热门关键词搜索结果统计")
    print("=" * 60)
    print(f"{'关键词':<10} {'结果数':<10} {'状态'}")
    print("-" * 40)

    for keyword in keywords:
        params = {
            "keyword": keyword,
            "pageNum": 1,
            "pageSize": 1
        }

        try:
            response = requests.get(search_url, headers=headers, params=params)
            result = response.json()

            if result.get("status") == "SUCCESS":
                total = result.get("total", 0)
                status = "✅" if total > 0 else "❌"
                print(f"{keyword:<10} {total:<10} {status}")
            else:
                print(f"{keyword:<10} {'错误':<10} ❌")

        except Exception as e:
            print(f"{keyword:<10} {'异常':<10} ❌")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🎵 测试关键词搜索音乐接口")
    print("=" * 60)
    print("\n提示：确保 music 表中有数据")
    print()

    # 运行测试
    test_search_music()

    print("\n" + "=" * 60)

    # 搜索建议统计
    test_search_suggestions()

    print("\n" + "=" * 60)
    print("  ✅ 所有测试完成")
    print("=" * 60)