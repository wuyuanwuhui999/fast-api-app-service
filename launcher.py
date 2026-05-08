#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import signal
import sys
import os
import time
import threading
from datetime import datetime

class ServiceManager:
    def __init__(self):
        self.services = [
            {"name": "User Service", "port": 4005, "module": "user.main", "color": "\033[92m"},  # 绿色
            {"name": "Chat Service", "port": 4006, "module": "chat.main", "color": "\033[94m"},  # 蓝色
            {"name": "Tenant Service", "port": 4007, "module": "tenant.main", "color": "\033[93m"},  # 黄色
            {"name": "Prompt Service", "port": 4008, "module": "prompt.main", "color": "\033[95m"},  # 紫色
        ]
        self.processes = []
        self.running = True
        
        # 获取项目根目录
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.venv_python = os.path.join(self.project_dir, ".venv", "bin", "python")
        
        # 检查虚拟环境是否存在
        if not os.path.exists(self.venv_python):
            print(f"\033[91m错误: 找不到虚拟环境: {self.venv_python}\033[0m")
            print("请先创建虚拟环境: python -m venv .venv")
            sys.exit(1)
    
    def print_banner(self):
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     FastAPI 多模块服务一键启动器                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(f"\033[96m{banner}\033[0m")
    
    def log(self, message, color="\033[0m"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {message}\033[0m")
    
    def start_service(self, service):
        """启动单个服务"""
        cmd = [
            self.venv_python, "-m", "uvicorn",
            f"{service['module']}:app",
            "--reload",
            "--port", str(service['port']),
            "--host", "0.0.0.0"
        ]
        
        try:
            # 启动进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 启动日志输出线程
            def output_reader():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        # 美化日志输出
                        if "ERROR" in line:
                            self.log(f"[{service['name']}] {line.strip()}", "\033[91m")
                        elif "WARNING" in line:
                            self.log(f"[{service['name']}] {line.strip()}", "\033[93m")
                        else:
                            self.log(f"[{service['name']}] {line.strip()}", service['color'])
            
            thread = threading.Thread(target=output_reader, daemon=True)
            thread.start()
            
            return process
            
        except Exception as e:
            self.log(f"启动 {service['name']} 失败: {e}", "\033[91m")
            return None
    
    def start_all(self):
        """启动所有服务"""
        self.print_banner()
        
        # 检查端口是否被占用
        for service in self.services:
            port = service['port']
            result = subprocess.run(
                f"lsof -i :{port} | grep LISTEN",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log(f"警告: 端口 {port} 已被占用", "\033[93m")
        
        self.log("正在启动所有服务...", "\033[96m")
        print()
        
        for service in self.services:
            self.log(f"启动 {service['name']} (端口 {service['port']})...", service['color'])
            process = self.start_service(service)
            if process:
                self.processes.append(process)
            time.sleep(1)  # 等待启动
        
        print()
        self.log("=" * 60, "\033[96m")
        self.log("所有服务已启动！", "\033[92m")
        self.log("=" * 60, "\033[96m")
        
        # 打印服务地址
        print()
        for service in self.services:
            print(f"  {service['name']}:  \033[96mhttp://localhost:{service['port']}\033[0m")
        print()
        
        self.log("按 Ctrl+C 停止所有服务", "\033[93m")
        print()
        
        # 等待所有进程
        try:
            for process in self.processes:
                process.wait()
        except KeyboardInterrupt:
            self.stop_all()
    
    def stop_all(self):
        """停止所有服务"""
        print()
        self.log("正在停止所有服务...", "\033[93m")
        
        for process in self.processes:
            if process.poll() is None:  # 如果进程还在运行
                process.terminate()
        
        # 等待进程结束
        time.sleep(2)
        
        # 强制结束未响应的进程
        for process in self.processes:
            if process.poll() is None:
                process.kill()
        
        self.log("所有服务已停止", "\033[92m")
        sys.exit(0)

def main():
    manager = ServiceManager()
    
    # 设置信号处理
    signal.signal(signal.SIGINT, lambda sig, frame: manager.stop_all())
    signal.signal(signal.SIGTERM, lambda sig, frame: manager.stop_all())
    
    manager.start_all()

if __name__ == "__main__":
    main()