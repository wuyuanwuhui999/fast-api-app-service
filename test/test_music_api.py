# test_search_users.py
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


def test_search_users():
    """
    测试：搜索用户接口
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    # 搜索参数
    company_id = "0d3cc1965bd811f18f407875e005753f"
    page_num = 1
    page_size = 20
    keyword = "吴"

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

    # ==================== 搜索用户 ====================
    print("\n" + "=" * 60)
    print("测试：搜索用户")
    print("=" * 60)

    search_url = f"{base_url}/service/company/searchUsers"
    params = {
        "companyId": company_id,
        "pageNum": page_num,
        "pageSize": page_size,
        "keyword": keyword
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
            # data是用户对象列表
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 搜索结果统计:")
            print(f"   - 总记录数: {total}")
            print(f"   - 当前返回记录数: {len(data)}")

            if data:
                print("\n" + "-" * 60)
                print("👤 用户列表:")
                print("-" * 60)

                for idx, user in enumerate(data, 1):
                    print(f"{idx}. 用户对象: {json.dumps(user, ensure_ascii=False, indent=2)}")
                    print("-" * 50)

                print(f"\n📊 共找到 {total} 个用户，当前显示 {len(data)} 个")
            else:
                print("\n💡 未找到匹配的用户")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")

    # ==================== 测试未认证 ====================
    print("\n" + "=" * 60)
    print("测试：未认证请求")
    print("=" * 60)

    try:
        response = requests.get(search_url, params=params)
        result = response.json()

        if response.status_code == 401:
            print(f"✅ 未认证请求被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：未认证请求未被拦截 (状态码: {response.status_code})")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    return token, headers


def test_search_users_with_different_keywords():
    """
    测试：使用不同关键词搜索用户
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    company_id = "0d3cc1965bd811f18f407875e005753f"

    # 不同的搜索关键词
    keywords = ["吴", "时", "刻", "admin", "test"]

    print("\n" + "=" * 60)
    print("测试：使用不同关键词搜索用户")
    print("=" * 60)

    # ==================== 登录 ====================
    token = login(base_url, user_account, password)
    if not token:
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    search_url = f"{base_url}/service/company/searchUsers"

    for keyword in keywords:
        print(f"\n" + "-" * 50)
        print(f"🔍 搜索关键词: '{keyword}'")
        print("-" * 50)

        params = {
            "companyId": company_id,
            "pageNum": 1,
            "pageSize": 20,
            "keyword": keyword
        }

        try:
            response = requests.get(search_url, headers=headers, params=params)
            result = response.json()

            if result.get("status") == "SUCCESS":
                data = result.get("data", [])
                total = result.get("total", 0)

                print(f"   找到 {total} 个用户")

                # 显示前3个结果，直接打印用户对象
                for idx, user in enumerate(data[:3], 1):
                    print(f"   {idx}. 用户对象: {json.dumps(user, ensure_ascii=False)}")

                if len(data) > 3:
                    print(f"   ... 还有 {len(data) - 3} 个用户")
            else:
                print(f"   ❌ 搜索失败: {result.get('msg')}")

        except Exception as e:
            print(f"   ❌ 请求失败: {e}")


def test_search_users_pagination():
    """
    测试：分页功能
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    company_id = "0d3cc1965bd811f18f407875e005753f"
    keyword = "吴"

    print("\n" + "=" * 60)
    print("测试：分页功能")
    print("=" * 60)

    # ==================== 登录 ====================
    token = login(base_url, user_account, password)
    if not token:
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    search_url = f"{base_url}/service/company/searchUsers"

    # 测试不同的分页参数
    test_cases = [
        {"pageNum": 1, "pageSize": 5, "desc": "第1页，每页5条"},
        {"pageNum": 2, "pageSize": 5, "desc": "第2页，每页5条"},
        {"pageNum": 1, "pageSize": 10, "desc": "第1页，每页10条"},
        {"pageNum": 1, "pageSize": 100, "desc": "第1页，每页100条"},
    ]

    for test_case in test_cases:
        print(f"\n" + "-" * 50)
        print(f"📄 {test_case['desc']}")
        print("-" * 50)

        params = {
            "companyId": company_id,
            "pageNum": test_case["pageNum"],
            "pageSize": test_case["pageSize"],
            "keyword": keyword
        }

        try:
            response = requests.get(search_url, headers=headers, params=params)
            result = response.json()

            if result.get("status") == "SUCCESS":
                data = result.get("data", [])
                total = result.get("total", 0)

                print(f"   - 总记录数: {total}")
                print(f"   - 返回记录数: {len(data)}")

                # 打印第一个用户对象示例
                if data:
                    print(f"   - 第一个用户对象示例: {json.dumps(data[0], ensure_ascii=False)}")
            else:
                print(f"   ❌ 查询失败: {result.get('msg')}")

        except Exception as e:
            print(f"   ❌ 请求失败: {e}")


def test_search_users_without_keyword():
    """
    测试：不传关键词（应该返回所有用户）
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    company_id = "0d3cc1965bd811f18f407875e005753f"

    print("\n" + "=" * 60)
    print("测试：不传关键词（查询所有用户）")
    print("=" * 60)

    # ==================== 登录 ====================
    token = login(base_url, user_account, password)
    if not token:
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    search_url = f"{base_url}/service/company/searchUsers"

    # 不传keyword参数
    params = {
        "companyId": company_id,
        "pageNum": 1,
        "pageSize": 20
    }

    print(f"\n请求URL: {search_url}")
    print(f"请求参数: {params} (不含keyword)")

    try:
        response = requests.get(search_url, headers=headers, params=params)
        result = response.json()

        print("\n响应结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n✅ 查询成功！")
            print(f"   - 总用户数: {total}")
            print(f"   - 当前返回: {len(data)} 个用户")

            if data:
                print("\n前5个用户对象:")
                for idx, user in enumerate(data[:5], 1):
                    print(f"   {idx}. {json.dumps(user, ensure_ascii=False)}")
        else:
            print(f"\n❌ 查询失败: {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


def run_all_tests():
    """运行所有测试"""
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    print("\n" + "=" * 70)
    print("  👤 用户搜索功能完整测试")
    print("=" * 70)
    print(f"\n测试环境:")
    print(f"  - 服务地址: {base_url}")
    print(f"  - 测试用户: {user_account}")
    print()

    # ==================== 运行所有测试 ====================
    # 测试1：搜索用户（使用指定参数）
    test_search_users()

    # 测试2：使用不同关键词搜索
    test_search_users_with_different_keywords()

    # 测试3：分页功能测试
    test_search_users_pagination()

    # 测试4：不传关键词测试
    test_search_users_without_keyword()

    # ==================== 测试未认证 ====================
    print("\n" + "=" * 60)
    print("测试：未认证请求")
    print("=" * 60)

    search_url = f"{base_url}/service/company/searchUsers"
    params = {
        "companyId": "0d3cc1965bd811f18f407875e005753f",
        "pageNum": 1,
        "pageSize": 20,
        "keyword": "吴"
    }

    try:
        response = requests.get(search_url, params=params)
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
    print("\n📊 测试覆盖的场景:")
    print("  1. GET  /service/company/searchUsers               - 基础搜索功能")
    print("  2. GET  /service/company/searchUsers               - 不同关键词搜索")
    print("  3. GET  /service/company/searchUsers               - 分页功能测试")
    print("  4. GET  /service/company/searchUsers               - 不传关键词搜索")
    print("  5. GET  /service/company/searchUsers               - 认证拦截测试")
    print("\n📝 测试参数:")
    print("  - companyId: 0d3cc1965bd811f18f407875e005753f")
    print("  - keyword: 吴")
    print("  - pageNum: 1")
    print("  - pageSize: 20")


if __name__ == "__main__":
    run_all_tests()