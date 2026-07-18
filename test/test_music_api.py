import requests
import hashlib
import json


def md5_encrypt(text):
    """对字符串进行MD5加密"""
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()


def test_get_music_classify():
    """
    测试获取音乐分类接口
    流程：
    1. 调用登录接口获取 token
    2. 使用 token 调用 getMusicClassify 接口
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

    # ==================== 第二步：调用 getMusicClassify 接口 ====================
    print("\n" + "=" * 60)
    print("第二步：调用 getMusicClassify 获取音乐分类")
    print("=" * 60)

    classify_url = f"{base_url}/service/music/getMusicClassify"

    # 构建请求头，携带 Bearer Token
    classify_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    try:
        classify_response = requests.get(classify_url, headers=classify_headers)
        classify_response.raise_for_status()

        classify_result = classify_response.json()
        print(f"\n音乐分类接口响应:")
        print(json.dumps(classify_result, ensure_ascii=False, indent=2))

        # 检查接口是否成功
        if classify_result.get("status") == "SUCCESS":
            classify_data = classify_result.get("data", [])
            total = classify_result.get("total", 0)

            if classify_data and len(classify_data) > 0:
                print(f"\n✅ 获取音乐分类成功！共 {total} 条记录")
                print("\n分类列表：")
                print("-" * 60)
                for idx, item in enumerate(classify_data, 1):
                    print(f"{idx}. {item.get('classifyName', 'N/A')}")
                    print(f"   - ID: {item.get('id', 'N/A')}")
                    print(f"   - 排序权重: {item.get('classifyRank', 'N/A')}")
                    print(f"   - 权限: {item.get('permission', 'N/A')}")
                    print(f"   - 图标: {item.get('cover', 'N/A')}")
                    print(f"   - 状态: {'启用' if item.get('disabled') == 0 else '禁用'}")
                    print("-" * 60)
            else:
                print("\n⚠️ 接口返回成功，但 data 为空（暂无分类数据）")
                print(f"   total: {total}")
        else:
            print(f"\n❌ 获取音乐分类失败: {classify_result.get('msg', '未知错误')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 获取音乐分类请求失败: {e}")


if __name__ == "__main__":
    test_get_music_classify()