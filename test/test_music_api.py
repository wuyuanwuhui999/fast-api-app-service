# test_favorite_music.py
import requests
import hashlib
import json
import time


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


def test_get_favorite_directory():
    """
    测试1：获取用户音乐收藏夹列表
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"
    music_id = 64340  # 要检查的音乐ID

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

    # ==================== 获取收藏夹列表 ====================
    print("\n" + "=" * 60)
    print(f"测试1：获取音乐收藏夹列表 (musicId: {music_id})")
    print("=" * 60)

    directory_url = f"{base_url}/service/music/getFavoriteDirectory"
    params = {
        "musicId": music_id
    }

    print(f"\n请求URL: {directory_url}")
    print(f"请求参数: {params}")

    try:
        response = requests.get(directory_url, headers=headers, params=params)
        response.raise_for_status()

        result = response.json()

        print("\n" + "=" * 60)
        print("📊 接口响应结果")
        print("=" * 60)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 收藏夹总数: {total}")

            if data:
                print("\n" + "-" * 60)
                print("📁 收藏夹列表:")
                print("-" * 60)

                for idx, directory in enumerate(data, 1):
                    dir_id = safe_get_value(directory, 'id', 'N/A')
                    name = safe_get_value(directory, 'name', '未命名')
                    music_total = safe_get_int(directory, 'total', 0)
                    checked = safe_get_int(directory, 'checked', 0)
                    cover = safe_get_value(directory, 'cover', '无')
                    create_time = safe_get_value(directory, 'createTime', '未知')

                    check_icon = "✅" if checked == 1 else "❌"
                    check_text = "已包含" if checked == 1 else "未包含"

                    print(f"{idx}. 📁 {name}")
                    print(f"   - 收藏夹ID: {dir_id}")
                    print(f"   - 音乐总数: {music_total} 首")
                    print(f"   - 当前音乐状态: {check_icon} {check_text}")
                    print(f"   - 封面图: {cover}")
                    print(f"   - 创建时间: {create_time}")
                    print("-" * 50)

                checked_count = sum(1 for item in data if item.get('checked') == 1)
                print(f"\n📊 统计：共 {total} 个收藏夹，其中 {checked_count} 个包含当前音乐")
            else:
                print("\n💡 暂无收藏夹数据")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")

    # ==================== 测试未认证 ====================
    print("\n" + "=" * 60)
    print("测试：未认证请求")
    print("=" * 60)

    try:
        response = requests.get(directory_url, params=params)
        result = response.json()

        if response.status_code == 401:
            print(f"✅ 未认证请求被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：未认证请求未被拦截")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    return token, headers


def test_create_favorite_directory(token, headers):
    """
    测试2：创建收藏夹
    """
    base_url = "http://localhost:4009"
    create_url = f"{base_url}/service/music/createFavoriteDirectory"

    print("\n" + "=" * 60)
    print("测试2：创建收藏夹")
    print("=" * 60)

    # 测试数据1：正常创建
    test_name = f"测试收藏夹_{int(time.time())}"
    create_data = {"name": test_name}

    print(f"\n请求URL: {create_url}")
    print(f"请求体: {json.dumps(create_data, ensure_ascii=False)}")

    try:
        response = requests.post(create_url, headers=headers, json=create_data)
        response.raise_for_status()

        result = response.json()

        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            data = result.get("data", {})
            directory_id = data.get('id')
            print(f"\n✅ 收藏夹创建成功！")
            print(f"   - 收藏夹ID: {directory_id}")
            print(f"   - 名称: {data.get('name')}")
            return directory_id
        else:
            print(f"\n❌ 创建失败: {result.get('msg')}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")
        return None


def test_update_favorite_directory(token, headers, directory_id):
    """
    测试3：更新收藏夹名称
    """
    if not directory_id:
        print("\n⚠️ 跳过测试3：未提供收藏夹ID")
        return

    base_url = "http://localhost:4009"
    update_url = f"{base_url}/service/music/updateFavoriteDirectory"

    print("\n" + "=" * 60)
    print(f"测试3：更新收藏夹名称 (ID: {directory_id})")
    print("=" * 60)

    new_name = f"更新后的收藏夹_{int(time.time())}"
    update_data = {
        "id": directory_id,
        "name": new_name
    }

    print(f"\n请求URL: {update_url}")
    print(f"请求体: {json.dumps(update_data, ensure_ascii=False)}")

    try:
        response = requests.put(update_url, headers=headers, json=update_data)
        response.raise_for_status()

        result = response.json()

        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            print(f"\n✅ {result.get('msg')}")
            print(f"   - 受影响行数: {result.get('data')}")
            return True
        else:
            print(f"\n❌ 更新失败: {result.get('msg')}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")
        return False


def test_is_music_favorite(token, headers):
    """
    测试4：查询音乐是否已被收藏
    """
    base_url = "http://localhost:4009"
    music_ids = [64340, 64342, 64344, 99999]

    print("\n" + "=" * 60)
    print("测试4：查询音乐是否已被收藏")
    print("=" * 60)

    for music_id in music_ids:
        check_url = f"{base_url}/service/music/isMusicFavorite/{music_id}"

        try:
            response = requests.get(check_url, headers=headers)
            result = response.json()

            if result.get("status") == "SUCCESS":
                count = result.get("data", 0)
                status = "✅ 已收藏" if count > 0 else "❌ 未收藏"
                print(f"  音乐ID {music_id}: {status} (收藏在 {count} 个收藏夹)")
            else:
                print(f"  音乐ID {music_id}: 查询失败 - {result.get('msg')}")

        except Exception as e:
            print(f"  音乐ID {music_id}: 请求失败 - {e}")


def test_insert_music_favorite(token, headers, directory_id):
    """
    测试5：将音乐添加到收藏夹
    """
    if not directory_id:
        print("\n⚠️ 跳过测试5：未提供收藏夹ID")
        return

    base_url = "http://localhost:4009"
    music_id = 64340

    print("\n" + "=" * 60)
    print(f"测试5：将音乐添加到收藏夹 (musicId: {music_id})")
    print("=" * 60)

    insert_url = f"{base_url}/service/music/insertMusicFavorite/{music_id}"
    favorite_ids = [directory_id]

    print(f"\n请求URL: {insert_url}")
    print(f"请求体: {favorite_ids}")

    try:
        response = requests.post(insert_url, headers=headers, json=favorite_ids)
        response.raise_for_status()

        result = response.json()

        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            print(f"\n✅ {result.get('msg')}")
            print(f"   - 新增收藏记录数: {result.get('data')}")
            return True
        else:
            print(f"\n❌ 添加失败: {result.get('msg')}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")
        return False


def test_get_music_list_by_favorite_id(token, headers, directory_id):
    """
    测试6：根据收藏夹ID获取音乐列表
    """
    if not directory_id:
        print("\n⚠️ 跳过测试6：未提供收藏夹ID")
        return

    base_url = "http://localhost:4009"

    print("\n" + "=" * 60)
    print(f"测试6：根据收藏夹ID获取音乐列表 (favoriteId: {directory_id})")
    print("=" * 60)

    list_url = f"{base_url}/service/music/getMusicListByFavoriteId"
    params = {
        "favoriteId": directory_id,
        "pageNum": 1,
        "pageSize": 20
    }

    print(f"\n请求URL: {list_url}")
    print(f"请求参数: {params}")

    try:
        response = requests.get(list_url, headers=headers, params=params)
        response.raise_for_status()

        result = response.json()

        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 收藏夹音乐总数: {total}")
            print(f"📊 当前返回记录数: {len(data)}")

            if data:
                print("\n" + "-" * 50)
                print("🎵 音乐列表:")
                print("-" * 50)

                for idx, music in enumerate(data, 1):
                    song_name = safe_get_value(music, 'songName', '未知歌曲')
                    author_name = safe_get_value(music, 'authorName', '未知歌手')
                    is_like = safe_get_int(music, 'isLike', 0)
                    like_icon = "❤️" if is_like == 1 else "🤍"
                    print(f"{idx}. {like_icon} 《{song_name}》- {author_name}")
            else:
                print("\n💡 该收藏夹暂无音乐")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")


def test_insert_music_favorite_empty(token, headers, directory_id):
    """
    测试7：清空音乐的收藏（传入空列表）
    """
    if not directory_id:
        print("\n⚠️ 跳过测试7：未提供收藏夹ID")
        return

    base_url = "http://localhost:4009"
    music_id = 64340

    print("\n" + "=" * 60)
    print(f"测试7：清空音乐的收藏 (musicId: {music_id})")
    print("=" * 60)

    insert_url = f"{base_url}/service/music/insertMusicFavorite/{music_id}"

    print(f"\n请求URL: {insert_url}")
    print(f"请求体: [] (空列表)")

    try:
        response = requests.post(insert_url, headers=headers, json=[])
        response.raise_for_status()

        result = response.json()

        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            print(f"\n✅ {result.get('msg')}")
            print(f"   - 新增收藏记录数: {result.get('data')}")

            # 验证：查询收藏状态
            check_url = f"{base_url}/service/music/isMusicFavorite/{music_id}"
            check_response = requests.get(check_url, headers=headers)
            check_result = check_response.json()

            if check_result.get("status") == "SUCCESS":
                count = check_result.get("data", 0)
                print(f"   - 验证：音乐ID {music_id} 当前收藏在 {count} 个收藏夹中")
        else:
            print(f"\n❌ {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")


def test_delete_favorite_directory(token, headers, directory_id):
    """
    测试8：删除收藏夹
    """
    if not directory_id:
        print("\n⚠️ 跳过测试8：未提供收藏夹ID")
        return

    base_url = "http://localhost:4009"

    print("\n" + "=" * 60)
    print(f"测试8：删除收藏夹 (ID: {directory_id})")
    print("=" * 60)

    delete_url = f"{base_url}/service/music/deleteFavoriteDirectory/{directory_id}"

    print(f"\n请求URL: {delete_url}")
    print(f"请求方式: DELETE")

    try:
        response = requests.delete(delete_url, headers=headers)
        response.raise_for_status()

        result = response.json()

        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            print(f"\n✅ {result.get('msg')}")
            return True
        else:
            print(f"\n❌ 删除失败: {result.get('msg')}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")
        return False


def test_verify_delete(token, headers, directory_id):
    """
    测试9：验证删除（查询收藏夹列表，确认已删除）
    """
    if not directory_id:
        print("\n⚠️ 跳过测试9：未提供收藏夹ID")
        return

    base_url = "http://localhost:4009"

    print("\n" + "=" * 60)
    print("测试9：验证删除（查询收藏夹列表）")
    print("=" * 60)

    directory_url = f"{base_url}/service/music/getFavoriteDirectory"
    params = {"musicId": 64340}

    try:
        response = requests.get(directory_url, headers=headers, params=params)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            deleted_exists = any(item.get('id') == directory_id for item in data)

            if not deleted_exists:
                print(f"✅ 收藏夹 ID {directory_id} 已成功删除")
            else:
                print(f"❌ 收藏夹 ID {directory_id} 仍然存在")
        else:
            print(f"❌ 查询失败: {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


def test_batch_insert_to_favorite(token, headers):
    """
    测试10：批量添加音乐到多个收藏夹
    """
    base_url = "http://localhost:4009"

    print("\n" + "=" * 60)
    print("测试10：批量添加音乐到多个收藏夹")
    print("=" * 60)

    # 先创建两个收藏夹
    directory_ids = []
    for i in range(2):
        create_data = {"name": f"批量测试收藏夹_{i+1}_{int(time.time())}"}
        response = requests.post(
            f"{base_url}/service/music/createFavoriteDirectory",
            headers=headers,
            json=create_data
        )
        result = response.json()
        if result.get("status") == "SUCCESS":
            directory_ids.append(result.get("data", {}).get('id'))
            print(f"✅ 创建收藏夹 {i+1} 成功，ID: {directory_ids[-1]}")

    if len(directory_ids) < 2:
        print("⚠️ 创建收藏夹不足，跳过批量测试")
        return

    # 批量添加音乐到多个收藏夹
    music_id = 64342
    insert_url = f"{base_url}/service/music/insertMusicFavorite/{music_id}"

    print(f"\n将音乐 {music_id} 添加到收藏夹: {directory_ids}")

    try:
        response = requests.post(insert_url, headers=headers, json=directory_ids)
        result = response.json()

        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            print(f"\n✅ {result.get('msg')}")
            print(f"   - 新增收藏记录数: {result.get('data')}")

            # 验证
            check_url = f"{base_url}/service/music/isMusicFavorite/{music_id}"
            check_response = requests.get(check_url, headers=headers)
            check_result = check_response.json()

            if check_result.get("status") == "SUCCESS":
                count = check_result.get("data", 0)
                print(f"   - 验证：音乐 {music_id} 收藏在 {count} 个收藏夹中")

            # 清理：删除创建的收藏夹
            print("\n清理测试数据...")
            for did in directory_ids:
                delete_url = f"{base_url}/service/music/deleteFavoriteDirectory/{did}"
                requests.delete(delete_url, headers=headers)
                print(f"  已删除收藏夹 {did}")
        else:
            print(f"\n❌ {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


def test_get_music_list_by_favorite_id_pagination(token, headers, directory_id):
    """
    测试11：分页获取收藏夹音乐列表
    """
    if not directory_id:
        print("\n⚠️ 跳过测试11：未提供收藏夹ID")
        return

    base_url = "http://localhost:4009"

    print("\n" + "=" * 60)
    print(f"测试11：分页获取收藏夹音乐列表 (favoriteId: {directory_id})")
    print("=" * 60)

    list_url = f"{base_url}/service/music/getMusicListByFavoriteId"

    # 测试不同分页参数
    test_cases = [
        {"pageNum": 1, "pageSize": 5, "desc": "第1页，每页5条"},
        {"pageNum": 2, "pageSize": 5, "desc": "第2页，每页5条"},
        {"pageNum": 1, "pageSize": 500, "desc": "最大分页（500条）"},
    ]

    for test_case in test_cases:
        params = {
            "favoriteId": directory_id,
            "pageNum": test_case["pageNum"],
            "pageSize": test_case["pageSize"]
        }

        try:
            response = requests.get(list_url, headers=headers, params=params)
            result = response.json()

            if result.get("status") == "SUCCESS":
                data = result.get("data", [])
                total = result.get("total", 0)
                print(f"\n  {test_case['desc']}:")
                print(f"    - 返回记录数: {len(data)}")
                print(f"    - 总记录数: {total}")
            else:
                print(f"\n  {test_case['desc']}: 查询失败")

        except Exception as e:
            print(f"\n  {test_case['desc']}: 请求失败 - {e}")


def test_duplicate_insert_favorite(token, headers, directory_id):
    """
    测试12：重复添加音乐到同一收藏夹（幂等性测试）
    """
    if not directory_id:
        print("\n⚠️ 跳过测试12：未提供收藏夹ID")
        return

    base_url = "http://localhost:4009"
    music_id = 64340

    print("\n" + "=" * 60)
    print(f"测试12：重复添加音乐到同一收藏夹 (musicId: {music_id}, favoriteId: {directory_id})")
    print("=" * 60)

    insert_url = f"{base_url}/service/music/insertMusicFavorite/{music_id}"

    # 第一次添加
    print("\n第一次添加:")
    response1 = requests.post(insert_url, headers=headers, json=[directory_id])
    result1 = response1.json()
    print(f"  结果: {result1.get('msg')}, 新增: {result1.get('data')} 条")

    # 第二次添加（重复）
    print("\n第二次添加（重复）:")
    response2 = requests.post(insert_url, headers=headers, json=[directory_id])
    result2 = response2.json()
    print(f"  结果: {result2.get('msg')}, 新增: {result2.get('data')} 条")

    # 验证：应该有且只有一条记录
    check_url = f"{base_url}/service/music/isMusicFavorite/{music_id}"
    check_response = requests.get(check_url, headers=headers)
    check_result = check_response.json()

    if check_result.get("status") == "SUCCESS":
        count = check_result.get("data", 0)
        print(f"\n验证：音乐 {music_id} 当前收藏在 {count} 个收藏夹中")
        if count <= 1:
            print("✅ 重复添加被正确拦截，没有产生重复记录")
        else:
            print(f"⚠️ 存在 {count} 条记录，可能有重复")


def run_all_tests():
    """运行所有测试"""
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    print("\n" + "=" * 70)
    print("  🎵 音乐收藏夹功能完整测试")
    print("=" * 70)
    print(f"\n测试环境:")
    print(f"  - 服务地址: {base_url}")
    print(f"  - 测试用户: {user_account}")
    print()

    # ==================== 登录 ====================
    print("=" * 60)
    print("第一步：用户登录")
    print("=" * 60)

    token = login(base_url, user_account, password)
    if not token:
        print("❌ 登录失败，终止测试")
        return

    print(f"\n✅ 登录成功！")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    # ==================== 运行所有测试 ====================
    # 测试1：获取收藏夹列表
    test_get_favorite_directory()

    # 测试2：创建收藏夹
    directory_id = test_create_favorite_directory(token, headers)

    if directory_id:
        # 测试3：更新收藏夹名称
        test_update_favorite_directory(token, headers, directory_id)

        # 测试5：将音乐添加到收藏夹
        test_insert_music_favorite(token, headers, directory_id)

        # 测试6：根据收藏夹ID获取音乐列表
        test_get_music_list_by_favorite_id(token, headers, directory_id)

        # 测试11：分页获取收藏夹音乐列表
        test_get_music_list_by_favorite_id_pagination(token, headers, directory_id)

        # 测试12：重复添加测试
        test_duplicate_insert_favorite(token, headers, directory_id)

        # 测试8：删除收藏夹
        test_delete_favorite_directory(token, headers, directory_id)

        # 测试9：验证删除
        test_verify_delete(token, headers, directory_id)

    # 测试4：查询音乐是否已被收藏
    test_is_music_favorite(token, headers)

    # 测试7：清空音乐的收藏（先创建一个临时收藏夹）
    temp_dir_id = test_create_favorite_directory(token, headers)
    if temp_dir_id:
        # 先添加再清空
        test_insert_music_favorite(token, headers, temp_dir_id)
        test_insert_music_favorite_empty(token, headers, temp_dir_id)
        # 清理
        test_delete_favorite_directory(token, headers, temp_dir_id)

    # 测试10：批量添加音乐到多个收藏夹
    test_batch_insert_to_favorite(token, headers)

    # ==================== 测试未认证 ====================
    print("\n" + "=" * 60)
    print("测试：未认证请求")
    print("=" * 60)

    test_url = f"{base_url}/service/music/getFavoriteDirectory"
    params = {"musicId": 64340}

    try:
        response = requests.get(test_url, params=params)
        result = response.json()

        if response.status_code == 401:
            print(f"✅ 未认证请求被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：未认证请求未被拦截 (状态码: {response.status_code})")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # ==================== 测试总结 ====================
    print("\n" + "=" * 70)
    print("  ✅ 所有测试完成！")
    print("=" * 70)
    print("\n📊 测试覆盖的接口:")
    print("  1. GET  /service/music/getFavoriteDirectory      - 获取收藏夹列表")
    print("  2. POST /service/music/createFavoriteDirectory   - 创建收藏夹")
    print("  3. PUT  /service/music/updateFavoriteDirectory   - 更新收藏夹名称")
    print("  4. GET  /service/music/isMusicFavorite/{id}      - 查询音乐是否已收藏")
    print("  5. POST /service/music/insertMusicFavorite/{id}  - 添加音乐到收藏夹")
    print("  6. GET  /service/music/getMusicListByFavoriteId  - 获取收藏夹音乐列表")
    print("  7. DELETE /service/music/deleteFavoriteDirectory/{id} - 删除收藏夹")
    print("  8. 分页测试")
    print("  9. 幂等性测试")
    print("  10. 批量添加测试")
    print("  11. 清空收藏测试")
    print("  12. 认证拦截测试")


if __name__ == "__main__":
    run_all_tests()