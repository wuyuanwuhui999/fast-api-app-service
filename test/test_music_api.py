# test_author_category.py
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


def test_get_author_category():
    """
    测试获取歌手分类列表
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

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

    # ==================== 获取歌手分类列表 ====================
    print("\n" + "=" * 60)
    print("第二步：获取歌手分类列表")
    print("=" * 60)

    category_url = f"{base_url}/service/music/getMusicAuthorCategory"

    print(f"\n请求URL: {category_url}")
    print(f"请求方式: GET")

    try:
        response = requests.get(category_url, headers=headers)
        response.raise_for_status()

        result = response.json()

        print("\n" + "=" * 60)
        print("📊 接口响应结果")
        print("=" * 60)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 歌手分类总数: {total}")

            if data:
                print("\n" + "-" * 60)
                print("🎵 歌手分类列表（按 rank 降序排列）:")
                print("-" * 60)

                for idx, category in enumerate(data, 1):
                    category_id = safe_get_value(category, 'id', 'N/A')
                    category_name = safe_get_value(category, 'categoryName', '未知分类')
                    rank = safe_get_int(category, 'rank', 0)
                    disabled = safe_get_int(category, 'disabled', 0)
                    create_time = safe_get_value(category, 'createTime', '未知')
                    update_time = safe_get_value(category, 'updateTime', '未知')

                    print(f"{idx}. 📁 {category_name}")
                    print(f"   - 分类ID: {category_id}")
                    print(f"   - 排序权重: {rank}")
                    print(f"   - 状态: {'✅ 启用' if disabled == 0 else '❌ 禁用'}")
                    print(f"   - 创建时间: {create_time}")
                    print(f"   - 更新时间: {update_time}")
                    print("-" * 50)

                # 统计信息
                enabled_count = sum(1 for item in data if item.get('disabled') == 0)
                print(f"\n📊 统计：共 {len(data)} 个分类，全部启用")
            else:
                print("\n💡 暂无歌手分类数据")
        else:
            print(f"\n❌ 请求失败: {result.get('msg')}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {e}")

    # ==================== 测试未认证 ====================
    print("\n" + "=" * 60)
    print("测试：未认证请求")
    print("=" * 60)

    try:
        response = requests.get(category_url)
        result = response.json()

        if response.status_code == 401:
            print(f"✅ 未认证请求被正确拦截: {result.get('msg')}")
        else:
            print(f"⚠️ 异常：未认证请求未被拦截")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


def test_get_author_category_detail():
    """
    测试获取歌手分类列表（详细版）
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"\n✅ 登录成功！")
    headers = {'Authorization': f'Bearer {token}'}

    category_url = f"{base_url}/service/music/getMusicAuthorCategory"

    print("\n" + "=" * 60)
    print("📊 歌手分类详情")
    print("=" * 60)

    try:
        response = requests.get(category_url, headers=headers)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])
            total = result.get("total", 0)

            print(f"\n📊 共 {total} 个歌手分类")

            if data:
                # 按 rank 分组显示
                high_rank = [item for item in data if item.get('rank', 0) >= 8]
                mid_rank = [item for item in data if 5 <= item.get('rank', 0) < 8]
                low_rank = [item for item in data if item.get('rank', 0) < 5]

                print("\n🔝 高权重分类 (rank >= 8):")
                for item in high_rank:
                    print(f"  - {item.get('categoryName', '未知')} (rank: {item.get('rank', 0)})")

                print("\n📌 中权重分类 (5 <= rank < 8):")
                for item in mid_rank:
                    print(f"  - {item.get('categoryName', '未知')} (rank: {item.get('rank', 0)})")

                print("\n📎 低权重分类 (rank < 5):")
                for item in low_rank:
                    print(f"  - {item.get('categoryName', '未知')} (rank: {item.get('rank', 0)})")

                # 显示最大和最小rank
                if data:
                    ranks = [safe_get_int(item, 'rank', 0) for item in data]
                    print(f"\n📊 排序范围: 最高 {max(ranks)}，最低 {min(ranks)}")

        else:
            print(f"❌ 请求失败: {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


def test_author_category_simple():
    """
    简单测试：只显示分类名称和排序
    """
    # ==================== 配置参数 ====================
    base_url = "http://localhost:4009"
    user_account = "吴时吴刻"
    password = "123456"

    token = login(base_url, user_account, password)
    if not token:
        return

    print(f"\n✅ 登录成功！")
    headers = {'Authorization': f'Bearer {token}'}

    category_url = f"{base_url}/service/music/getMusicAuthorCategory"

    print("\n" + "=" * 60)
    print("🎵 歌手分类导航")
    print("=" * 60)

    try:
        response = requests.get(category_url, headers=headers)
        result = response.json()

        if result.get("status") == "SUCCESS":
            data = result.get("data", [])

            if data:
                print("\n可用的歌手分类:")
                print("-" * 40)

                # 按 rank 降序显示
                for idx, category in enumerate(data, 1):
                    category_name = safe_get_value(category, 'categoryName', '未知分类')
                    rank = safe_get_int(category, 'rank', 0)
                    print(f"  {idx:2d}. {category_name} (排序: {rank})")

                print("-" * 40)

                # 分类数量统计
                total = len(data)
                print(f"\n共 {total} 个分类")
            else:
                print("\n💡 暂无歌手分类数据")
        else:
            print(f"❌ 请求失败: {result.get('msg')}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🎵 测试获取歌手分类列表接口")
    print("=" * 60)

    # 运行测试
    test_get_author_category()

    print("\n" + "=" * 60)

    # 详细测试
    test_get_author_category_detail()

    print("\n" + "=" * 60)

    # 简单导航测试
    test_author_category_simple()

    print("\n" + "=" * 60)
    print("  ✅ 所有测试完成")
    print("=" * 60)