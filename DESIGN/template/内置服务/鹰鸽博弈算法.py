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

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
if template_dir not in sys.path:
    sys.path.insert(0, template_dir)

try:
    from terminate_service_manager import start_terminate_service, get_terminate_service
    _TERMINATE_SERVICE_AVAILABLE = True
except ImportError:
    _TERMINATE_SERVICE_AVAILABLE = False
    print("[警告] 无法导入终止服务管理器，终止服务功能将不可用")

try:
    from http_connect import HTTPStatusReporter
except ImportError:
    HTTPStatusReporter = None
    print("[警告] 无法导入HTTPStatusReporter")

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
        return round(utilization.gpu, 2)
    except:
        return 0.00

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

        "memory_usage": f"{get_memory_usage():.2f}",
        "cpu_usage": f"{get_cpu_usage():.2f}",
        "gpu_usage": f"{get_gpu_usage():.2f}",
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
    global program_running

    parser = argparse.ArgumentParser(description='鹰鸽博弈算法 - HTTP状态上报版本')
    parser.add_argument('--algorithm', default='鹰鸽博弈算法', help='算法名称')
    parser.add_argument('--algo_ip', default=None, help='算法IP地址')
    parser.add_argument('--algo_port', type=int, default=8081, help='算法端口')
    parser.add_argument('--interval', type=int, default=2, help='状态上报间隔（秒）')
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

    print(f"启动鹰鸽博弈算法")
    print(f"算法地址: {args.algo_ip}:{args.algo_port}")
    print(f"状态上报间隔: {args.interval}秒")

    http_reporter = HTTPStatusReporter()
    
    algorithm_info = {
        "name": args.algorithm,
        "category": "内置服务",
        "className": "博弈论类", 
        "subcategory": "鹰鸽博弈",
        "version": "1.0",
        "description": "鹰鸽博弈算法，用于分析竞争策略和资源分配",
        "ip": args.algo_ip,
        "port": args.algo_port,
        "creator": "system",
    }
    
    memory_usage = get_memory_usage()
    cpu_usage = get_cpu_usage()
    gpu_usage = get_gpu_usage()
    
    status_data = [{
        "name": args.algorithm,
        "category": "内置服务",
        "className": "博弈论类",
        "subcategory": "鹰鸽博弈",
        "version": "1.0",
        "description": "鹰鸽博弈算法，用于分析竞争策略和资源分配",
        "ip": args.algo_ip,
        "port": args.algo_port,
        "creator": "system",
        "network_info": {
            "status": "空闲",
            "is_remote": True,
            "cpu_usage": f"{cpu_usage:.2f}",
            "gpu_usage": [{'usage': f"{gpu_usage:.2f}", "index": gpu_usage, "name": gpu_usage, "memory_used_mb": 10, "memory_total_mb": 100}],
            "memory_usage": f"{memory_usage:.2f}",
            "last_update_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "gpu_new": "",
        }
    }]
    
    algorithm_info["status_data"] = status_data

    try:
        algorithm_info["network_info"]["gpu_usage"] = get_gpu_usage()
    except:
        pass

    report_thread = http_reporter.start_periodic_reporting(args.algorithm, algorithm_info, args.interval)
    
    algorithm = TemplateClass()
    
    try:
        while program_running:
            algorithm.is_running = True
            algorithm.run()
            algorithm.is_running = False
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭...")
    finally:
        if HTTPStatusReporter:
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