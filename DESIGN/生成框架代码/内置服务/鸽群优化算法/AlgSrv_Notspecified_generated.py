
# -*- coding: utf-8 -*-
import os
import sys
import argparse
import threading
import socket
import time
import signal
import json
from flask import Flask, request, jsonify


class AlgorithmHttpServer:
    def __init__(self, port=8080):
        self.app = Flask("AlgorithmHttpServer")
        self.port = port
        self.server_thread = None
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            return jsonify({
                "status": "running",
                "algorithm": os.path.basename(__file__),
                "pid": os.getpid()
            })
        
        @self.app.route('/terminate', methods=['POST'])
        def terminate():
            data = request.json
            if not data:
                return jsonify({"status": "error", "message": "请求数据为空"}), 400
            
            target_ip = data.get('target_ip')
            if not target_ip:
                return jsonify({"status": "error", "message": "缺少目标IP参数"}), 400
            
            local_ip = self.get_local_ip()
            
            if target_ip != local_ip:
                return jsonify({
                    "status": "ignored",
                    "message": f"目标IP({target_ip})不是本机IP({local_ip})，请求被忽略"
                }), 200
            
            process_number = data.get('process_number')
            if not process_number:
                return jsonify({"status": "error", "message": "缺少进程编号参数"}), 400
            
            threading.Thread(target=self._exit_process, daemon=True).start()
            return jsonify({"status": "success", "message": "正在终止进程"}), 200
                
    
    def get_local_ip(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    
    def _exit_process(self):
        print("收到终止指令，3秒后关闭进程...")
        import time
        time.sleep(3)
        os._exit(0)
    
    def start(self):
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False),
            daemon=True
        )
        self.server_thread.start()
        print(f"HTTP服务已启动在端口: {self.port}")
        return self.server_thread
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'template')
if template_dir not in sys.path:
    sys.path.insert(0, template_dir)


def get_terminator():
    return ProcessTerminator()


class ProcessTerminator:
    def __init__(self):
        self.process_number = os.getpid()
        print(f"Process terminator initialized, PID: {self.process_number}")
    
    def terminate_process(self, target_ip=None):
        local_ip = socket.gethostbyname(socket.gethostname())
        
        if target_ip and target_ip != local_ip:
            print(f"Target IP ({target_ip}) does not match local IP ({local_ip}), ignoring termination request")
            return False
        
        print(f"Terminating process {self.process_number}...")
        threading.Thread(target=self._delayed_terminate).start()
        return True
    
    def _delayed_terminate(self):
        time.sleep(1)
        os.kill(self.process_number, signal.SIGTERM)
# -*- coding: utf-8 -*-
import socket
import json
import time
import argparse
import os
import pynvml
import psutil
import numpy as np
import ast
import signal
import sys
import threading
import requests
import datetime

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
if template_dir not in sys.path:
    sys.path.insert(0, template_dir)

try:
    from terminate_service_manager import start_terminate_service, get_terminate_service
    _TERMINATE_SERVICE_AVAILABLE = True
except ImportError:
    _TERMINATE_SERVICE_AVAILABLE = False
    print("[警告] 无法导入终止服务管理器，终止服务功能将不可用")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return round(process.memory_percent(), 2)

def get_cpu_usage():
    process = psutil.Process(os.getpid())
    return round(process.cpu_percent(interval=1), 2)

def get_gpu_usage():
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_percent = utilization.gpu
        return round(gpu_percent, 2)
    except:
        return 0

class HTTPStatusReporter:
    
    def __init__(self, server_ip='180.1.80.3', server_port=8192):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({'Connection': 'close'})
        self.session.mount('http://', requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=1,
            pool_maxsize=1
        ))
        self.server_ip = server_ip
        self.server_port = server_port
        self.base_url = f"http://{server_ip}:{server_port}/resource/webSocketOnMessage"
        self.reporting = False
        self.report_thread = None
        self.running = False
        
    def log_with_timestamp(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def get_gpu_usage(self):
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_percent = utilization.gpu
            return round(gpu_percent, 2)
        except:
            return 0

    def get_memory_usage(self):
        process = psutil.Process(os.getpid())
        return round(process.memory_percent(), 2)

    def get_cpu_usage(self):
        process = psutil.Process(os.getpid())
        return round(process.cpu_percent(interval=1), 2)

    def build_status_message(self, algorithm_name, algorithm_info):
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()
        
        status_data = [{
            "name": algorithm_name,
            "category": algorithm_info.get("category", "内置服务"),
            "className": algorithm_info.get("class", "协同控制类"),
            "subcategory": algorithm_info.get("subcategory", "优化算法类"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "鸽群优化算法，用于多智能体协同优化"),
            "ip": get_local_ip(),
            "port": algorithm_info.get("network_info", {}).get("port", 8081),
            "creator": algorithm_info.get("creator", "system"),
            "network_info": {
                "status": algorithm_info.get("network_info", {}).get("status", "空闲"),
                "is_remote": algorithm_info.get("network_info", {}).get("is_remote", True),
                "cpu_usage": cpu_usage,
                "gpu_usage": [{'usage': gpu_usage, "index": 0, "name": "GPU-0", "memory_used_mb": 10, "memory_total_mb": 100}],
                "memory_usage": memory_usage,
                "last_update_timestamp": datetime.datetime.now().isoformat(),
                "gpu_new": "",
            },
        }]
        return status_data
        
    def send_status_message(self, algorithm_name, algorithm_info):
        try:
            payload = self.build_status_message(algorithm_name, algorithm_info)
            response = self.session.post(
                self.base_url,
                json=payload,
                headers={'Content-Type': 'application/json', 'Connection': 'close'},
                timeout=(15, 30)
            )
            self.log_with_timestamp(f"状态上报成功: HTTP {response.status_code}")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            self.log_with_timestamp(f"状态上报失败: {e}")
            return False
            
    def start_periodic_reporting(self, algorithm_name, algorithm_info, interval=2):
        def report_loop():
            while self.running:
                self.send_status_message(algorithm_name, algorithm_info)
                time.sleep(interval)
                
        self.running = True
        report_thread = threading.Thread(target=report_loop, daemon=True)
        report_thread.start()
        self.report_thread = report_thread
        self.log_with_timestamp(f"启动定期状态上报，间隔{interval}秒")
        return report_thread
        
    def stop_reporting(self):
        self.running = False

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
            print(f"发送算法信息时出错: {e}")
            return False

    def close(self):
        self.socket.close()

def load_algorithm_from_file(file_path, algorithm_name):
    try:
        if not os.path.exists(file_path):
            print(f"错误: 文件 '{file_path}' 不存在")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            algorithms_data = json.load(f)

        if algorithm_name not in algorithms_data:
            print(f"错误: 在文件中找不到算法 '{algorithm_name}'")
            return None

        return algorithms_data[algorithm_name]
    except json.JSONDecodeError:
        print(f"错误: 文件 '{file_path}' 不是有效的JSON格式")
        return None
    except Exception as e:
        print(f"加载算法信息时出错: {e}")
        return None

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

class AlgSrv_Notspecified:
    def __init__(self, initial_state=None, initial_covariance=None, process_noise=None, measurement_noise=None):
        if initial_state is None:
            initial_state = np.array([0.0, 0.0])
        if initial_covariance is None:
            initial_covariance = np.eye(2)
        if process_noise is None:
            process_noise = np.eye(2) * 0.01
        if measurement_noise is None:
            measurement_noise = np.array([[0.1]])

        self.state = initial_state
        self.covariance = initial_covariance
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.is_running = False

    def predict(self, control_input):
        F = np.array([[1.0, 1.0], [0.0, 1.0]])

        B = np.array([0.5, 1.0])

        self.state = F @ self.state + B * control_input

        self.covariance = F @ self.covariance @ F.T + self.process_noise

    def update(self, measurement):
        H = np.array([[1.0, 0.0]])
        kalman_gain = self.covariance @ H.T @ np.linalg.inv(H @ self.covariance @ H.T + self.measurement_noise)
        self.state = self.state + kalman_gain @ (measurement - H @ self.state)
        self.covariance = (np.eye(2) - kalman_gain @ H) @ self.covariance

    def get_state(self):
        return self.state, self.covariance

    def run(self):
        time.sleep(0.5)

program_running = True
client = None
status_thread = None

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

def signal_handler(sig, frame):
    global program_running
    program_running = False
    print("正在关闭程序...")

def status_monitoring_thread(client, config_param, algorithm, args):
    global program_running

    while program_running:
        current_status = "调用中" if algorithm.is_running else "空闲"

        updated_info = update_algorithm_info(
            config_param,
            ip=args.algo_ip,
            port=args.algo_port,
            status=current_status,
            is_remote=args.remote
        )

        if updated_info:
            client.send_algorithm_info(updated_info)

        time.sleep(args.interval)

    send_offline_status(client, config_param, args.algo_ip, args.algo_port, args.remote)

def main():
    global program_running

    parser = argparse.ArgumentParser(description='鸽群优化算法 - HTTP状态上报版本')
    parser.add_argument('--server', default='127.0.0.1', help='服务器IP地址')
    parser.add_argument('--port', type=int, default=12345, help='服务器端口')
    parser.add_argument('--file', default='algorithms.json', help='存储算法信息的JSON文件路径')
    parser.add_argument('--algorithm', default='鸽群优化算法', help='算法名称')
    parser.add_argument('--algo_ip', default=None, help='算法IP地址')
    parser.add_argument('--algo_port', type=int, default=8081, help='算法端口')
    parser.add_argument('--interval', type=int, default=2, help='状态上报间隔（秒）')
    parser.add_argument('--remote', type=ast.literal_eval, default=False, help='是否为远程算法')
    parser.add_argument('--remote_ip', default='180.1.80.3', help='远程HTTP服务器IP')
    parser.add_argument('--remote_port', type=int, default=8192, help='远程HTTP服务器端口')
    parser.add_argument('--terminate-port', type=int, default=8081, help='终止服务端口')

    args = parser.parse_args()
    
    print("="*60)
    print(f"启动算法: {args.algorithm}")
    print("="*60)
    
    if _TERMINATE_SERVICE_AVAILABLE:
        print(f"\n[启动] 正在启动终止服务在端口 {args.terminate_port}...")
        if start_terminate_service(port=args.terminate_port):
            print(f"[成功] 终止服务已启动在端口 {args.terminate_port}")
            print(f"[提示] 可通过以下方式终止此进程:")
            print(f"        POST http://localhost:{args.terminate_port}/terminate")
            print(f"        请求体: {{'port': '{os.getpid()}'}}")
            print(f"[当前PID] {os.getpid()}")
            print(f"[监听地址] 0.0.0.0:{args.terminate_port}")
        else:
            print(f"[失败] 终止服务启动失败")
    else:
        print("\n[跳过] 终止服务不可用，请检查 terminate_service_manager.py 是否存在")
    
    print("="*60 + "\n")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.algo_ip is None:
        args.algo_ip = get_local_ip()

    print(f"启动鸽群优化算法")
    print(f"算法地址: {args.algo_ip}:{args.algo_port}")
    print(f"远程服务器: {args.remote_ip}:{args.remote_port}")
    print(f"状态上报间隔: {args.interval}秒")

    http_reporter = HTTPStatusReporter(args.remote_ip, args.remote_port)
    
    algorithm_info = {
        "category": "内置服务",
        "class": "协同控制类", 
        "subcategory": "优化算法类",
        "version": "1.0",
        "creator": "system",
        "description": "鸽群优化算法，用于多目标优化问题求解",
        "inputs": [
            {"name": "目标函数", "symbol": "objective", "type": "function", "dimension": 1, "description": "待优化的目标函数"},
            {"name": "搜索空间", "symbol": "bounds", "type": "array", "dimension": 2, "description": "变量的上下界"}
        ],
        "outputs": [
            {"name": "最优解", "symbol": "best_solution", "type": "array", "dimension": 1, "description": "找到的最优解"},
            {"name": "最优值", "symbol": "best_value", "type": "float", "dimension": 1, "description": "最优解对应的函数值"}
        ],
        "network_info": {
            "port": args.algo_port,
            "status": "运行中"
        }
    }

    report_thread = http_reporter.start_periodic_reporting(args.algorithm, algorithm_info, args.interval)
    
    algorithm = AlgSrv_Notspecified()
    
    try:
        while program_running:
            algorithm.is_running = True
            algorithm.run()
            algorithm.is_running = False
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭...")
    finally:
        http_reporter.stop_reporting()
        
        algorithm_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.algorithm, algorithm_info)
        
        if _TERMINATE_SERVICE_AVAILABLE:
            print("\n[终止服务] 显示请求日志:")
            service = get_terminate_service()
            if service and service.request_log:
                service.print_logs()
            else:
                print("  没有收到终止请求")
        
        print("\n程序已安全退出")

if __name__ == "__main__":
    main()