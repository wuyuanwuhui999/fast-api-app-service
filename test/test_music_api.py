import requests
import hashlib
import json


def md5_encrypt(text):
    """对字符串进行MD5加密"""
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()


def test_get_music_list_by_author_id():
    """
    测试根据歌手ID获取音乐列表接口
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    author_id = 841138  # 歌手ID（请替换为实际存在的歌手ID）
    page_num = 1
    page_size = 10

    # ==================== 第一步：登录获取 Token ====================
    print("=" * 60)
    print("第一步：用户登录")
    print("=" * 60)

    login_url = f"{base_url}/service/user/login"
    encrypted_password = md5_encrypt(password)

    login_data = {
        "userAccount": user_account,
        "password": encrypted_password
    }

    login_headers = {'Content-Type': 'application/json'}

    try:
        login_response = requests.post(login_url, json=login_data, headers=login_headers)
        login_response.raise_for_status()

        login_result = login_response.json()

        if login_result.get("status") != "SUCCESS":
            print(f"\n❌ 登录失败: {login_result.get('msg', '未知错误')}")
            return

        token = login_result.get("token")
        if not token:
            print("\n❌ 登录响应中未找到 token")
            return

        print(f"\n✅ 登录成功！")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 登录请求失败: {e}")
        return

    # ==================== 第二步：调用 getMusicListByAuthorId 接口 ====================
    print("\n" + "=" * 60)
    print(f"第二步：调用 getMusicListByAuthorId 获取音乐列表（歌手ID: {author_id}）")
    print("=" * 60)

    music_url = f"{base_url}/service/music/getMusicListByAuthorId"

    music_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    params = {
        "authorId": author_id,
        "pageNum": page_num,
        "pageSize": page_size
    }

    print(f"\n请求URL: {music_url}")
    print(f"请求参数: {json.dumps(params, ensure_ascii=False)}")

    try:
        music_response = requests.get(music_url, headers=music_headers, params=params)
        music_response.raise_for_status()

        music_result = music_response.json()

        print("\n" + "=" * 60)
        print("📊 接口响应结果")
        print("=" * 60)

        print(f"\n完整响应:")
        print(json.dumps(music_result, ensure_ascii=False, indent=2))

        # ==================== 解析响应 ====================
        print("\n" + "=" * 60)
        print("🎯 响应数据解析")
        print("=" * 60)

        status = music_result.get("status")
        msg = music_result.get("msg")
        total = music_result.get("total")
        data = music_result.get("data", [])

        print(f"status: {status}")
        print(f"msg: {msg}")
        print(f"total: {total}")
        print(f"data 长度: {len(data)}")

        if status == "SUCCESS" and data:
            print(f"\n✅ 获取音乐列表成功！共 {total} 条记录，当前返回 {len(data)} 条")

            # 打印歌手信息（从第一条数据中获取）
            first_item = data[0] if data else {}
            author_name = first_item.get('authorName', '未知歌手')
            print(f"\n🎤 歌手: {author_name}")

            print("\n" + "-" * 80)
            print("歌曲列表：")
            print("-" * 80)

            for idx, item in enumerate(data, 1):
                print(f"{idx}. 🎵 {item.get('songName', '未知歌曲')}")
                print(f"   - 音乐ID: {item.get('id', 'N/A')}")
                print(f"   - 专辑: {item.get('albumName', 'N/A')}")
                print(f"   - 语言: {item.get('language', 'N/A')}")
                print(f"   - 热门: {'🔥 是' if item.get('isHot') == 1 else '❄️ 否'}")
                print(f"   - 点赞状态: {'❤️ 已点赞' if item.get('isLike') == 1 else '🤍 未点赞'}")
                if item.get('cover'):
                    print(f"   - 封面: {item.get('cover')}")
                if item.get('playUrl'):
                    print(f"   - 播放地址: {item.get('playUrl')[:80]}...")
                print("-" * 80)

            # 统计
            liked_count = sum(1 for item in data if item.get('isLike') == 1)
            hot_count = sum(1 for item in data if item.get('isHot') == 1)
            print(f"\n📊 统计：共 {len(data)} 首歌曲，{liked_count} 首已点赞，{hot_count} 首热门")
        else:
            print(f"\n⚠️ {msg or '暂无数据'}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 获取音乐列表请求失败: {e}")


def test_music_list_pagination():
    """
    测试音乐列表分页功能
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    author_id = 1001

    # ==================== 登录 ====================
    login_url = f"{base_url}/service/user/login"
    encrypted_password = md5_encrypt(password)

    try:
        login_response = requests.post(login_url, json={
            "userAccount": user_account,
            "password": encrypted_password
        })
        login_result = login_response.json()

        if login_result.get("status") != "SUCCESS":
            print(f"登录失败: {login_result.get('msg')}")
            return

        token = login_result.get("token")
        print("✅ 登录成功！")

    except Exception as e:
        print(f"登录失败: {e}")
        return

    # ==================== 测试分页 ====================
    print("\n" + "=" * 60)
    print("测试分页功能")
    print("=" * 60)

    music_url = f"{base_url}/service/music/getMusicListByAuthorId"
    music_headers = {'Authorization': f'Bearer {token}'}

    page_sizes = [5, 10, 20]

    for page_size in page_sizes:
        params = {
            "authorId": author_id,
            "pageNum": 1,
            "pageSize": page_size
        }

        try:
            response = requests.get(music_url, headers=music_headers, params=params)
            response.raise_for_status()
            result = response.json()

            total = result.get("total", 0)
            data_len = len(result.get("data", []))
            print(f"pageSize={page_size}: total={total}, 返回={data_len} 条")

        except Exception as e:
            print(f"pageSize={page_size}: 请求失败 - {e}")


def test_multiple_authors():
    """
    测试多个歌手的音乐列表
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    # ==================== 登录 ====================
    login_url = f"{base_url}/service/user/login"
    encrypted_password = md5_encrypt(password)

    try:
        login_response = requests.post(login_url, json={
            "userAccount": user_account,
            "password": encrypted_password
        })
        login_result = login_response.json()

        if login_result.get("status") != "SUCCESS":
            print(f"登录失败: {login_result.get('msg')}")
            return

        token = login_result.get("token")
        print("✅ 登录成功！")

    except Exception as e:
        print(f"登录失败: {e}")
        return

    # ==================== 测试多个歌手 ====================
    print("\n" + "=" * 60)
    print("测试多个歌手的音乐列表")
    print("=" * 60)

    music_url = f"{base_url}/service/music/getMusicListByAuthorId"
    music_headers = {'Authorization': f'Bearer {token}'}

    # 测试多个歌手ID（请替换为实际存在的歌手ID）
    test_author_ids = [1001, 1002, 1003]

    print(f"\n{'歌手ID':<10} {'歌曲总数':<10} {'返回数量':<10} {'状态'}")
    print("-" * 50)

    for author_id in test_author_ids:
        params = {
            "authorId": author_id,
            "pageNum": 1,
            "pageSize": 5
        }

        try:
            response = requests.get(music_url, headers=music_headers, params=params)
            response.raise_for_status()
            result = response.json()

            total = result.get("total", 0)
            data_len = len(result.get("data", []))
            status = result.get("status")

            print(f"{author_id:<10} {total:<10} {data_len:<10} {status}")

        except Exception as e:
            print(f"{author_id:<10} {'错误':<10} {'错误':<10} {str(e)[:20]}")


if __name__ == "__main__":
    # 测试单个歌手
    test_get_music_list_by_author_id()

    # 可选：测试分页
    # test_music_list_pagination()

    # 可选：测试多个歌手
    # test_multiple_authors()