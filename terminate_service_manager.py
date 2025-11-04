# -*- coding: utf-8 -*-
import os
import sys
import time
import psutil
import threading
from flask import Flask, request, jsonify

class TerminateServiceManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.app = Flask("TerminateService")
            self.app.json.ensure_ascii = False
            self.port = 8081
            self.server_thread = None
            self.is_running = False
            self.request_log = []
            self.allowed_ips = []
            self.initialized = True
            self._setup_routes()

    def _setup_routes(self):
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({"status": "404", "message": "Endpoint not found"}), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({"status": "500", "message": "Internal server error"}), 500

        @self.app.errorhandler(Exception)
        def handle_exception(e):
            return jsonify({"status": "500", "message": str(e)}), 500

        @self.app.route('/status', methods=['GET'])
        def get_status():
            client_ip = request.remote_addr
            client_host = request.host
            self.request_log.append({
                "endpoint": "/status",
                "ip": client_ip,
                "host": client_host,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action": "status_check"
            })
            return jsonify({
                "status": "200",
                "server": "TerminateService",
                "pid": os.getpid(),
                "client_ip": client_ip,
                "client_host": client_host,
                "port": self.port
            })

        @self.app.route('/terminate', methods=['POST'])
        def terminate():
            client_ip = request.remote_addr
            client_host = request.host
            
            if self.allowed_ips and client_ip not in self.allowed_ips:
                self.request_log.append({
                    "endpoint": "/terminate",
                    "ip": client_ip,
                    "host": client_host,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "terminate_rejected",
                    "reason": "IP not whitelisted"
                })
                return jsonify({
                    "status": "403",
                    "message": f"Access denied for IP {client_ip}",
                    "client_ip": client_ip
                }), 403

            data = request.get_json() or {}
            process_identifier = data.get('pid') or data.get('port') or data.get('name')

            if not process_identifier:
                return jsonify({
                    "status": "400",
                    "message": "Missing process identifier (pid, port, or name)",
                    "client_ip": client_ip
                }), 400

            self.request_log.append({
                "endpoint": "/terminate",
                "ip": client_ip,
                "host": client_host,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action": "terminate",
                "target": process_identifier
            })

            threading.Thread(
                target=self._exit_process,
                args=(process_identifier, client_ip),
                daemon=True
            ).start()

            return jsonify({
                "status": "200",
                "message": f"Termination signal sent to process {process_identifier}",
                "client_ip": client_ip
            }), 200

        @self.app.route('/logs', methods=['GET'])
        def get_logs():
            client_ip = request.remote_addr
            return jsonify({
                "status": "200",
                "logs": self.request_log,
                "client_ip": client_ip
            })

    def _exit_process(self, process_identifier, client_ip):
        time.sleep(0.5)
        print(f"\n收到来自 {client_ip} 的终止请求，目标: {process_identifier}")
        print(f"当前进程PID: {os.getpid()}")
        
        try:
            if str(process_identifier) == str(os.getpid()):
                print("正在终止当前进程...")
                os._exit(0)
            else:
                print(f"忽略请求（目标PID {process_identifier} 与当前PID {os.getpid()} 不匹配）")
        except Exception as e:
            print(f"终止进程时出错: {e}")

    def kill_process_using_port(self, port):
        killed = False
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.connections()
                for conn in connections:
                    if conn.laddr.port == port:
                        print(f"强制关闭占用端口 {port} 的进程: PID={proc.pid}, Name={proc.name()}")
                        proc.kill()
                        killed = True
                        time.sleep(0.5)
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return killed

    def is_port_available(self, port):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except OSError:
            return False

    def find_available_port(self, start_port=8080, max_attempts=10):
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_available(port):
                return port
        return None

    def start(self, port=8081, allowed_ips=None):
        if self.is_running:
            print(f"终止服务已在端口 {self.port} 上运行")
            return True

        self.port = port
        self.allowed_ips = allowed_ips or []

        if not self.is_port_available(port):
            print(f"端口 {port} 被占用，正在强制释放...")
            if self.kill_process_using_port(port):
                print(f"已释放端口 {port}")
                time.sleep(1)
            else:
                print(f"无法释放端口 {port}，尝试查找其他可用端口...")
                new_port = self.find_available_port(port, 10)
                if new_port:
                    print(f"使用备用端口: {new_port}")
                    self.port = new_port
                else:
                    print("无法找到可用端口，终止服务启动失败")
                    return False

        def run_server():
            try:
                self.app.run(
                    host='0.0.0.0',
                    port=self.port,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                print(f"Flask服务器启动失败: {e}")
                self.is_running = False

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        
        time.sleep(0.5)
        return True

    def print_logs(self):
        if not self.request_log:
            print("  没有请求记录")
            return
        
        print(f"\n{'='*60}")
        print(f"终止服务请求日志 (端口: {self.port})")
        print(f"{'='*60}")
        for idx, log in enumerate(self.request_log, 1):
            print(f"\n[请求 {idx}]")
            print(f"  时间: {log.get('timestamp')}")
            print(f"  端点: {log.get('endpoint')}")
            print(f"  客户端IP: {log.get('ip')}")
            print(f"  客户端主机: {log.get('host')}")
            print(f"  操作: {log.get('action')}")
            if 'target' in log:
                print(f"  目标: {log.get('target')}")
            if 'reason' in log:
                print(f"  原因: {log.get('reason')}")
        print(f"\n{'='*60}\n")

def start_terminate_service(port=8081, allowed_ips=None):
    manager = TerminateServiceManager()
    return manager.start(port=port, allowed_ips=allowed_ips)

def get_terminate_service():
    return TerminateServiceManager()

if __name__ == "__main__":
    print("启动终止服务测试...")
    if start_terminate_service(port=8081):
        print("终止服务已启动在端口 8081")
        print(f"当前进程PID: {os.getpid()}")
        print("\n测试命令:")
        print(f"  curl http://localhost:8081/status")
        print(f"  curl -X POST http://localhost:8081/terminate -H 'Content-Type: application/json' -d '{{\"pid\": \"{os.getpid()}\"}}'")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n程序退出")
            service = get_terminate_service()
            service.print_logs()
    else:
        print("终止服务启动失败")

