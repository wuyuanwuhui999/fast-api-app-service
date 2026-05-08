#!/bin/bash

cd /Users/wuwenqiang/Documents/code/python/fast-api-app-service

# 激活虚拟环境
source .venv/bin/activate

# 启动各个服务（后台运行）
python -m uvicorn user.main:app --reload --port 4005 --host 0.0.0.0 &
python -m uvicorn chat.main:app --reload --port 4006 --host 0.0.0.0 &
python -m uvicorn tenant.main:app --reload --port 4007 --host 0.0.0.0 &
python -m uvicorn prompt.main:app --reload --port 4008 --host 0.0.0.0 &

echo "所有服务已启动"
echo "User Service: http://localhost:4005"
echo "Chat Service: http://localhost:4006"
echo "Tenant Service: http://localhost:4007"
echo "Prompt Service: http://localhost:4008"

# 等待用户按 Ctrl+C
wait