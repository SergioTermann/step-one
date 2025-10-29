def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个远程地址（不需要真正连接）
        s.connect(("8.8.8.8", 80))
        # 获取本地IP地址
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


import socket
import json
import os
from datetime import datetime
import requests
import psutil
import pynvml
import threading
import argparse
import signal
import time


class HTTPStatusReporter:
    """HTTP状态上报器"""
    
    def __init__(self, server_ip='180.1.80.3', server_port=8192):
        """初始化HTTP状态上报器"""
        self.server_ip = server_ip
        self.server_port = server_port
        self.base_url = f"http://{server_ip}:{server_port}/resource/webSocketOnMessage"
        self.reporting = False
        self.report_thread = None
        # 创建session并禁用系统代理
        self.session = requests.Session()
        self.session.trust_env = False
        
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
    
    def get_local_ip(self):
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def build_status_message(self, algorithm_name, algorithm_info):
        """构建状态消息"""
        # 获取当前资源使用情况
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()

        # 构建完整的状态消息
        status_data = [{
            "name": algorithm_name,
            "category": algorithm_info.get("category", "内置组件"),
            "className": algorithm_info.get("class", "协同控制类"),
            "subcategory": algorithm_info.get("subcategory", "侦察算法类"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "基于信息素的协同侦察算法，用于多智能体协同侦察任务"),
            "ip": get_local_ip(),
            "port": algorithm_info.get("network_info", {}).get("port", 8080),
            "creator": algorithm_info.get("creator", "system"),
            "network_info": {
                "status": algorithm_info.get("network_info", {}).get("status", "空闲"),
                "is_remote": algorithm_info.get("network_info", {}).get("is_remote", False),
                "cpu_usage": cpu_usage,
                "gpu_usage": [{'usage': gpu_usage, "index": gpu_usage, "name": gpu_usage, "memory_used_mb": 10, "memory_total_mb": 100}],
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
                    headers={'Content-Type': 'application/json', 'Connection': 'close'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.log_with_timestamp(f"状态上报成功: {algorithm_name}")
                else:
                    self.log_with_timestamp(f"状态上报失败: HTTP {response.status_code}")
                    
        except Exception as e:
            self.log_with_timestamp(f"状态上报时出错: {e}")
            return True

    
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


# 全局变量
program_running = True


def signal_handler(sig, frame):
    """信号处理器"""
    global program_running
    print("\n收到中断信号，正在关闭程序...")
    program_running = False


def create_result_directory():
    """创建结果存储目录"""
    base_dir = "experiment_results"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    return base_dir


def save_experiment_result(base_dir, data):
    """保存实验结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(base_dir, f"experiment_{timestamp}.json")

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"结果已保存到 {filename}")


def start_server(host='0.0.0.0', port=12345, remote_http_ip='180.1.80.3', remote_http_port=8192, report_interval=30):
    """启动服务器接收实验数据，集成HTTP状态上报功能"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建HTTP状态上报器
    http_reporter = HTTPStatusReporter(remote_http_ip, remote_http_port)
    
    # 算法信息
    algorithm_name = "基于信息素的协同侦察算法"
    algorithm_info = {
        "category": "内置组件",
        "class": "协同控制类",
        "subcategory": "侦察算法类",
        "version": "1.0",
        "creator": "system",
        "description": "基于信息素机制的多智能体协同侦察算法",
        "inputs": [
            {"name": "target_area", "type": "dict", "description": "目标侦察区域"},
            {"name": "agent_count", "type": "int", "description": "智能体数量"},
            {"name": "pheromone_params", "type": "dict", "description": "信息素参数"}
        ],
        "outputs": [
            {"name": "reconnaissance_result", "type": "dict", "description": "侦察结果"},
            {"name": "coverage_rate", "type": "float", "description": "区域覆盖率"}
        ],
        "network_info": {
            "port": port,
            "status": "运行中"
        }
    }
    
    # 启动HTTP状态上报
    try:
        http_reporter.start_periodic_reporting(algorithm_name, algorithm_info, report_interval)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已启动HTTP状态上报服务")
    except Exception as e:
        print(f"启动HTTP状态上报失败: {e}")
    
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(5)

        print(f"服务器已启动，监听 {host}:{port}")

        # 创建结果存储目录
        base_dir = create_result_directory()

        while program_running:
            try:
                server_socket.settimeout(1.0)  # 设置超时以便检查program_running
                client_socket, address = server_socket.accept()
                print(f"接收到来自 {address} 的连接")

                # 接收数据长度
                length_data = client_socket.recv(10).decode('utf-8').strip()
                length = int(length_data)

                # 接收完整数据
                data = client_socket.recv(length).decode('utf-8')

                # 尝试解析JSON
                try:
                    parsed_data = json.loads(data)

                    # 判断是元数据还是实验数据
                    if "协同侦察算法" in parsed_data:
                        print("接收到算法元数据")
                    else:
                        print(f"接收到第 {parsed_data.get('experiment_number', 'N/A')} 次实验结果")
                        save_experiment_result(base_dir, parsed_data)

                except json.JSONDecodeError:
                    print("接收到非JSON格式数据")

                client_socket.close()

            except socket.timeout:
                continue  # 超时后继续循环检查program_running
            except Exception as e:
                if program_running:
                    print(f"处理连接时发生错误: {e}")
                    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"服务器运行出错: {e}")
    finally:
        # 发送离线状态
        try:
            offline_info = algorithm_info.copy()
            offline_info["network_info"]["status"] = "离线"
            http_reporter.send_status_message(algorithm_name, offline_info)
        except Exception as e:
            print(f"发送离线状态失败: {e}")
        
        # 停止HTTP状态上报
        http_reporter.stop_reporting()
        
        # 关闭服务器socket
        try:
            server_socket.close()
        except:
            pass
            
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 服务器已关闭")


if __name__ == "__main__":
    # 使用argparse解析命令行参数
    parser = argparse.ArgumentParser(description='基于信息素的协同侦察算法')
    parser.add_argument('--host', default='0.0.0.0', help='服务器监听地址')
    parser.add_argument('--port', type=int, default=12345, help='服务器监听端口')
    parser.add_argument('--remote_http_ip', default='180.1.80.3', help='远程HTTP服务器IP')
    parser.add_argument('--remote_http_port', type=int, default=8192, help='远程HTTP服务器端口')
    parser.add_argument('--report_interval', type=int, default=30, help='状态上报间隔(秒)')
    
    args = parser.parse_args()
    
    # 可以根据需要修改监听的IP和端口
    start_server(
        host=args.host,
        port=args.port,
        remote_http_ip=args.remote_http_ip,
        remote_http_port=args.remote_http_port,
        report_interval=args.report_interval
    )
