import requests
import hashlib
import json


def md5_encrypt(text):
    """对字符串进行MD5加密"""
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()


def test_get_keyword_music():
    """
    测试获取推荐音乐接口
    流程：
    1. 调用登录接口获取 token
    2. 使用 token 调用 getKeywordMusic 接口
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

    # ==================== 第二步：调用 getKeywordMusic 接口 ====================
    print("\n" + "=" * 60)
    print("第二步：调用 getKeywordMusic 获取推荐音乐")
    print("=" * 60)

    music_url = f"{base_url}/service/music/getKeywordMusic"

    # 构建请求头，携带 Bearer Token
    music_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    try:
        music_response = requests.get(music_url, headers=music_headers)
        music_response.raise_for_status()

        music_result = music_response.json()
        print(f"\n推荐音乐接口响应:")
        print(json.dumps(music_result, ensure_ascii=False, indent=2))

        # 检查接口是否成功
        if music_result.get("status") == "SUCCESS":
            music_data = music_result.get("data")
            if music_data:
                print("\n✅ 获取推荐音乐成功！")
                print(f"   - 歌曲名: {music_data.get('songName', 'N/A')}")
                print(f"   - 作者: {music_data.get('authorName', 'N/A')}")
                print(f"   - 专辑: {music_data.get('albumName', 'N/A')}")
                print(f"   - 是否热门: {'是' if music_data.get('isHot') else '否'}")
                print(f"   - 是否点赞: {'是' if music_data.get('isLike') else '否'}")
            else:
                print("\n⚠️ 接口返回成功，但 data 为空（暂无推荐音乐）")
        else:
            print(f"\n❌ 获取推荐音乐失败: {music_result.get('msg', '未知错误')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 获取推荐音乐请求失败: {e}")


if __name__ == "__main__":
    test_get_keyword_music()