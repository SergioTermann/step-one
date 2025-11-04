import os
import sys
import threading
import time
import signal
import socket
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
        def handle_exception(error):
            return jsonify({"status": "500", "message": str(error)}), 500
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            client_ip = request.remote_addr
            client_host = request.host
            print(f"[状态查询] 来源IP: {client_ip}, Host: {client_host}")
            
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
            print(f"[终止请求] 来源IP: {client_ip}, Host: {client_host}")
            
            if self.allowed_ips and client_ip not in self.allowed_ips:
                print(f"[拒绝访问] IP {client_ip} 不在白名单中")
                return jsonify({
                    "status": "403",
                    "message": f"Access denied for IP: {client_ip}",
                    "client_ip": client_ip
                }), 403
            
            data = request.json
            if not data:
                return jsonify({
                    "status": "500",
                    "message": "Request data is empty",
                    "client_ip": client_ip
                }), 500
            
            process_identifier = data.get('port')
            if not process_identifier:
                return jsonify({
                    "status": "500",
                    "message": "Missing process identifier ('port')",
                    "client_ip": client_ip
                }), 500
            
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
            print(f"[日志查询] 来源IP: {client_ip}")
            return jsonify({
                "status": "200",
                "logs": self.request_log,
                "client_ip": client_ip
            })
    
    def _exit_process(self, process_identifier, client_ip):
        print(f"[执行终止] 目标进程: {process_identifier}, 请求来源: {client_ip}")
        try:
            pid = int(process_identifier)
            os.kill(pid, signal.SIGTERM)
            print(f"[成功] 已向 PID {pid} 发送 SIGTERM 信号")
        except Exception as e:
            print(f"[失败] 终止进程失败: {e}")
    
    def is_port_available(self, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def kill_process_using_port(self, port):
        try:
            import psutil
            killed = False
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    for conn in proc.connections():
                        if conn.laddr.port == port:
                            print(f"[端口冲突] 发现进程占用端口 {port}: {proc.info['name']} (PID: {proc.info['pid']})")
                            print(f"[强制关闭] 正在终止进程 PID: {proc.info['pid']}")
                            proc.kill()
                            proc.wait(timeout=2)
                            print(f"[成功] 进程 {proc.info['pid']} 已被强制终止")
                            killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except psutil.TimeoutExpired:
                    print(f"[超时] 进程可能已被终止")
                    killed = True
                    continue
            if killed:
                time.sleep(1)
                return True
            return False
        except ImportError:
            print("[错误] 需要安装 psutil 库: pip install psutil")
            return False
        except Exception as e:
            print(f"[错误] 释放端口时出错: {e}")
            return False
    
    def set_allowed_ips(self, ips):
        if isinstance(ips, str):
            self.allowed_ips = [ips]
        elif isinstance(ips, list):
            self.allowed_ips = ips
        else:
            self.allowed_ips = []
        print(f"[IP白名单] 已设置允许的IP: {self.allowed_ips}")
    
    def start(self, port=8081, allowed_ips=None):
        if self.is_running:
            print(f"[警告] 终止服务已在端口 {self.port} 运行")
            return True
        
        self.port = port
        
        if allowed_ips:
            self.set_allowed_ips(allowed_ips)
        
        if not self.is_port_available(self.port):
            print(f"[端口冲突] 端口 {self.port} 已被占用，正在尝试释放...")
            if self.kill_process_using_port(self.port):
                print(f"[成功] 端口 {self.port} 已释放，等待系统回收...")
                time.sleep(1)
                if self.is_port_available(self.port):
                    print(f"[成功] 端口 {self.port} 现在可用")
                else:
                    print(f"[失败] 无法释放端口 {self.port}")
                    return False
            else:
                print(f"[失败] 无法找到或终止占用端口 {self.port} 的进程")
                return False
        
        try:
            self.server_thread = threading.Thread(
                target=lambda: self.app.run(
                    host='0.0.0.0',
                    port=self.port,
                    debug=False,
                    use_reloader=False
                ),
                daemon=True
            )
            self.server_thread.start()
            self.is_running = True
            print(f"[启动成功] HTTP终止服务已启动在端口 {self.port}")
            print(f"[监听地址] 0.0.0.0:{self.port}")
            print(f"[当前进程] PID: {os.getpid()}")
            return True
        except Exception as e:
            print(f"[启动失败] {e}")
            return False
    
    def stop(self):
        if self.is_running:
            print("[关闭服务] 正在关闭HTTP终止服务...")
            self.is_running = False
            os.kill(os.getpid(), signal.SIGINT)
    
    def print_logs(self):
        print("\n" + "="*60)
        print("请求日志记录:")
        print("="*60)
        for idx, log in enumerate(self.request_log, 1):
            print(f"\n[{idx}] {log['timestamp']}")
            print(f"    端点: {log['endpoint']}")
            print(f"    IP地址: {log['ip']}")
            print(f"    主机: {log['host']}")
            print(f"    操作: {log['action']}")
            if 'target' in log:
                print(f"    目标: {log['target']}")
        print("="*60 + "\n")


def start_terminate_service(port=8081, allowed_ips=None):
    manager = TerminateServiceManager()
    return manager.start(port=port, allowed_ips=allowed_ips)


def get_terminate_service():
    return TerminateServiceManager()


if __name__ == "__main__":
    print("="*60)
    print("算法终止服务管理器")
    print("="*60)
    
    manager = TerminateServiceManager()
    
    if manager.start(port=8081):
        print("\n服务已启动，按 Ctrl+C 停止服务\n")
        try:
            while True:
                time.sleep(5)
                if manager.request_log:
                    manager.print_logs()
        except KeyboardInterrupt:
            print("\n[用户中断] 正在关闭服务...")
            manager.stop()
    else:
        print("[失败] 服务启动失败")
        sys.exit(1)

