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

    def build_status_message(self, algorithm_name, algorithm_info):
        payload = {
            "name": algorithm_name,
            **(algorithm_info or {})
        }
        # 确保存在network_info字典并添加时间戳
        network_info = payload.get("network_info", {})
        network_info["last_update_timestamp"] = int(time.time())
        payload["network_info"] = network_info
        return payload

    def send_status_message(self, algorithm_name, algorithm_info):
        payload = self.build_status_message(algorithm_name, algorithm_info)
        try:
            response = self.session.post(
                self.remote_url,
                json=payload,
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