@echo off
echo ========================================
echo   FastAPI 微服务启动器 (Nacos版本)
echo ========================================
echo.

:: 激活虚拟环境
call .venv\Scripts\activate

:: 启动所有服务（后台运行）
start "User Service" cmd /c "python -m uvicorn user.main:app --reload --port 4005 --host 0.0.0.0"
timeout /t 2 /nobreak > nul

start "Chat Service" cmd /c "python -m uvicorn chat.main:app --reload --port 4006 --host 0.0.0.0"
timeout /t 2 /nobreak > nul

start "Tenant Service" cmd /c "python -m uvicorn tenant.main:app --reload --port 4007 --host 0.0.0.0"
timeout /t 2 /nobreak > nul

start "Prompt Service" cmd /c "python -m uvicorn prompt.main:app --reload --port 4008 --host 0.0.0.0"
timeout /t 2 /nobreak > nul

start "Gateway Service" cmd /c "python -m uvicorn gateway.main:app --reload --port 4009 --host 0.0.0.0"

echo.
echo 所有服务已启动
echo ========================================
echo Gateway:    http://localhost:4009
echo User:       http://localhost:4005
echo Chat:       http://localhost:4006  
echo Tenant:     http://localhost:4007
echo Prompt:     http://localhost:4008
echo ========================================
echo.
echo Nacos控制台: http://localhost:8848/nacos
echo 账号/密码: nacos/nacos
echo.
pause