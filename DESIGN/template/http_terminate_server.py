import os
import threading
import time
import signal
import socket
from flask import Flask, request, jsonify


class TerminateHttpServer:
    def __init__(self, port=8081):
        self.app = Flask("TerminateHttpServer")
        self.port = port
        self.server_thread = None

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
            return jsonify({"status": "200", "server": "TerminateHttpServer", "pid": os.getpid()})
        
        @self.app.route('/terminate', methods=['POST'])
        def terminate():
            data = request.json
            if not data:
                return jsonify({"status": "500", "message": "Request data is empty"}), 500
            
            process_identifier = data.get('port')
            if not process_identifier:
                return jsonify({"status": "500", "message": "Missing process identifier ('port')"}), 500
            
            threading.Thread(target=self._exit_process, args=(process_identifier,), daemon=True).start()
            return jsonify({"status": "200", "message": f"Termination signal sent to process {process_identifier}"}), 200
    
    def _exit_process(self, process_identifier):
        print(f"Received termination request for process {process_identifier}...")
        pid = int(process_identifier)
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to PID {pid}")

    def _terminate_by_name(self, process_name):
        import psutil
        found = False
        for proc in psutil.process_iter(['pid', 'name']):
            if process_name.lower() in proc.info['name'].lower():
                print(f"Found matching process: {proc.info['name']} (PID: {proc.info['pid']})")
                os.kill(proc.info['pid'], signal.SIGTERM)
                print(f"Sent SIGTERM to process {proc.info['pid']}")
                found = True
        if not found:
            print(f"No process found with name matching '{process_name}'")

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
                            print(f"发现进程占用端口 {port}: {proc.info['name']} (PID: {proc.info['pid']})")
                            print(f"强制关闭进程 PID: {proc.info['pid']}")
                            proc.kill()
                            proc.wait(timeout=2)
                            print(f"进程 {proc.info['pid']} 已被强制终止")
                            killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except psutil.TimeoutExpired:
                    print(f"进程可能已被终止")
                    killed = True
                    continue
            if killed:
                time.sleep(1)
                return True
            return False
        except ImportError:
            print("需要安装 psutil 库来释放端口: pip install psutil")
            return False
        except Exception as e:
            print(f"释放端口时出错: {e}")
            return False
    
    def start(self):
        if not self.is_port_available(self.port):
            print(f"端口 {self.port} 已被占用，正在尝试释放...")
            if self.kill_process_using_port(self.port):
                print(f"端口 {self.port} 已释放，等待系统回收...")
                time.sleep(1)
                if self.is_port_available(self.port):
                    print(f"端口 {self.port} 现在可用")
                else:
                    raise Exception(f"无法释放端口 {self.port}，请手动检查")
            else:
                raise Exception(f"无法找到或终止占用端口 {self.port} 的进程")
        
        try:
            self.server_thread = threading.Thread(
                target=lambda: self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False),
                daemon=True
            )
            self.server_thread.start()
            print(f"HTTP 终止服务器已启动在端口: {self.port}")
        except Exception as e:
            print(f"启动服务器失败: {e}")
            raise

    def stop(self):
        if self.server_thread:
            print("Shutting down HTTP termination server...")
            os.kill(os.getpid(), signal.SIGINT)


def main():
    try:
        server = TerminateHttpServer(port=8081)
        server.start()
        print(f"服务器正在监听端口: {server.port}")
        print("按 Ctrl+C 停止服务器")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
    except Exception as e:
        print(f"服务器运行错误: {e}")


if __name__ == "__main__":
    main()
