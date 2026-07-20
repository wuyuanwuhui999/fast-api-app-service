# test_favorite_author_crud.py (修复版)
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


def safe_get_name(author):
    """安全获取歌手名称，处理None值"""
    name = author.get('author_name')
    if name is None:
        return '未知歌手'
    return str(name)


def safe_get_id(author):
    """安全获取歌手ID"""
    author_id = author.get('author_id')
    if author_id is None:
        return 'N/A'
    return str(author_id)


def test_insert_favorite_author():
    """
    测试添加喜欢的歌手
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    author_id = 841138  # 歌手ID（请替换为实际存在的歌手ID）

    # ==================== 登录 ====================
    print("=" * 60)
    print("第一步：用户登录")
    print("=" * 60)

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"\n✅ 登录成功！")

    # ==================== 添加喜欢的歌手 ====================
    print("\n" + "=" * 60)
    print(f"第二步：添加喜欢的歌手 (authorId: {author_id})")
    print("=" * 60)

    insert_url = f"{base_url}/service/music/insertFavoriteAuthor/{author_id}"
    headers = {
        'Authorization': f'Bearer {token}'
    }

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
            print(f"\n✅ {result.get('msg')}")
        else:
            print(f"\n❌ {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")


def test_delete_favorite_author():
    """
    测试删除喜欢的歌手
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    author_id = 841138  # 歌手ID

    # ==================== 登录 ====================
    print("=" * 60)
    print("第一步：用户登录")
    print("=" * 60)

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"\n✅ 登录成功！")

    # ==================== 删除喜欢的歌手 ====================
    print("\n" + "=" * 60)
    print(f"第二步：删除喜欢的歌手 (authorId: {author_id})")
    print("=" * 60)

    delete_url = f"{base_url}/service/music/deleteFavoriteAuthor/{author_id}"
    headers = {
        'Authorization': f'Bearer {token}'
    }

    print(f"\n请求URL: {delete_url}")
    print(f"请求方式: DELETE")

    try:
        response = requests.delete(delete_url, headers=headers)
        response.raise_for_status()

        result = response.json()

        print("\n" + "=" * 60)
        print("📊 接口响应结果")
        print("=" * 60)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            print(f"\n✅ {result.get('msg')}")
        else:
            print(f"\n❌ {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")


def test_crud_flow():
    """
    测试完整的增删查流程
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    author_id = 841138  # 周杰伦的author_id

    # ==================== 登录 ====================
    print("=" * 60)
    print("用户登录")
    print("=" * 60)

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"✅ 登录成功！\n")
    headers = {'Authorization': f'Bearer {token}'}

    # ==================== 1. 先查询当前喜欢的歌手列表 ====================
    print("=" * 60)
    print("步骤1：查询当前喜欢的歌手列表")
    print("=" * 60)

    favorite_url = f"{base_url}/service/music/getFavoriteAuthor"
    response = requests.get(favorite_url, headers=headers)
    result = response.json()

    current_favorites = result.get("data", [])
    print(f"当前喜欢的歌手数量: {len(current_favorites)}")

    # 安全获取作者信息（处理None值）
    author_ids = []
    author_names = []
    for author in current_favorites:
        aid = safe_get_id(author)
        name = safe_get_name(author)
        author_ids.append(aid)
        author_names.append(name)

    print(f"喜欢的歌手: {', '.join(author_names) if author_names else '无'}")

    # 检查目标作者是否已在列表中
    target_in_list = str(author_id) in author_ids
    print(f"目标歌手 (authorId: {author_id}) 是否在列表中: {'是' if target_in_list else '否'}")

    # ==================== 2. 添加喜欢的歌手 ====================
    print("\n" + "=" * 60)
    print(f"步骤2：添加喜欢的歌手 (authorId: {author_id})")
    print("=" * 60)

    insert_url = f"{base_url}/service/music/insertFavoriteAuthor/{author_id}"
    response = requests.post(insert_url, headers=headers)
    result = response.json()
    print(f"添加结果: {result.get('msg')}")

    # ==================== 3. 再次查询喜欢的歌手列表 ====================
    print("\n" + "=" * 60)
    print("步骤3：再次查询喜欢的歌手列表（验证添加）")
    print("=" * 60)

    response = requests.get(favorite_url, headers=headers)
    result = response.json()

    new_favorites = result.get("data", [])
    print(f"添加后喜欢的歌手数量: {len(new_favorites)}")

    new_author_ids = []
    new_author_names = []
    for author in new_favorites:
        aid = safe_get_id(author)
        name = safe_get_name(author)
        new_author_ids.append(aid)
        new_author_names.append(name)

    print(f"喜欢的歌手: {', '.join(new_author_names) if new_author_names else '无'}")

    if str(author_id) in new_author_ids:
        print(f"✅ 歌手ID {author_id} 已成功添加")
    else:
        print(f"⚠️ 歌手ID {author_id} 未在列表中")

    # ==================== 4. 删除喜欢的歌手 ====================
    print("\n" + "=" * 60)
    print(f"步骤4：删除喜欢的歌手 (authorId: {author_id})")
    print("=" * 60)

    delete_url = f"{base_url}/service/music/deleteFavoriteAuthor/{author_id}"
    response = requests.delete(delete_url, headers=headers)
    result = response.json()
    print(f"删除结果: {result.get('msg')}")

    # ==================== 5. 最后查询喜欢的歌手列表 ====================
    print("\n" + "=" * 60)
    print("步骤5：最后查询喜欢的歌手列表（验证删除）")
    print("=" * 60)

    response = requests.get(favorite_url, headers=headers)
    result = response.json()

    final_favorites = result.get("data", [])
    print(f"最终喜欢的歌手数量: {len(final_favorites)}")

    final_author_ids = []
    final_author_names = []
    for author in final_favorites:
        aid = safe_get_id(author)
        name = safe_get_name(author)
        final_author_ids.append(aid)
        final_author_names.append(name)

    print(f"喜欢的歌手: {', '.join(final_author_names) if final_author_names else '无'}")

    if str(author_id) not in final_author_ids:
        print(f"✅ 歌手ID {author_id} 已成功删除")
    else:
        print(f"⚠️ 歌手ID {author_id} 仍在列表中")


def test_duplicate_insert():
    """
    测试重复添加喜欢的歌手
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    author_id = 841138

    # ==================== 登录 ====================
    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"✅ 登录成功！\n")
    headers = {'Authorization': f'Bearer {token}'}

    # 先确保歌手被删除（清理状态）
    delete_url = f"{base_url}/service/music/deleteFavoriteAuthor/{author_id}"
    requests.delete(delete_url, headers=headers)

    # ==================== 第一次添加 ====================
    print("=" * 60)
    print(f"第一次添加喜欢的歌手 (authorId: {author_id})")
    print("=" * 60)

    insert_url = f"{base_url}/service/music/insertFavoriteAuthor/{author_id}"
    response = requests.post(insert_url, headers=headers)
    result = response.json()
    print(f"结果: {result.get('msg')}")

    # ==================== 第二次添加（重复） ====================
    print("\n" + "=" * 60)
    print(f"第二次添加喜欢的歌手（重复） (authorId: {author_id})")
    print("=" * 60)

    response = requests.post(insert_url, headers=headers)
    result = response.json()
    print(f"结果: {result.get('msg')}")

    if result.get("status") != "SUCCESS":
        print("✅ 重复添加被正确拦截")
    else:
        print("⚠️ 重复添加未被拦截")

    # ==================== 清理数据 ====================
    print("\n" + "=" * 60)
    print("清理测试数据")
    print("=" * 60)

    response = requests.delete(delete_url, headers=headers)
    result = response.json()
    print(f"清理结果: {result.get('msg')}")


def test_get_favorite_author():
    """
    测试获取用户喜欢的歌手列表（独立测试）
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    # ==================== 登录 ====================
    print("=" * 60)
    print("用户登录")
    print("=" * 60)

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"✅ 登录成功！\n")
    headers = {'Authorization': f'Bearer {token}'}

    # ==================== 获取喜欢的歌手列表 ====================
    print("=" * 60)
    print("获取用户喜欢的歌手列表")
    print("=" * 60)

    favorite_url = f"{base_url}/service/music/getFavoriteAuthor"
    response = requests.get(favorite_url, headers=headers)
    result = response.json()

    print(f"\n完整响应:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("status") == "SUCCESS":
        data = result.get("data", [])
        total = result.get("total", 0)

        print(f"\n📊 用户喜欢的歌手总数: {total}")

        if data:
            print("\n🎵 喜欢的歌手列表:")
            print("-" * 60)

            for idx, author in enumerate(data, 1):
                # 安全获取字段
                name = safe_get_name(author)
                aid = safe_get_id(author)
                cat_id = author.get('category_id', 'N/A')
                avatar = author.get('avatar', '无')
                is_publish = author.get('is_publish', 0)

                print(f"{idx}. 🎤 {name}")
                print(f"   - 歌手ID: {aid}")
                print(f"   - 分类ID: {cat_id}")
                print(f"   - 头像: {avatar}")
                print(f"   - 发布状态: {'✅ 已发布' if is_publish == 1 else '❌ 未发布'}")
                print("-" * 60)

            # 统计信息
            published_count = sum(1 for item in data if item.get('is_publish') == 1)
            print(f"\n📊 统计：共 {len(data)} 位歌手，{published_count} 位已发布")
        else:
            print("\n💡 当前用户还没有喜欢的歌手，请先点赞歌手！")
    else:
        print(f"❌ 请求失败: {result.get('msg')}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🎵 测试添加/删除喜欢的歌手接口")
    print("=" * 60)

    # 测试添加
    test_insert_favorite_author()

    print("\n" + "=" * 60)

    # 测试删除
    test_delete_favorite_author()

    print("\n" + "=" * 60)

    # 测试获取列表
    test_get_favorite_author()

    print("\n" + "=" * 60)

    # 测试完整流程
    test_crud_flow()

    print("\n" + "=" * 60)

    # 测试重复添加
    test_duplicate_insert()