def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个远程地址（不需要真正连接）
        s.connect(("8.8.8.8", 80))
        # 获取本地IP地址
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import threading
import json
import time
import sys
import datetime
import struct
import socket  # 保留socket用于本地监听
import psutil
import pynvml
import os

# Configuration parameters
REMOTE_IP = '180.1.80.3'
REMOTE_PORT = 8192
REMOTE_URL = f'http://{REMOTE_IP}:{REMOTE_PORT}/resource/webSocketOnMessage'
LOCAL_IP = '180.1.80.241'
LOCAL_PORT = 5371


def log_with_timestamp(message):
    """Print message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


class HTTPStatusReporter:
    def __init__(self, remote_url=REMOTE_URL, session=None):
        self.remote_url = remote_url
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.session.headers.update({'Connection': 'close'})
        self._running = False
        self._thread = None

    def get_memory_usage(self):
        """获取当前进程内存使用率"""
        process = psutil.Process(os.getpid())
        return process.memory_percent()

    def get_cpu_usage(self):
        """获取当前进程CPU使用率"""
        process = psutil.Process(os.getpid())
        return process.cpu_percent(interval=1)

    def get_gpu_usage(self):
        """获取当前GPU使用率"""
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_percent = utilization.gpu
            return gpu_percent
        except:
            return 0

    def build_status_message(self, algorithm_name, algorithm_info):
        # 获取当前资源使用情况
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()

        # 构建完整的状态消息
        status_data = [{
            "name": algorithm_name,
            "category": algorithm_info.get("category", "内置组件"),
            "className": algorithm_info.get("class", "协同控制类"),
            "subcategory": algorithm_info.get("subcategory", "打击算法类"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "基于狼群智能的协同打击算法，用于多智能体协同打击任务"),
            "ip": get_local_ip(),
            "port": algorithm_info.get("network_info", {}).get("port", 8080),
            "creator": algorithm_info.get("creator", "system"),
            "network_info": {
                "status": algorithm_info.get("network_info", {}).get("status", "空闲"),
                "is_remote": algorithm_info.get("network_info", {}).get("is_remote", False),
                "cpu_usage": cpu_usage,
                "gpu_usage": [{'usage': gpu_usage, "index": gpu_usage, "name": gpu_usage, "memory_used_mb": 10, "memory_total_mb": 100}],
                "memory_usage": memory_usage,
                "last_update_timestamp": datetime.datetime.now().isoformat(),
                "gpu_new": "",
            },
        }]

        return status_data

    def send_status_message(self, algorithm_name, algorithm_info):
        status_data = self.build_status_message(algorithm_name, algorithm_info)
        try:
            response = self.session.post(
                self.remote_url,
                json=status_data,
                headers={'Content-Type': 'application/json', 'Connection': 'close'},
                timeout=5
            )
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] 发送结果: HTTP {response.status_code}")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] 发送失败: {e}")
            return False

    def start_periodic_reporting(self, algorithm_name, algorithm_info, interval=30):
        if self._running:
            return self._thread
        self._running = True

        def _worker():
            while self._running:
                self.send_status_message(algorithm_name, algorithm_info)
                time.sleep(max(1, int(interval)))

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()
        return self._thread

    def stop_reporting(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None


class OnlineDebugger:
    def __init__(self):
        self.running = True
        self.remote_socket = None  # 保留用于本地UDP服务器
        self.local_socket = None
        self.client_count = 0
        self.message_count = 0
        self.session = requests.Session()  # 创建HTTP会话
        self.session.trust_env = False  # 禁用系统代理，避免502网关问题
        self.session.headers.update({'Connection': 'close'})
        self.client_addresses = set()  # Track unique client addresses
        log_with_timestamp(f"目标远程服务器: {REMOTE_URL}")
        log_with_timestamp(f"本地监听地址: {LOCAL_IP}:{LOCAL_PORT}")

    def connect_to_remote(self):
        log_with_timestamp("正在测试HTTP连接...")
        try:
            # 使用二进制测试负载，符合服务端常见要求
            test_payload = b'ping'
            log_with_timestamp(f"正在测试HTTP连接到 {REMOTE_URL}...")
            
            try:
                # 发送测试请求（二进制 + octet-stream）
                response = self.session.post(
                    REMOTE_URL,
                    data=test_payload,
                    headers={'Content-Type': 'application/octet-stream'},
                    timeout=5
                )
                
                log_with_timestamp(f"远程响应状态: HTTP {response.status_code}")
                preview = response.text[:100] if hasattr(response, 'text') else ''
                if preview:
                    log_with_timestamp(f"响应内容: {preview}")
                
                if response.status_code == 200:
                    log_with_timestamp(f'HTTP连接到远程服务器 {REMOTE_URL} 已建立')
                    return True
                else:
                    log_with_timestamp("HTTP连接测试失败（可能是代理/网关或端点不匹配）。")
                    return False
                    
            except requests.exceptions.RequestException as e:
                log_with_timestamp(f'HTTP连接测试异常: {e}')
                return False
                
        except Exception as e:
            log_with_timestamp(f'HTTP连接测试失败: {e}')
            return False

    def build_status_message(self):
        payload = {
            "name": "Qwen2.5llm",
            "ip": "192.168.1.100",
            "port": 12345,
            "category": "123",
            "className": "aabb",
            "subcategory": "qwen",
            "version": "2.5",
            "creator": "system",
            "description": "LLM",
            "inputs": [{"name": "promt", "symbol": "prompt", "type": "str", "dimension": 1}],
            "outputs": [{"name": "callback", "symbol": "response", "type": "str", "dimension": 1}],
            "network_info": {

                "status": "free",
                "is_remote": True,
                "last_update_timestamp": 1729468000,
                "cpu_usage": 42.7,
                "memory_usage": 65.2,
                "gpu_usage": [
                    {"index": 0, "name": "NVIDIA RTX 3080", "usage": 72.1, "memory_used_mb": 4200, "memory_total_mb": 10000}
                ]
            }
        }
        return payload

    def send_status_message(self):
        payload = self.build_status_message()
        try:
            response = self.session.post(
                REMOTE_URL,
                json=payload,
                headers={'Content-Type': 'application/json', 'Connection': 'close'},
                timeout=5
            )
            log_with_timestamp(f"发送结果: HTTP {response.status_code}")
            preview = response.text[:200] if hasattr(response, 'text') else ''
            if preview:
                log_with_timestamp(f"响应内容: {preview}")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            log_with_timestamp(f"发送失败: {e}")
            return False

    def run(self):
        log_with_timestamp('开始按指定消息格式发送...')
        ok = self.send_status_message()
        if not ok:
            log_with_timestamp('发送未成功（可检查网络连通性或端点配置）')


if __name__ == '__main__':
    debugger = OnlineDebugger()
    try:
        debugger.run()
    except Exception as e:
        log_with_timestamp(f'程序异常退出: {e}')
        import traceback
        log_with_timestamp('完整错误跟踪:')
        traceback.print_exc()