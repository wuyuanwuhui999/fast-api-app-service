import requests
import hashlib
import json


def md5_encrypt(text):
    """对字符串进行MD5加密"""
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()


def test_get_music_author_list_by_category_id():
    """
    测试根据分类ID获取歌手列表接口
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    category_id = 1  # 分类ID
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

    # ==================== 第二步：调用 getMusicAuthorListByCategoryId 接口 ====================
    print("\n" + "=" * 60)
    print(f"第二步：调用 getMusicAuthorListByCategoryId 获取歌手列表（分类ID: {category_id}）")
    print("=" * 60)

    author_url = f"{base_url}/service/music/getMusicAuthorListByCategoryId"

    author_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    params = {
        "categoryId": category_id,
        "pageNum": page_num,
        "pageSize": page_size
    }

    print(f"\n请求URL: {author_url}")
    print(f"请求参数: {json.dumps(params, ensure_ascii=False)}")

    try:
        author_response = requests.get(author_url, headers=author_headers, params=params)
        author_response.raise_for_status()

        author_result = author_response.json()

        print("\n" + "=" * 60)
        print("📊 接口响应结果")
        print("=" * 60)

        print(f"\n完整响应:")
        print(json.dumps(author_result, ensure_ascii=False, indent=2))

        # ==================== 解析响应 ====================
        print("\n" + "=" * 60)
        print("🎯 响应数据解析")
        print("=" * 60)

        status = author_result.get("status")
        msg = author_result.get("msg")
        total = author_result.get("total")
        data = author_result.get("data", [])

        print(f"status: {status}")
        print(f"msg: {msg}")
        print(f"total: {total}")
        print(f"data 长度: {len(data)}")

        if status == "SUCCESS" and data:
            print(f"\n✅ 获取歌手列表成功！共 {total} 条记录，当前返回 {len(data)} 条")

            print("\n" + "-" * 80)
            print("歌手列表：")
            print("-" * 80)

            for idx, item in enumerate(data, 1):
                print(f"{idx}. 🎤 {item.get('authorName', '未知歌手')}")
                print(f"   - ID: {item.get('id', 'N/A')}")
                print(f"   - 歌手ID: {item.get('authorId', 'N/A')}")
                print(f"   - 分类ID: {item.get('categoryId', 'N/A')}")
                print(f"   - 国家: {item.get('country', 'N/A')}")
                print(f"   - 排名: {item.get('rank', 'N/A')}")
                print(f"   - 歌曲数量: {item.get('total', 0)} 首")
                print(f"   - 点赞状态: {'❤️ 已点赞' if item.get('isLike') == 1 else '🤍 未点赞'}")
                if item.get('avatar'):
                    print(f"   - 头像: {item.get('avatar')}")
                print("-" * 80)

            # 统计
            total_songs = sum(item.get('total', 0) for item in data)
            liked_count = sum(1 for item in data if item.get('isLike') == 1)
            print(f"\n📊 统计：共 {len(data)} 位歌手，总歌曲数 {total_songs} 首，{liked_count} 位歌手已点赞")
        else:
            print(f"\n⚠️ {msg or '暂无数据'}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 获取歌手列表请求失败: {e}")


def test_author_list_with_pagination():
    """
    测试歌手列表分页功能
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    category_id = 5

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

    author_url = f"{base_url}/service/music/getMusicAuthorListByCategoryId"
    author_headers = {'Authorization': f'Bearer {token}'}

    page_sizes = [5, 10, 20]

    for page_size in page_sizes:
        params = {
            "categoryId": category_id,
            "pageNum": 1,
            "pageSize": page_size
        }

        try:
            response = requests.get(author_url, headers=author_headers, params=params)
            response.raise_for_status()
            result = response.json()

            total = result.get("total", 0)
            data_len = len(result.get("data", []))
            print(f"pageSize={page_size}: total={total}, 返回={data_len} 条")

        except Exception as e:
            print(f"pageSize={page_size}: 请求失败 - {e}")


if __name__ == "__main__":
    # 测试歌手列表
    test_get_music_author_list_by_category_id()

    # 可选：测试分页
    # test_author_list_with_pagination()