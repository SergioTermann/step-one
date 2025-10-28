#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from datetime import datetime
import time

def test_send_status():
    """测试发送状态消息"""
    
    # 模拟状态数据
    test_data = [{
        "name": "测试算法",
        "category": "内置组件",
        "className": "协同控制类",
        "subcategory": "测试算法类",
        "version": "1.0",
        "description": "这是一个用于测试的算法",
        "ip": "192.168.1.100",
        "port": 8080,
        "creator": "system",
        "network_info": {
            "status": "运行中",
            "is_remote": True,
            "cpu_usage": 25.5,
            "gpu_usage": [{'usage': 15.2, "index": 0, "name": "GPU-0", "memory_used_mb": 512, "memory_total_mb": 8192}],
            "memory_usage": 45.8,
            "last_update_timestamp": datetime.now().isoformat(),
            "gpu_new": "",
        },
    }]
    
    url = "http://127.0.0.1:8192/resource/webSocketOnMessage"
    
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在发送测试数据到模拟服务...")
        
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 发送成功! HTTP {response.status_code}")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 服务器响应: {response.json()}")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 发送失败! HTTP {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 请求异常: {e}")

def test_health_check():
    """测试健康检查"""
    url = "http://127.0.0.1:8192/health"
    
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在进行健康检查...")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 健康检查通过! {response.json()}")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 健康检查失败! HTTP {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 健康检查异常: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("开始测试模拟需求端HTTP服务")
    print("=" * 60)
    
    # 健康检查
    test_health_check()
    
    print("-" * 40)
    
    # 发送测试数据
    test_send_status()
    
    print("-" * 40)
    print("测试完成!")
    print("=" * 60)