# test_upload_doc.py
import requests
import os
import sys
from pathlib import Path


def upload_document(
    file_path: str,
    token: str,
    directory_id: str = "public",
    tenant_id: str = "personal",
    gateway_url: str = "http://localhost:4009"
):
    """
    调用上传文档接口
    
    Args:
        file_path: 要上传的文件路径（支持 PDF 或 TXT）
        token: JWT token（包含 Bearer 前缀）
        directory_id: 目录ID，默认为 "public"
        tenant_id: 租户ID，默认为 "personal"
        gateway_url: 网关地址，默认为 "http://localhost:4009"
    """
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 错误：文件不存在 - {file_path}")
        return None
    
    # 检查文件扩展名
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in ['.pdf', '.txt']:
        print(f"❌ 错误：只支持 PDF 和 TXT 文件，当前文件: {file_ext}")
        return None
    
    # 构建URL
    url = f"{gateway_url}/service/chat/uploadDoc/{tenant_id}/{directory_id}"
    
    # 构建请求头
    headers = {
        "Authorization": token if token.startswith("Bearer ") else f"Bearer {token}",
        "Accept": "application/json"
    }
    
    # 准备文件
    with open(file_path, 'rb') as f:
        files = {
            'file': (os.path.basename(file_path), f, 'application/octet-stream')
        }
        
        print(f"📤 正在上传文件: {os.path.basename(file_path)}")
        print(f"📍 目标URL: {url}")
        print(f"📁 目录ID: {directory_id}")
        print(f"🏢 租户ID: {tenant_id}")
        print("-" * 50)
        
        try:
            # 发送请求
            response = requests.post(
                url,
                headers=headers,
                files=files,
                timeout=60
            )
            
            # 打印响应
            print(f"📊 HTTP状态码: {response.status_code}")
            print("-" * 50)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 上传成功!")
                print(f"响应内容: {result}")
                return result
            else:
                print(f"❌ 上传失败!")
                print(f"响应内容: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ 请求超时")
            return None
        except requests.exceptions.ConnectionError:
            print("❌ 连接失败，请确保网关服务已启动")
            return None
        except Exception as e:
            print(f"❌ 发生错误: {str(e)}")
            return None


def main():
    """主函数"""
    
    # ====== 配置参数（请根据需要修改） ======
    
    # JWT Token（包含 Bearer 前缀）
    TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ7XCJ1c2VyX2FjY291bnRcIjogXCJcdTU0MzRcdTYwMjhcdTU0MzRcdTYwOTRcIiwgXCJlbWFpbFwiOiBcIjI3NTAxODcyM0BxcS5jb21cIiwgXCJ1c2VybmFtZVwiOiBcIlx1NTQzNFx1NjAyOFx1NTQzNFx1NjA5NFwiLCBcImlkXCI6IFwiZTk5MWJmZTc1OThlNGViZWFiM2RkNGFmOWI3ZDA5YjBcIiwgXCJjcmVhdGVfZGF0ZVwiOiBcIjIwMTktMDgtMTNUMDA6MDA6MDBcIiwgXCJ1cGRhdGVfZGF0ZVwiOiBcIjIwMjQtMDctMzFUMjM6MTU6MzBcIiwgXCJ0ZWxlcGhvbmVcIjogXCIxNTMwMjY4Njk0N1wiLCBcImF2YXRlclwiOiBcIi9zdGF0aWMvdXNlci9hdmF0ZXIvXHU1NDM0XHU2MDI4XHU1NDM0XHU2MDk0LmpwZ1wiLCBcImJpcnRoZGF5XCI6IFwiMTk5MC0xMC0xMFwiLCBcInNleFwiOiBcIjBcIiwgXCJyb2xlXCI6IFwiYWRtaW5cIiwgXCJzaWduXCI6IFwiXHU2NWUwXHU2MDI4XHVmZjBjXHU2NzA5XHU2MDk0XCIsIFwicmVnaW9uXCI6IG51bGwsIFwiZGlzYWJsZWRcIjogMCwgXCJwZXJtaXNzaW9uXCI6IDF9IiwiZXhwIjoxNzg1Mzg2NzAyfQ.IHT15WbRV8ebeTGYioiohjDUY_nViokJHehSxRd0OiM"
    
    # 文件路径（请修改为你要上传的文件路径）
    FILE_PATH = "/Users/wuwenqiang/Downloads/保单_吴文强_商业险_粤B-6CJ89_10574003903210360091.pdf"  # 或 "./test.txt"
    
    # 目录ID（可选，默认为 "public"）
    DIRECTORY_ID = "e3361de7abe341778aa9e0ff0691aa25"
    
    # 租户ID（可选，默认为 "personal"）
    TENANT_ID = "f96f89c075d611f0be3b002b67a509e7"
    
    # 网关地址（可选）
    GATEWAY_URL = "http://localhost:4009"
    
    # ====== 执行上传 ======
    
    print("=" * 50)
    print("🚀 文档上传测试脚本")
    print("=" * 50)
    print()
    
    # 检查token
    if not TOKEN or TOKEN == "Bearer YOUR_TOKEN_HERE":
        print("❌ 错误：请先配置有效的 TOKEN")
        print("提示：在脚本中修改 TOKEN 变量")
        sys.exit(1)
    
    # 执行上传
    result = upload_document(
        file_path=FILE_PATH,
        token=TOKEN,
        directory_id=DIRECTORY_ID,
        tenant_id=TENANT_ID,
        gateway_url=GATEWAY_URL
    )
    
    if result:
        print("\n🎉 脚本执行完成！")
    else:
        print("\n❌ 脚本执行失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()