# -*- coding: utf-8 -*-
import socket
import json
import time
import argparse
import os
import pynvml
import psutil
import numpy as np
import signal
import sys
import threading
import requests
from datetime import datetime
from flask import Flask, request, jsonify


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


class HTTPStatusReporter:
    def __init__(self, server_ip='180.1.80.3', server_port=8192):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({'Connection': 'close'})
        self.server_ip = server_ip
        self.server_port = server_port
        self.base_url = f"http://{server_ip}:{server_port}/resource/webSocketOnMessage"
        self.reporting = False
        self.report_thread = None
        
    def log_with_timestamp(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_memory_usage(self):
        process = psutil.Process(os.getpid())
        return f"{process.memory_percent():.2f}"

    def get_cpu_usage(self):
        process = psutil.Process(os.getpid())
        return f"{process.cpu_percent(interval=1):.2f}"

    def get_gpu_usage(self):
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_percent = utilization.gpu
            return f"{gpu_percent:.2f}"
        except Exception:
            return "0.00"

    def build_status_message(self, algorithm_name, algorithm_info):
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()

        status_data = [{
            "name": algorithm_name,
            "category": algorithm_info.get("category", "内置服务"),
            "className": algorithm_info.get("class", "算法类"),
            "subcategory": algorithm_info.get("subcategory", "通用算法"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "算法描述"),
            "ip": get_local_ip(),
            "port": algorithm_info.get("network_info", {}).get("port", 8080),
            "creator": algorithm_info.get("creator", "system"),
            "network_info": {
                "status": algorithm_info.get("network_info", {}).get("status", "空闲"),
                "is_remote": algorithm_info.get("network_info", {}).get("is_remote", True),
                "cpu_usage": cpu_usage,
                "gpu_usage": [{'usage': gpu_usage, "index": gpu_usage, "name": gpu_usage, "memory_used_mb": 10, "memory_total_mb": 100}],
                "memory_usage": memory_usage,
                "last_update_timestamp": datetime.now().isoformat(),
                "gpu_new": "",
            },
        }]

        return status_data
    
    def send_status_message(self, algorithm_name, algorithm_info):
        try:
            status_data = self.build_status_message(algorithm_name, algorithm_info)

            if not status_data:
                return False

            response = self.session.post(
                self.base_url,
                json=status_data,
                headers={'Content-Type': 'application/json', 'Connection': 'close'},
                timeout=10
            )

            if response.status_code == 200:
                self.log_with_timestamp(f"成功发送算法 '{algorithm_name}' 的状态信息")
                return True
            else:
                self.log_with_timestamp(f"发送状态失败，HTTP状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_with_timestamp(f"发送状态时发生错误: {str(e)}")
            return False
    
    def periodic_report(self, algorithm_name, algorithm_info, interval):
        while self.reporting:
            self.send_status_message(algorithm_name, algorithm_info)
            time.sleep(interval)
    
    def start_periodic_reporting(self, algorithm_name, algorithm_info, interval=30):
        if self.reporting:
            self.log_with_timestamp("状态上报已在运行中")
            return None
            
        self.reporting = True
        self.report_thread = threading.Thread(
            target=self.periodic_report,
            args=(algorithm_name, algorithm_info, interval),
            daemon=True
        )
        self.report_thread.start()
        self.log_with_timestamp(f"启动定期状态上报，间隔: {interval}秒")
        return self.report_thread
    
    def stop_reporting(self):
        if self.reporting:
            self.reporting = False
            if self.report_thread:
                self.report_thread.join(timeout=2)
            self.log_with_timestamp("已停止状态上报")


def get_memory_usage():
    process = psutil.Process(os.getpid())
    return f"{process.memory_percent():.2f}%"


def get_cpu_usage():
    process = psutil.Process(os.getpid())
    return f"{process.cpu_percent(interval=1):.2f}%"


def get_gpu_usage():
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_percent = utilization.gpu
        return f"{gpu_percent:.2f}%"
    except Exception:
        return "0.00%"


class AlgorithmStatusClient:
    def __init__(self, server_ip='127.0.0.1', server_port=12345):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_algorithm_info(self, algorithm_info):
        try:
            data = json.dumps(algorithm_info, ensure_ascii=False).encode('utf-8')
            self.socket.sendto(data, (self.server_ip, self.server_port))
            print(f"已发送算法 '{algorithm_info.get('name', '未命名')}' 的信息到 {self.server_ip}:{self.server_port}")
            return True
        except Exception as e:
            print(f"发送算法信息时发生错误: {str(e)}")
            return False

    def close(self):
        self.socket.close()


def update_algorithm_info(algorithm_info, ip='192.168.43.3', port=9090, status="空闲", is_remote=True):
    if not algorithm_info:
        return None

    algorithm_info["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

    algorithm_info["network_info"] = {
        "ip": ip,
        "port": port,
        "status": status,
        "memory_usage": get_memory_usage(),
        "cpu_usage": get_cpu_usage(),
        "gpu_usage": get_gpu_usage(),
        "is_remote": is_remote
    }

    return algorithm_info


class StandardAlgorithm:
    def __init__(self):
        self.is_running = False
        self.algorithm_name = "标准算法"
        
    def initialize(self, **kwargs):
        pass
        
    def run(self):
        self.is_running = True
        time.sleep(0.5)
        self.is_running = False
        
    def get_result(self):
        return None


program_running = True


def send_offline_status(client, algorithm_info, algo_ip, algo_port, is_remote):
    if client and algorithm_info:
        offline_info = update_algorithm_info(
            algorithm_info,
            ip=algo_ip,
            port=algo_port,
            status="离线",
            is_remote=is_remote
        )
        client.send_algorithm_info(offline_info)
        print("已发送离线状态")


class TerminateServer:
    def __init__(self):
        self.app = Flask("TerminateServer")
        self.server_thread = None
        
        @self.app.route('/terminate', methods=['POST'])
        def terminate_handler():
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 收到终止指令，正在安全关闭...")
            threading.Thread(target=self._exit_process).start()
            return jsonify({"status": "success", "message": "终止信号已接收"}), 200
    
    def _exit_process(self):
        time.sleep(1)
        os._exit(0)
    
    def start(self, port=8081):
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False),
            daemon=True
        )
        self.server_thread.start()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 终止指令监听服务已启动在端口: {port}")


def main():
    parser = argparse.ArgumentParser(description='标准算法模板')
    parser.add_argument('--server', default='127.0.0.1', help='服务器IP地址')
    parser.add_argument('--port', type=int, default=12345, help='服务器端口')
    parser.add_argument('--name', default='标准算法', help='算法名称')
    parser.add_argument('--algo-ip', default='192.168.43.4', help='算法IP地址')
    parser.add_argument('--algo-port', type=int, default=8080, help='算法服务端口')
    parser.add_argument('--interval', type=float, default=2.0, help='发送间隔(秒)')
    parser.add_argument('--count', type=int, default=0, help='发送次数(0表示无限发送)')
    parser.add_argument('--remote', action='store_true', default=True, help='是否为远程算法')
    parser.add_argument('--http-server', default='180.1.80.3', help='远程HTTP服务器IP地址')
    parser.add_argument('--http-port', type=int, default=8192, help='远程HTTP服务器端口')
    parser.add_argument('--terminate-port', type=int, default=8081, help='终止服务监听端口')

    args = parser.parse_args()
    
    terminate_server = TerminateServer()
    terminate_server.start(port=args.terminate_port)
    
    config_param = {
        'category': '内置服务',
        'class': '算法类',
        'subcategory': '通用算法',
        'version': '1.0',
        'creator': 'system',
        'create_time': time.strftime("%Y/%m/%d %H:%M"),
        'maintainer': 'system',
        'update_time': time.strftime("%Y/%m/%d %H:%M"),
        'description': '标准算法模板',
        'inputs': [
            {'name': '输入参数', 'symbol': 'input', 'type': 'vector', 'dimension': '1', 'description': '算法输入'}
        ],
        'outputs': [
            {'name': '输出结果', 'symbol': 'output', 'type': 'vector', 'dimension': '1', 'description': '算法输出'}
        ],
        'network_info': {
            'ip': '127.0.0.1',
            'status': '空闲',
            'is_remote': False
        }
    }

    args.ip = get_local_ip()
    
    http_reporter = HTTPStatusReporter(args.http_server, args.http_port)
    
    algorithm_info = {
        "name": args.name,
        "category": config_param.get("category", "内置服务"),
        "class": config_param.get("class", "算法类"),
        "subcategory": config_param.get("subcategory", "通用算法"),
        "version": config_param.get("version", "1.0"),
        "creator": config_param.get("creator", "system"),
        "description": config_param.get("description", "算法描述"),
        "inputs": config_param.get("inputs", []),
        "outputs": config_param.get("outputs", []),
        "network_info": {
            "ip": args.algo_ip,
            "port": args.algo_port,
            "status": "运行中"
        }
    }

    algorithm = StandardAlgorithm()

    def signal_handler_with_http(sig, frame):
        global program_running
        print(f"\n接收到信号 {sig}，正在关闭程序...")
        program_running = False
        
        offline_info = algorithm_info.copy()
        offline_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.name, offline_info)
        
        http_reporter.stop_reporting()
        
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler_with_http)
    signal.signal(signal.SIGTERM, signal_handler_with_http)

    http_reporter.start_periodic_reporting(args.name, algorithm_info, args.interval)

    count = 0
    while program_running and (args.count == 0 or count < args.count):
        algorithm.run()

        count += 1
        if count > 20:
            algorithm.is_running = False
            
        if args.count > 0:
            print(f"已执行算法 {count}/{args.count} 次")
        else:
            print(f"已执行算法 {count} 次")

        time.sleep(args.interval / 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='临时解析器获取终止端口')
    parser.add_argument('--terminate-port', type=int, default=9999, help='终止服务器端口')
    args, _ = parser.parse_known_args()
    
    def add_terminate_support(port=9999):
        import threading
        import socket
        import json
        import signal
        import time
        import os
        
        class ProcessTerminator:
            def __init__(self, port=9999):
                self.port = port
                self.server_thread = None
                
            def start(self):
                self.server_thread = threading.Thread(target=self._run_server, daemon=True)
                self.server_thread.start()
                return self.server_thread
                
            def _run_server(self):
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind(('0.0.0.0', self.port))
                server_socket.listen(5)
                print(f"Termination server started on port {self.port}")
                
                while True:
                    client_socket, addr = server_socket.accept()
                    data = client_socket.recv(1024).decode('utf-8')
                    if data:
                        request = json.loads(data)
                        if request.get('action') == 'terminate':
                            print("Received termination request, shutting down...")
                            client_socket.send(json.dumps({"status": "success"}).encode('utf-8'))
                            client_socket.close()
                            time.sleep(1)
                            os._exit(0)
                    client_socket.close()
        
        terminator = ProcessTerminator(port=port)
        terminator.start()
        
        def signal_handler(sig, frame):
            print("Received termination signal, shutting down...")
            os._exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    add_terminate_support(port=args.terminate_port)
    print(f"Termination server started on port: {args.terminate_port}")

    class AlgorithmHttpServer:
        def __init__(self, port=9999):
            self.port = port
            self.server_thread = None
            
        def start(self):
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            return self
            
        def _run_server(self):
            from flask import Flask, request, jsonify
            app = Flask("AlgorithmHttpServer")
            
            @app.route('/terminate', methods=['POST'])
            def terminate():
                print("Received HTTP termination request, shutting down...")
                threading.Thread(target=lambda: (time.sleep(1), os._exit(0))).start()
                return jsonify({"status": "success"})
                
            app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
    
    def get_terminator(port=9999):
        http_server = AlgorithmHttpServer(port=port)
        http_server.start()
        return http_server
        
    def register_current_process(process_number):
        print(f"Process registered with number: {process_number}")
    
    process_number = args.name if hasattr(args, 'name') else os.path.basename(__file__).split('.')[0]
    terminator = get_terminator(port=args.terminate_port if hasattr(args, 'terminate_port') else 9999)
    register_current_process(process_number)
    print(f"已启动进程终止HTTP服务，进程编号: {process_number}")

    main()
