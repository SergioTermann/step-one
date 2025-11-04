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
        self.server_ip = server_ip
        self.server_port = server_port
        self.base_url = f"http://{server_ip}:{server_port}/resource/webSocketOnMessage"
        self.reporting = False
        self.report_thread = None
        self.session = requests.Session()
        self.session.trust_env = False
        
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
            return 0.0
    
    def build_status_message(self, algorithm_name, algorithm_info):
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()

        status_data = [{
            "name": algorithm_name,
            "category": algorithm_info.get("category", "外置信息代理"),
            "className": algorithm_info.get("class", "资源分配类"),
            "subcategory": algorithm_info.get("subcategory", "拍卖机制类"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "拍卖算法，用于资源分配和任务调度"),
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
            if status_data:
                response = self.session.post(
                    self.base_url,
                    json=status_data,
                    headers={'Content-Type': 'application/json', 'Connection': 'close'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.log_with_timestamp(f"状态上报成功: {algorithm_name}")
                else:
                    self.log_with_timestamp(f"状态上报失败: HTTP {response.status_code}")
                    
        except Exception as e:
            self.log_with_timestamp(f"状态上报时出错: {e}")
            self.log_with_timestamp(f"发送状态失败，HTTP状态码: {response.status_code}")
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

class TemplateClass:
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
    parser.add_argument('--name', default='拍卖算法', help='要加载的算法名称')
    parser.add_argument('--algo-ip', default='192.168.43.3', help='算法服务IP地址')
    parser.add_argument('--algo-port', type=int, default=8080, help='算法服务端口')
    parser.add_argument('--interval', type=float, default=2.0, help='发送间隔(秒)')
    parser.add_argument('--count', type=int, default=0, help='发送次数(0表示无限发送)')
    parser.add_argument('--status', default='running', help='算法状态')
    parser.add_argument('--remote', action='store_true', default=True, help='是否为远程算法')
    parser.add_argument('--http-server', default='180.1.80.3', help='HTTP状态上报服务器IP')
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
    config_param = "${SPECIAL_PARAM}"

    try:
        config_param = ast.literal_eval(config_param)
    except (SyntaxError, ValueError):
        config_param = {}
        print("无法解析配置参数，使用默认配置")

    if not config_param:
        print(f"无法加载算法 '{args.name}'，程序退出")
        return

    args.ip = get_local_ip()
    
    http_reporter = HTTPStatusReporter(args.http_server, args.http_port)
    
    algorithm_info = {
        "category": "外置信息代理",
        "class": "资源分配类",
        "subcategory": "拍卖机制类",
        "version": "1.0",
        "creator": "system",
        "description": "拍卖算法，用于资源分配和任务调度",
        "inputs": [
            {"name": "bidders", "type": "list", "description": "竞拍者列表"},
            {"name": "items", "type": "list", "description": "拍卖物品列表"},
            {"name": "budget", "type": "float", "description": "预算限制"}
        ],
        "outputs": [
            {"name": "allocation", "type": "dict", "description": "分配结果"},
            {"name": "prices", "type": "list", "description": "成交价格"},
            {"name": "winners", "type": "list", "description": "获胜者列表"}
        ],
        "network_info": {
            "port": args.algo_port,
            "status": "运行中"
        }
    }
    
    http_reporter.start_periodic_reporting(args.name, algorithm_info, args.report_interval)
    
    def cleanup_and_exit():
        global program_running
        program_running = False
        
        offline_info = algorithm_info.copy()
        offline_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.name, offline_info)
        
        http_reporter.stop_reporting()
        
        if status_thread:
            status_thread.join(timeout=2.0)
        
        if client:
            client.close()
        
        print("程序已正常退出")
    
    def new_signal_handler(sig, frame):
        print(f"\n接收到信号 {sig}，正在退出...")
        cleanup_and_exit()
        sys.exit(0)
    
    client = AlgorithmStatusClient(args.server, args.port)

    updated_info = update_algorithm_info(config_param, ip=args.algo_ip, port=args.algo_port, status="空闲")
    client.send_algorithm_info(updated_info)

    algorithm = TemplateClass()

    signal.signal(signal.SIGINT, new_signal_handler)
    signal.signal(signal.SIGTERM, new_signal_handler)

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
        if _TERMINATE_SERVICE_AVAILABLE:
            print("\n[终止服务] 显示请求日志:")
            service = get_terminate_service()
            if service and service.request_log:
                service.print_logs()
            else:
                print("  没有收到终止请求")
        cleanup_and_exit()

if __name__ == "__main__":
    main()