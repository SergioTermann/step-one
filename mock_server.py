#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import json
from datetime import datetime
import threading
import time

app = Flask(__name__)

def log_with_timestamp(message):
    """带时间戳的日志输出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

@app.route('/resource/webSocketOnMessage', methods=['POST'])
def receive_status():
    """接收状态消息的端点"""
    try:
        # 获取请求数据
        data = request.get_json()
        
        # 打印接收到的数据
        log_with_timestamp("=" * 60)
        log_with_timestamp("收到新的状态消息:")
        log_with_timestamp("=" * 60)
        
        if isinstance(data, list):
            for i, item in enumerate(data):
                log_with_timestamp(f"算法 {i+1}:")
                log_with_timestamp(f"  名称: {item.get('name', 'N/A')}")
                log_with_timestamp(f"  类别: {item.get('category', 'N/A')}")
                log_with_timestamp(f"  类名: {item.get('className', 'N/A')}")
                log_with_timestamp(f"  子类别: {item.get('subcategory', 'N/A')}")
                log_with_timestamp(f"  版本: {item.get('version', 'N/A')}")
                log_with_timestamp(f"  IP地址: {item.get('ip', 'N/A')}")
                log_with_timestamp(f"  端口: {item.get('port', 'N/A')}")
                log_with_timestamp(f"  创建者: {item.get('creator', 'N/A')}")
                log_with_timestamp(f"  描述: {item.get('description', 'N/A')}")
                
                # 网络信息
                network_info = item.get('network_info', {})
                if network_info:
                    log_with_timestamp(f"  网络状态: {network_info.get('status', 'N/A')}")
                    log_with_timestamp(f"  是否远程: {network_info.get('is_remote', 'N/A')}")
                    log_with_timestamp(f"  CPU使用率: {network_info.get('cpu_usage', 'N/A')}%")
                    log_with_timestamp(f"  内存使用率: {network_info.get('memory_usage', 'N/A')}%")
                    
                    # GPU信息
                    gpu_usage = network_info.get('gpu_usage', [])
                    if gpu_usage and isinstance(gpu_usage, list):
                        for gpu in gpu_usage:
                            log_with_timestamp(f"  GPU使用率: {gpu.get('usage', 'N/A')}%")
                            log_with_timestamp(f"  GPU内存: {gpu.get('memory_used_mb', 'N/A')}MB / {gpu.get('memory_total_mb', 'N/A')}MB")
                    
                    log_with_timestamp(f"  最后更新时间: {network_info.get('last_update_timestamp', 'N/A')}")
                
                log_with_timestamp("-" * 40)
        else:
            log_with_timestamp("接收到的数据格式:")
            log_with_timestamp(json.dumps(data, indent=2, ensure_ascii=False))
        
        log_with_timestamp("=" * 60)
        
        # 返回成功响应
        return jsonify({"status": "success", "message": "数据接收成功"}), 200
        
    except Exception as e:
        log_with_timestamp(f"处理请求时出错: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

@app.route('/', methods=['GET'])
def index():
    """根路径"""
    return jsonify({
        "message": "模拟需求端HTTP服务正在运行",
        "endpoints": {
            "/resource/webSocketOnMessage": "POST - 接收状态消息",
            "/health": "GET - 健康检查",
            "/": "GET - 服务信息"
        },
        "timestamp": datetime.now().isoformat()
    }), 200

def print_startup_info():
    """打印启动信息"""
    log_with_timestamp("=" * 60)
    log_with_timestamp("模拟需求端HTTP服务启动成功!")
    log_with_timestamp("=" * 60)
    log_with_timestamp("服务地址: http://180.1.80.3:8192")
    log_with_timestamp("主要端点:")
    log_with_timestamp("  POST /resource/webSocketOnMessage - 接收状态消息")
    log_with_timestamp("  GET  /health - 健康检查")
    log_with_timestamp("  GET  / - 服务信息")
    log_with_timestamp("=" * 60)
    log_with_timestamp("等待接收状态消息...")
    log_with_timestamp("=" * 60)

if __name__ == '__main__':
    # 延迟打印启动信息
    def delayed_startup_info():
        time.sleep(1)
        print_startup_info()
    
    startup_thread = threading.Thread(target=delayed_startup_info)
    startup_thread.daemon = True
    startup_thread.start()
    
    # 启动Flask服务
    app.run(host='0.0.0.0', port=8192, debug=False)