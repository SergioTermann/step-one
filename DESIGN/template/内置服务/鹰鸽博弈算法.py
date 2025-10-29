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
# 导入HTTP状态上报器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
import requests
from requests.adapters import HTTPAdapter
from http_connect import HTTPStatusReporter

def get_local_ip():
    """获取本地IP地址"""
    try:
        # 创建一个临时socket连接
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # 连接到外部地址
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"  # 如果获取失败，返回本地回环地址


def get_memory_usage():
    """获取当前进程内存使用率"""
    process = psutil.Process(os.getpid())
    return process.memory_percent()


def get_cpu_usage():
    """获取当前进程CPU使用率"""
    process = psutil.Process(os.getpid())
    return process.cpu_percent(interval=1)


def get_gpu_usage():
    """获取当前GPU使用率"""
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        return utilization.gpu
    except:
        return 0.00


class AlgorithmStatusClient:
    def __init__(self, server_ip='127.0.0.1', server_port=12345):
        """初始化算法状态发送客户端"""
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_algorithm_info(self, algorithm_info):
        """发送算法信息到注册服务器"""
        try:
            # 将算法信息转换为JSON字符串
            data = json.dumps(algorithm_info, ensure_ascii=False).encode('utf-8')

            # 发送数据
            self.socket.sendto(data, (self.server_ip, self.server_port))
            print(f"已发送算法 '{algorithm_info.get('name', '未命名')}' 的信息到 {self.server_ip}:{self.server_port}")
            return True
        except Exception as e:
            print(f"发送算法信息时出错: {e}")
            return False

    def close(self):
        """关闭socket连接"""
        self.socket.close()


def load_algorithm_from_file(file_path, algorithm_name):
    """从文件中加载指定名称的算法信息"""
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
    """更新算法信息，添加网络状态信息"""
    if not algorithm_info:
        return None

        # 更新时间戳为当前时间
    algorithm_info["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # 添加网络信息
    algorithm_info["network_info"] = {
        # 网络和运行时信息
        "ip": ip,
        "port": port,
        "status": status,

        # 资源使用情况 - 调用您已有的函数
        "memory_usage": get_memory_usage(),
        "cpu_usage": get_cpu_usage(),
        "gpu_usage": get_gpu_usage(),
        "is_remote": is_remote
    }

    return algorithm_info


class TemplateClass:
    def __init__(self, initial_state=None, initial_covariance=None, process_noise=None, measurement_noise=None):
        # 为了兼容性添加默认参数
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
        self.is_running = False  # 添加运行状态标志

    def predict(self, control_input):
        # 状态转移矩阵 (假设简单的匀速运动模型)
        F = np.array([[1.0, 1.0], [0.0, 1.0]])

        # 控制输入矩阵 (假设控制输入直接影响加速度)
        B = np.array([0.5, 1.0])  # 对于位置和速度的影响

        # 预测状态
        self.state = F @ self.state + B * control_input

        # 预测协方差
        self.covariance = F @ self.covariance @ F.T + self.process_noise

    def update(self, measurement):
        # 测量矩阵 (假设直接测量位置)
        H = np.array([[1.0, 0.0]])
        kalman_gain = self.covariance @ H.T @ np.linalg.inv(H @ self.covariance @ H.T + self.measurement_noise)
        self.state = self.state + kalman_gain @ (measurement - H @ self.state)
        self.covariance = (np.eye(2) - kalman_gain @ H) @ self.covariance

    def get_state(self):
        return self.state, self.covariance

    def run(self):
        # 算法执行代码...
        # 这里可以添加实际的算法逻辑
        time.sleep(0.5)  # 模拟算法执行

    # 全局变量用于跟踪程序状态


program_running = True
client = None
status_thread = None


def send_offline_status(client, algorithm_info, algo_ip, algo_port, is_remote):
    """发送离线状态"""
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
    """处理程序终止信号"""
    global program_running
    program_running = False
    print("正在关闭程序...")


def status_monitoring_thread(client, config_param, algorithm, args):
    """状态监控线程，负责根据算法运行状态更新和发送状态信息"""
    global program_running

    while program_running:
        # 根据算法运行状态确定状态信息
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

        # 程序结束前发送离线状态
    send_offline_status(client, config_param, args.algo_ip, args.algo_port, args.remote)


def main():
    global program_running

    parser = argparse.ArgumentParser(description='鹰鸽博弈算法 - HTTP状态上报版本')
    parser.add_argument('--algorithm', default='鹰鸽博弈算法', help='算法名称')
    parser.add_argument('--algo_ip', default=None, help='算法IP地址')
    parser.add_argument('--algo_port', type=int, default=8080, help='算法端口')
    parser.add_argument('--interval', type=int, default=30, help='状态上报间隔（秒）')

    args = parser.parse_args()

    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 如果没有指定算法IP，使用本地IP
    if args.algo_ip is None:
        args.algo_ip = get_local_ip()

    print(f"启动鹰鸽博弈算法")
    print(f"算法地址: {args.algo_ip}:{args.algo_port}")
    print(f"状态上报间隔: {args.interval}秒")

    # 创建HTTP状态上报器
    http_reporter = HTTPStatusReporter()
    
    # 构建算法信息
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
    
    # 获取当前资源使用情况
    memory_usage = get_memory_usage()
    cpu_usage = get_cpu_usage()
    gpu_usage = get_gpu_usage()
    
    # 构建完整的状态消息
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
            "cpu_usage": cpu_usage,
            "gpu_usage": [{'usage': gpu_usage, "index": gpu_usage, "name": gpu_usage, "memory_used_mb": 10, "memory_total_mb": 100}],
            "memory_usage": memory_usage,
            "last_update_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "gpu_new": "",
        }
    }]
    
    # 将状态数据添加到算法信息中
    algorithm_info["status_data"] = status_data

    try:
        # 添加GPU使用率（如果可用）
        algorithm_info["network_info"]["gpu_usage"] = get_gpu_usage()
    except:
        pass

    # 启动定期状态上报
    report_thread = http_reporter.start_periodic_reporting(args.algorithm, algorithm_info, args.interval)
    
    # 创建算法实例
    algorithm = TemplateClass()
    
    try:
        # 主算法循环
        while program_running:
            algorithm.is_running = True
            algorithm.run()  # 执行算法逻辑
            algorithm.is_running = False
            time.sleep(1)  # 短暂休息
            
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭...")
    finally:
        # 停止状态上报
        http_reporter.stop_reporting()
        
        # 发送最终的离线状态
        algorithm_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.algorithm, algorithm_info)
        
        print("程序已安全退出")


if __name__ == "__main__":
    main()