# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import psutil
import socket
import threading
from datetime import datetime
from flask import Flask, request, jsonify

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except Exception:
            return "127.0.0.1"


class ProcessTerminator:
    def __init__(self, port=9999):
        self.app = Flask("ProcessTerminator")
        self.port = port
        self.server_thread = None
        self.process_map = {}
        self.local_ip = get_local_ip()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 本机IP地址: {self.local_ip}")
        
        @self.app.route('/terminate', methods=['POST'])
        def terminate_handler():
            try:
                data = request.json
                if not data:
                    return jsonify({
                        "status": "error",
                        "message": "请求数据为空"
                    }), 400
                
                target_ip = data.get('target_ip')
                if not target_ip:
                    return jsonify({
                        "status": "error",
                        "message": "缺少目标IP参数"
                    }), 400
                
                if target_ip != self.local_ip:
                    return jsonify({
                        "status": "ignored",
                        "message": f"目标IP({target_ip})不是本机IP({self.local_ip})，请求被忽略"
                    }), 200
                
                process_number = data.get('process_number')
                if not process_number:
                    return jsonify({
                        "status": "error",
                        "message": "缺少进程编号参数"
                    }), 400
                
                result = self.terminate_process(process_number)
                return jsonify(result), 200 if result["status"] == "success" else 400
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"处理请求时出错: {str(e)}"
                }), 500
    
    def register_process(self, process_number, process_id):
        self.process_map[process_number] = process_id
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 注册进程: 编号={process_number}, PID={process_id}")
    
    def terminate_process(self, process_number):
        if process_number not in self.process_map:
            return {
                "status": "error",
                "message": f"未找到进程编号 {process_number}"
            }
        
        try:
            pid = self.process_map[process_number]
            process = psutil.Process(pid)
            process_name = process.name()
            
            process.terminate()
            
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                process.kill()
            
            del self.process_map[process_number]
            
            return {
                "status": "success",
                "message": f"进程 {process_number} (PID={pid}, 名称={process_name}) 已成功终止"
            }
            
        except psutil.NoSuchProcess:
            del self.process_map[process_number]
            return {
                "status": "success",
                "message": f"进程 {process_number} 已不存在，可能已终止"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"终止进程 {process_number} 时出错: {str(e)}"
            }
    
    def start(self):
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False),
            daemon=True
        )
        self.server_thread.start()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 进程终止服务已启动在端口: {self.port}")
        return self.server_thread


_instance = None


def get_terminator(port=8011):
    global _instance
    if _instance is None:
        _instance = ProcessTerminator(port=port)
        _instance.start()
    return _instance


def register_current_process(process_number):
    terminator = get_terminator()
    terminator.register_process(process_number, os.getpid())


if __name__ == "__main__":
    terminator = get_terminator()
    
    register_current_process("test_process")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("程序已手动终止")
