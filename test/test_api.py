import requests
import hashlib

def md5_encrypt(text):
    """对字符串进行MD5加密"""
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()

# 1. 定义接口地址
url = "http://localhost:4009/service/user/login"

# 2. 定义账号密码
userAccount = "吴时吴刻"
password = "123456"

# 3. 对密码进行MD5加密
encrypted_password = md5_encrypt(password)
print(f"加密后的密码: {encrypted_password}")

# 4. 构建请求头和请求体
headers = {
    'Content-Type': 'application/json'
}

data = {
    "userAccount": userAccount,
    "password": encrypted_password
}

# 5. 发送POST请求
try:
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()  # 检查HTTP错误
    
    # 6. 打印返回结果
    print("\n登录接口返回结果:")
    print(response.json())  # 以JSON格式打印
    
except requests.exceptions.RequestException as e:
    print(f"请求发生错误: {e}")