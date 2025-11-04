
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
    def __init__(self, port=8081):
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

try:
    from terminate_service_manager import start_terminate_service, get_terminate_service
    _TERMINATE_SERVICE_AVAILABLE = True
except ImportError:
    _TERMINATE_SERVICE_AVAILABLE = False
    print("[警告] 无法导入终止服务管理器，终止服务功能将不可用")

def add_terminate_support():
    print("Termination server support added")

def get_terminator():
    return ProcessTerminator()

def register_current_process(process_number):
    print(f"Process {process_number} registered")

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
from datetime import datetime

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
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip

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
        
    def log_with_timestamp(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_memory_usage(self):
        process = psutil.Process(os.getpid())
        return round(process.memory_percent(), 2)

    def get_cpu_usage(self):
        process = psutil.Process(os.getpid())
        return round(process.cpu_percent(interval=1), 2)

    def get_gpu_usage(self):
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_percent = utilization.gpu
            return round(gpu_percent, 2)
        except Exception:
            return 0

    def build_status_message(self, algorithm_name, algorithm_info):
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()

        status_data = [{
            "name": algorithm_name,
            "category": algorithm_info.get("category", "内置服务"),
            "className": algorithm_info.get("class", "认知识别类"),
            "subcategory": algorithm_info.get("subcategory", "聚类分析类"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "K-means聚类算法，用于数据聚类分析"),
            "ip": get_local_ip(),
            "port": algorithm_info.get("network_info", {}).get("port", 8081),
            "creator": algorithm_info.get("creator", "system"),
            "network_info": {
                "status": algorithm_info.get("network_info", {}).get("status", "空闲"),
                "is_remote": algorithm_info.get("network_info", {}).get("is_remote", True),
                "cpu_usage": cpu_usage,
                "gpu_usage": [{'usage': gpu_usage, "index": 0, "name": "GPU-0", "memory_used_mb": 10, "memory_total_mb": 100}],
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
                timeout=(15, 30)
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
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    gpu_percent = utilization.gpu
    return round(gpu_percent, 2)

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
    global client, program_running, status_thread

    parser = argparse.ArgumentParser(description='算法状态发送客户端')
    parser.add_argument('--server', default='127.0.0.1', help='服务器IP地址')
    parser.add_argument('--port', type=int, default=12345, help='服务器端口')
    parser.add_argument('--file', default='algorithms.json', help='存储算法信息的JSON文件路径')
    parser.add_argument('--name', default='K_means算法', help='要加载的算法名称')
    parser.add_argument('--algo-ip', default='192.168.43.3', help='算法服务IP地址')
    parser.add_argument('--algo-port', type=int, default=8081, help='算法服务端口')
    parser.add_argument('--interval', type=float, default=2.0, help='发送间隔(秒)')
    parser.add_argument('--count', type=int, default=0, help='发送次数(0表示无限发送)')
    parser.add_argument('--status', default='running', help='算法状态')
    parser.add_argument('--remote', action='store_true', default=True, help='是否为远程算法')
    parser.add_argument('--http-server', default='180.1.80.3', help='HTTP状态上报服务器IP地址')
    parser.add_argument('--http-port', type=int, default=8192, help='HTTP状态上报服务器端口')
    parser.add_argument('--report-interval', type=int, default=30, help='HTTP状态上报间隔(秒)')
    parser.add_argument('--terminate-port', type=int, default=8081, help='终止服务端口')

    args = parser.parse_args()
    
    print("="*60)
    print(f"启动算法: {args.name}")
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
    config_param = "{'category': '内置服务', 'class': '认知识别类', 'subcategory': '聚类分析类', 'version': '1.3', 'creator': '陈五', 'create_time': '2025/1/10 09:15', 'maintainer': '陈五', 'update_time': '2025-04-07 10:13:36', 'description': 'K-means算法是一种常用的聚类分析算法，旨在将数据点分为K个簇，使得每个点都属于距离最近的簇。', 'inputs': [{'name': '惯性数据', 'symbol': 'IMU', 'type': 'double', 'dimension': '1', 'description': 'mxn'}, {'name': 'GPS数据', 'symbol': 'GPS', 'type': 'double', 'dimension': '1', 'description': 'GPS位置数据'}, {'name': '图像地址', 'symbol': 'img_path', 'type': 'int8', 'dimension': '1', 'description': '图像文件路径'}, {'name': '时间戳', 'symbol': 't', 'type': 'vector', 'dimension': '秒', 'description': '数据采集时间戳'}, {'name': '簇数量', 'symbol': 'K', 'type': 'std::vector<int>', 'dimension': '1', 'description': '期望的聚类数量'}], 'outputs': [{'name': '物体类别标签', 'symbol': 'labels', 'type': 'vector', 'dimension': '1', 'description': '识别的物体类别标签'}, {'name': '物体绝对位置', 'symbol': 'positions', 'type': 'double', 'dimension': '位置', 'description': '各物体的绝对位置坐标'}, {'name': '物体加速度', 'symbol': 'accel', 'type': 'double', 'dimension': '米每平方秒', 'description': '各物体的加速度'}, {'name': '置信度', 'symbol': 'confidence', 'type': 'vector', 'dimension': '1', 'description': '各物体识别的置信度'}], 'network_info': {'ip': '127.0.0.1', 'status': '空闲', 'is_remote': False}}"

    try:
        config_param = ast.literal_eval(config_param)
    except (SyntaxError, ValueError):
        config_param = {}
        print("无法解析配置参数，使用默认配置")

    if not config_param:
        print(f"无法加载算法 '{args.name}'，程序退出")
        return

    args.ip = get_local_ip()
    client = AlgorithmStatusClient(args.server, args.port)

    http_reporter = HTTPStatusReporter(args.http_server, args.http_port)
    
    algorithm_info = {
        "category": "内置服务",
        "class": "数据分析类",
        "subcategory": "聚类算法类",
        "version": "1.0",
        "creator": "system",
        "description": "K-means聚类算法，用于数据聚类和模式识别",
        "inputs": ["数据集", "聚类数量K"],
        "outputs": ["聚类中心", "聚类结果"],
        "network_info": {
            "port": args.algo_port,
            "status": "运行中"
        }
    }
    
    http_reporter.start_periodic_reporting(args.name, algorithm_info, args.report_interval)

    updated_info = update_algorithm_info(config_param, ip=args.algo_ip, port=args.algo_port, status="空闲")
    client.send_algorithm_info(updated_info)

    algorithm = AlgSrv_Notspecified()

    def signal_handler_with_http(sig, frame):
        global program_running
        print(f"\n接收到信号 {sig}，正在关闭程序...")
        program_running = False
        algorithm_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.name, algorithm_info)
        http_reporter.stop_reporting()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler_with_http)
    signal.signal(signal.SIGTERM, signal_handler_with_http)

    status_thread = threading.Thread(target=status_monitoring_thread, args=(client, config_param, algorithm, args), daemon=True)
    status_thread.start()

    try:
        count = 0
        algorithm.is_running = True
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
    except Exception as e:
        print(f"程序执行出错: {e}")
    finally:
        program_running = False

        algorithm_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.name, algorithm_info)
        http_reporter.stop_reporting()

        if status_thread:
            status_thread.join(timeout=2.0)

        if client:
            client.close()
        
        if _TERMINATE_SERVICE_AVAILABLE:
            print("\n[终止服务] 显示请求日志:")
            service = get_terminate_service()
            if service and service.request_log:
                service.print_logs()
            else:
                print("  没有收到终止请求")

        print("\n程序已正常退出")


if __name__ == "__main__":
    main()