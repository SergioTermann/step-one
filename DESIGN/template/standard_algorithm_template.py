# -*- coding: utf-8 -*-
"""
标准算法模板 - 基于AlgSrv_Notspecified_generated.py倒推生成
包含完整的HTTP状态上报和UDP通信功能
"""
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
    s.connect(("8.8.8.8", 80))  # 连接到外部地址
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip


class HTTPStatusReporter:
    """HTTP状态上报器"""
    
    def __init__(self, server_ip='180.1.80.3', server_port=8192):
        """初始化HTTP状态上报器"""
        self.session = requests.Session()  # 创建HTTP会话
        self.session.trust_env = False  # 禁用系统代理，避免502网关问题
        self.session.headers.update({'Connection': 'close'})
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
        return f"{process.memory_percent():.2f}"

    def get_cpu_usage(self):
        """获取当前进程CPU使用率"""
        process = psutil.Process(os.getpid())
        return f"{process.cpu_percent(interval=1):.2f}"

    def get_gpu_usage(self):
        """获取当前GPU使用率"""
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_percent = utilization.gpu
            return f"{gpu_percent:.2f}"
        except:
            return "0.00"

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
        """发送状态消息"""
        try:
            status_data = self.build_status_message(algorithm_name, algorithm_info)

            if not status_data:
                return False

            # 发送HTTP POST请求
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
    return f"{process.memory_percent():.2f}%"


def get_cpu_usage():
    """获取当前进程CPU使用率"""
    process = psutil.Process(os.getpid())
    return f"{process.cpu_percent(interval=1):.2f}%"


def get_gpu_usage():
    """获取当前GPU使用率"""
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_percent = utilization.gpu
        return f"{gpu_percent:.2f}%"
    except:
        return "0.00%"


class AlgorithmStatusClient:
    def __init__(self, server_ip='127.0.0.1', server_port=12345):
        """初始化算法状态发送客户端"""
        self.server_ip = server_ip
        self.server_port = server_port
        print('server ip is', server_ip)
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
            print(f"发送算法信息时发生错误: {str(e)}")
            return False

    def close(self):
        """关闭socket连接"""
        self.socket.close()


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


class StandardAlgorithm:
    """标准算法基类 - 需要被具体算法继承"""
    
    def __init__(self):
        self.is_running = False  # 添加运行状态标志
        self.algorithm_name = "标准算法"  # 算法名称，子类应该重写
        
    def initialize(self, **kwargs):
        """初始化算法参数 - 子类应该重写此方法"""
        pass
        
    def run(self):
        """算法执行逻辑 - 子类应该重写此方法"""
        self.is_running = True
        # 模拟算法执行
        time.sleep(0.5)
        self.is_running = False
        
    def get_result(self):
        """获取算法结果 - 子类应该重写此方法"""
        return None


# 全局变量用于跟踪程序状态
program_running = True


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


def main():
    """主函数 - 标准的算法启动流程"""
    parser = argparse.ArgumentParser(description='标准算法模板')
    parser.add_argument('--server', default='127.0.0.1', help='服务器IP地址')
    parser.add_argument('--port', type=int, default=12345, help='服务器端口')
    parser.add_argument('--name', default='标准算法', help='算法名称')
    parser.add_argument('--algo-ip', default='192.168.43.4', help='算法IP地址')
    parser.add_argument('--algo-port', type=int, default=8080, help='算法服务端口')
    parser.add_argument('--interval', type=float, default=2.0, help='发送间隔(秒)')
    parser.add_argument('--count', type=int, default=0, help='发送次数(0表示无限发送)')
    parser.add_argument('--remote', action='store_true', default=True, help='是否为远程算法')
    # 添加HTTP服务器相关参数
    parser.add_argument('--http-server', default='180.1.80.3', help='远程HTTP服务器IP地址')
    parser.add_argument('--http-port', type=int, default=8192, help='远程HTTP服务器端口')

    args = parser.parse_args()
    
    # 默认配置参数 - 具体算法应该修改这些参数
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
    
    # 创建HTTP状态上报器
    http_reporter = HTTPStatusReporter(args.http_server, args.http_port)
    
    # 构建详细的算法信息
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

    # 初始化算法实例
    algorithm = StandardAlgorithm()

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

    count = 0
    while program_running and (args.count == 0 or count < args.count):
        # 算法执行
        algorithm.run()

        count += 1
        # 模拟算法状态变化
        if count > 20:
            algorithm.is_running = False
            
        if args.count > 0:
            print(f"已执行算法 {count}/{args.count} 次")
        else:
            print(f"已执行算法 {count} 次")

        # 在算法执行之间添加一些间隔
        time.sleep(args.interval / 2)


if __name__ == "__main__":
    main()