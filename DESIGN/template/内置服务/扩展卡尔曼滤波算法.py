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


def get_local_ip():
    """获取本地IP地址"""
    # 创建一个临时socket连接
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # 连接到外部地址
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    return local_ip


class HTTPStatusReporter:
    """HTTP状态上报器"""
    
    def __init__(self, server_ip='180.1.80.3', server_port=8192):
        """初始化HTTP状态上报器"""
        self.session = requests.Session()  # 创建HTTP会话
        self.session.trust_env = False  # 禁用系统代理，避免502网关问题
        self.session.headers.update({'Connection': 'close'})
        # 设置更长的连接超时和读取超时
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
        """带时间戳的日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_memory_usage(self):
        """获取当前进程内存使用率"""
        process = psutil.Process(os.getpid())
        return process.memory_percent()

    def get_cpu_usage(self):
        """获取当前进程CPU使用率"""
        process = psutil.Process(os.getpid())
        return process.cpu_percent(interval=1)

    def get_gpu_usage(self):
        """获取当前GPU使用率"""
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            return utilization.gpu
        except:
            return 0.00
    
    def build_status_message(self, algorithm_name, algorithm_info):
        """构建状态消息"""
        # 获取当前资源使用情况
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()

        # 构建完整的状态消息
        status_data = [{
            "name": algorithm_name,
            "category": algorithm_info.get("category", "内置服务"),
            "className": algorithm_info.get("class", "认知识别类"),
            "subcategory": algorithm_info.get("subcategory", "状态估计类"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "扩展卡尔曼滤波算法，用于非线性系统状态估计"),
            "ip": get_local_ip(),
            "port": algorithm_info.get("network_info", {}).get("port", 8080),
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
        """发送状态消息到服务器"""
        try:
            status_data = self.build_status_message(algorithm_name, algorithm_info)
            if status_data:
                response = self.session.post(
                    self.base_url,
                    json=status_data,
                    timeout=(15, 30),  # 连接超时15秒，读取超时30秒
                    headers={'Connection': 'close'}
                )
                
                if response.status_code == 200:
                    self.log_with_timestamp(f"状态上报成功: {algorithm_name}")
                else:
                    self.log_with_timestamp(f"状态上报失败: HTTP {response.status_code}")
                    
        except requests.exceptions.RequestException as e:
            self.log_with_timestamp(f"状态上报时发生网络错误: {e}")
        except Exception as e:
            self.log_with_timestamp(f"状态上报时发生未知错误: {e}")
    
    def periodic_report(self, algorithm_name, algorithm_info, interval):
        """定期上报状态"""
        while self.reporting:
            self.send_status_message(algorithm_name, algorithm_info)
            time.sleep(interval)
    
    def start_periodic_reporting(self, algorithm_name, algorithm_info, interval=30):
        """启动定期状态上报"""
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
        """停止状态上报"""
        if self.reporting:
            self.reporting = False
            if self.report_thread:
                self.report_thread.join(timeout=2)
            self.log_with_timestamp("已停止状态上报")


def get_memory_usage():
    """获取当前进程内存使用率"""
    process = psutil.Process(os.getpid())
    return f"{process.memory_percent():.2f}"


def get_cpu_usage():
    """获取当前进程CPU使用率"""
    process = psutil.Process(os.getpid())
    return f"{process.cpu_percent(interval=1):.2f}"


def get_gpu_usage():
    """获取当前GPU使用率"""
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    gpu_percent = utilization.gpu
    return f"{gpu_percent:.2f}"


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
    """主函数"""
    global program_running
    program_running = True
    
    parser = argparse.ArgumentParser(description='算法状态发送器')
    parser.add_argument('--server', default='127.0.0.1', help='服务器IP地址')
    parser.add_argument('--port', type=int, default=12345, help='服务器端口')
    parser.add_argument('--algo-file', default='algorithm.json', help='算法文件路径')
    parser.add_argument('--name', default='扩展卡尔曼滤波算法', help='算法名称')
    parser.add_argument('--algo-ip', default='192.168.43.3', help='算法IP地址')
    parser.add_argument('--algo-port', type=int, default=8080, help='算法服务端口')
    parser.add_argument('--interval', type=float, default=2.0, help='发送间隔(秒)')
    parser.add_argument('--count', type=int, default=0, help='发送次数(0表示无限发送)')
    parser.add_argument('--status', default='running', help='算法状态')
    parser.add_argument('--remote', action='store_true', default=True, help='是否为远程算法')
    # 添加HTTP服务器相关参数
    parser.add_argument('--http-server', default='180.1.80.3', help='远程HTTP服务器IP地址')
    parser.add_argument('--http-port', type=int, default=8192, help='远程HTTP服务器端口')

    args = parser.parse_args()
    config_param = "${SPECIAL_PARAM}"

    try:
        config_param = ast.literal_eval(config_param)
    except (SyntaxError, ValueError):
        # 如果解析失败，使用默认空字典
        config_param = {}
        print("无法解析配置参数，使用默认配置")

    if not config_param:
        print(f"无法加载算法 '{args.name}'，程序退出")
        return

    args.ip = get_local_ip()
    
    # 创建HTTP状态上报器
    http_reporter = HTTPStatusReporter(args.http_server, args.http_port)
    
    # 构建详细的算法信息
    algorithm_info = {
        "name": args.name,
        "category": "内置服务",
        "class": "滤波算法类",
        "subcategory": "卡尔曼滤波类",
        "version": "1.0",
        "creator": "system",
        "description": "扩展卡尔曼滤波算法，用于非线性系统状态估计",
        "inputs": ["状态向量", "观测向量", "控制输入"],
        "outputs": ["估计状态", "协方差矩阵"],
        "network_info": {
            "ip": args.algo_ip,
            "port": args.algo_port,
            "status": "运行中"
        }
    }

    # 初始化算法模板类
    algorithm = TemplateClass()

    # 设置信号处理器，用于捕获程序终止信号
    def signal_handler_with_http(sig, frame):
        global program_running
        print(f"\n接收到信号 {sig}，正在关闭程序...")
        program_running = False
        
        # 发送离线状态
        offline_info = algorithm_info.copy()
        offline_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.name, offline_info)
        
        # 停止HTTP状态上报
        http_reporter.stop_reporting()
        
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler_with_http)
    signal.signal(signal.SIGTERM, signal_handler_with_http)

    # 启动HTTP状态上报
    http_reporter.start_periodic_reporting(args.name, algorithm_info, args.interval)

    try:
        count = 0
        algorithm.is_running = True
        while program_running and (args.count == 0 or count < args.count):
            # 算法执行，这将设置is_running为True
            algorithm.run()

            count += 1
            if count > 20:
                algorithm.is_running = False
            if args.count > 0:
                print(f"已执行算法 {count}/{args.count} 次")
            else:
                print(f"已执行算法 {count} 次")

            # 在算法执行之间添加一些间隔
            time.sleep(args.interval / 2)
    except Exception as e:
        print(f"程序执行出错: {e}")
    finally:
        # 设置程序状态为不运行
        program_running = False

        # 发送离线状态
        offline_info = algorithm_info.copy()
        offline_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.name, offline_info)
        
        # 停止HTTP状态上报
        http_reporter.stop_reporting()

        print("程序已正常退出")



if __name__ == "__main__":
    main()