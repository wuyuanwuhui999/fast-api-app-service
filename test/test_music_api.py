import requests
import hashlib
import json


def md5_encrypt(text):
    """对字符串进行MD5加密"""
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()


def test_get_music_list_by_classify_id():
    """
    测试根据分类ID获取音乐列表接口
    流程：
    1. 调用登录接口获取 token
    2. 使用 token 调用 getMusicListByClassifyId 接口（classifyId=5）
    """

    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    # 分类ID（可修改为其他值进行测试）
    classify_id = 5
    page_num = 1
    page_size = 10

    # ==================== 第一步：登录获取 Token ====================
    print("=" * 60)
    print("第一步：用户登录")
    print("=" * 60)

    login_url = f"{base_url}/service/user/login"

    # 对密码进行 MD5 加密
    encrypted_password = md5_encrypt(password)
    print(f"用户账号: {user_account}")
    print(f"原始密码: {password}")
    print(f"MD5加密后: {encrypted_password}")

    login_data = {
        "userAccount": user_account,
        "password": encrypted_password
    }

    login_headers = {
        'Content-Type': 'application/json'
    }

    try:
        login_response = requests.post(login_url, json=login_data, headers=login_headers)
        login_response.raise_for_status()

        login_result = login_response.json()
        print(f"\n登录响应: {json.dumps(login_result, ensure_ascii=False, indent=2)}")

        # 检查登录是否成功
        if login_result.get("status") != "SUCCESS":
            print(f"\n❌ 登录失败: {login_result.get('msg', '未知错误')}")
            return

        # 提取 token
        token = login_result.get("token")
        if not token:
            print("\n❌ 登录响应中未找到 token")
            return

        print(f"\n✅ 登录成功！")
        print(f"Token: {token[:50]}...")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 登录请求失败: {e}")
        return

    # ==================== 第二步：调用 getMusicListByClassifyId 接口 ====================
    print("\n" + "=" * 60)
    print(f"第二步：调用 getMusicListByClassifyId 获取音乐列表（分类ID: {classify_id}）")
    print("=" * 60)

    music_url = f"{base_url}/service/music/getMusicListByClassifyId"

    # 构建请求头，携带 Bearer Token
    music_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    # 请求参数
    params = {
        "classifyId": classify_id,
        "pageNum": page_num,
        "pageSize": page_size
    }

    print(f"\n请求URL: {music_url}")
    print(f"请求参数: {json.dumps(params, ensure_ascii=False)}")

    try:
        music_response = requests.get(music_url, headers=music_headers, params=params)
        music_response.raise_for_status()

        music_result = music_response.json()
        print(f"\n音乐列表接口响应:")
        print(json.dumps(music_result, ensure_ascii=False, indent=2))

        # 检查接口是否成功
        if music_result.get("status") == "SUCCESS":
            music_data = music_result.get("data", [])
            total = music_result.get("total", 0)
            msg = music_result.get("msg")

            if msg:
                print(f"\n📝 提示信息: {msg}")

            if music_data and len(music_data) > 0:
                print(f"\n✅ 获取音乐列表成功！共 {total} 条记录，当前返回 {len(music_data)} 条")
                print(f"\n音乐列表（分类ID: {classify_id}）：")
                print("-" * 80)

                for idx, item in enumerate(music_data, 1):
                    print(f"{idx}. 🎵 {item.get('songName', '未知歌曲')} - {item.get('authorName', '未知歌手')}")
                    print(f"   - 音乐ID: {item.get('id', 'N/A')}")
                    print(f"   - 专辑: {item.get('albumName', 'N/A')}")
                    print(f"   - 分类排名: {item.get('audioRank', 'N/A')}")
                    print(f"   - 点赞状态: {'❤️ 已点赞' if item.get('isLike') == 1 else '🤍 未点赞'}")
                    print(f"   - 热门: {'🔥 是' if item.get('isHot') == 1 else '❄️ 否'}")
                    if item.get('cover'):
                        print(f"   - 封面: {item.get('cover')}")
                    if item.get('playUrl'):
                        print(f"   - 播放地址: {item.get('playUrl')[:80]}...")
                    print("-" * 80)

                # 统计点赞数量
                liked_count = sum(1 for item in music_data if item.get('isLike') == 1)
                print(f"\n📊 统计：共 {len(music_data)} 首歌曲，其中 {liked_count} 首已点赞")

            else:
                print(f"\n⚠️ 接口返回成功，但 data 为空（分类ID {classify_id} 下暂无音乐数据）")
                print(f"   total: {total}")
        else:
            print(f"\n❌ 获取音乐列表失败: {music_result.get('msg', '未知错误')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 获取音乐列表请求失败: {e}")


def test_music_list_with_different_classify_ids():
    """
    测试多个分类ID的音乐列表
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

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

    login_headers = {
        'Content-Type': 'application/json'
    }

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

    # ==================== 第二步：测试多个分类ID ====================
    print("\n" + "=" * 60)
    print("第二步：批量测试多个分类ID")
    print("=" * 60)

    # 测试多个分类ID
    test_classify_ids = [1, 5, 10, 20, 50]

    music_url = f"{base_url}/service/music/getMusicListByClassifyId"
    music_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    results = []

    for classify_id in test_classify_ids:
        params = {
            "classifyId": classify_id,
            "pageNum": 1,
            "pageSize": 5
        }

        try:
            response = requests.get(music_url, headers=music_headers, params=params)
            response.raise_for_status()

            result = response.json()

            if result.get("status") == "SUCCESS":
                data = result.get("data", [])
                total = result.get("total", 0)
                results.append({
                    "classify_id": classify_id,
                    "total": total,
                    "return_count": len(data),
                    "success": True
                })
                print(f"✅ 分类ID {classify_id}: 共 {total} 条记录，返回 {len(data)} 条")
            else:
                results.append({
                    "classify_id": classify_id,
                    "total": 0,
                    "return_count": 0,
                    "success": False,
                    "msg": result.get("msg", "未知错误")
                })
                print(f"❌ 分类ID {classify_id}: {result.get('msg', '未知错误')}")

        except Exception as e:
            results.append({
                "classify_id": classify_id,
                "total": 0,
                "return_count": 0,
                "success": False,
                "msg": str(e)
            })
            print(f"❌ 分类ID {classify_id}: 请求异常 - {e}")

    # 打印汇总结果
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    success_count = sum(1 for r in results if r["success"])
    total_music_count = sum(r["total"] for r in results if r["success"])
    print(f"测试分类数: {len(results)}")
    print(f"成功: {success_count}, 失败: {len(results) - success_count}")
    print(f"总音乐记录数: {total_music_count}")


if __name__ == "__main__":
    # 测试单个分类ID
    test_get_music_list_by_classify_id()

    # 可选：测试多个分类ID
    # test_music_list_with_different_classify_ids()