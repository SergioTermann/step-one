import numpy as np
import matplotlib.pyplot as plt
import socket
import os
import json
from datetime import datetime
from mpl_toolkits.mplot3d import Axes3D
import time
import requests
import psutil
import pynvml
import threading
import argparse
import signal


def get_local_ip():
    """获取本地IP地址"""
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个远程地址（不会实际发送数据）
        s.connect(("8.8.8.8", 80))
        # 获取本地IP地址
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


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
        except:
            return "0.00%"
    
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
            "subcategory": algorithm_info.get("subcategory", "编队控制类"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "一致性编队算法，用于多智能体系统编队控制"),
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
                    return True
                else:
                    self.log_with_timestamp(f"状态上报失败: HTTP {response.status_code}")
                    return False
                    
        except requests.exceptions.RequestException as e:
            self.log_with_timestamp(f"HTTP请求异常: {e}")
            return False
        except Exception as e:
            self.log_with_timestamp(f"发送状态消息时出错: {e}")
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


# 全局变量
program_running = True


def signal_handler(sig, frame):
    """信号处理器"""
    global program_running
    print("\n收到中断信号，正在关闭程序...")
    program_running = False


def send_data_to_server(server_ip, server_port, data):
    try:
        # 创建socket对象
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 连接服务器
        client_socket.connect((server_ip, server_port))

        # 发送数据
        client_socket.send(data.encode('utf-8'))

        # 关闭连接
        client_socket.close()

        print(f"数据成功发送到 {server_ip}:{server_port}")
    except Exception as e:
        print(f"发送数据时发生错误: {e}")


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


def generate_algorithm_metadata(filename):
    current_time = datetime.now()

    metadata = {
        "一致性编队算法": {
            "category": "内置服务",
            "subcategory": "协同控制类",
            "version": "1.4",
            "creator": "吴刚",
            "create_time": "2025/1/22 13:10",
            "maintainer": "吴刚",
            "update_time": current_time.strftime("%Y/%m/%d %H:%M"),
            "description": "一致性编队算法基于一致性理论，实现多无人机系统的协同编队控制，保持预定的几何构型。",
            "system_info": {
                "local_ip": get_local_ip(),
                "script_name": filename
            },
            "inputs": [
                {
                    "name": "无人机集群期望形状",
                    "symbol": "F",
                    "type": "矩阵",
                    "dimension": "nx3",
                    "description": "编队的相对位置构型"
                }
            ],
            "outputs": [
                {
                    "name": "编队位置信息",
                    "symbol": "formation_pos",
                    "type": "矩阵",
                    "dimension": "nx3",
                    "description": "编队中各无人机的位置坐标"
                }
            ]
        }
    }

    return json.dumps(metadata, ensure_ascii=False, indent=4)


def leader_follower_formation_control(agents_positions, agents_velocities, desired_formation, max_iterations=100):

    n_agents = agents_positions.shape[0]
    positions_history = [agents_positions.copy()]
    velocities_history = [agents_velocities.copy()]
    formation_errors = []

    # 参数设置
    dt = 0.1  # 时间步长
    ed = 20  # 无人机间距设置
    alpha = 2  # 一致性算法中速度系数

    # 初始化积分误差
    integral_error = np.zeros((n_agents, 3))

    # 构建无人机编队相对位置关系
    edge = np.array([
        [0, 0, 0],
        [-ed, 0, -2],
        [0, -ed, -2],
        [-ed * 2, 0, -4],
        [0, -ed * 2, -4]
    ])

    # 构建邻接矩阵 (表示无人机之间的通信拓扑)
    adjacency_matrix = np.zeros((n_agents, n_agents))
    adjacency_matrix[1, 0] = 1  # 无人机2连接到无人机1(领航者)
    adjacency_matrix[2, 0] = 1  # 无人机3连接到无人机1(领航者)
    adjacency_matrix[3, 1] = 1  # 无人机4连接到无人机2
    adjacency_matrix[4, 2] = 1  # 无人机5连接到无人机3

    # 领航者速度函数
    def get_leader_velocity(t):
        return np.array([5 / np.sqrt(2), 5 / np.sqrt(2), 1])

    for iteration in range(max_iterations):
        positions = positions_history[-1].copy()
        velocities = velocities_history[-1].copy()

        # 计算当前编队形状误差
        formation_head = positions[0]  # 以第一个无人机为编队头
        current_errors = np.zeros((n_agents, 3))
        for i in range(n_agents):
            actual_relative_position = positions[i] - formation_head
            current_errors[i] = actual_relative_position - desired_formation[i]

        # 计算整体编队形状误差
        formation_error = np.sum(np.linalg.norm(current_errors, axis=1) ** 2)
        formation_errors.append(formation_error)

        # 初始化控制输入
        u = np.zeros((n_agents, 3))

        # 更新领航者(无人机1)的速度和位置
        t = iteration * dt
        velocities[0] = get_leader_velocity(t)
        positions[0] = positions[0] + velocities[0] * dt

        # 更新跟随者的位置和速度
        for j in range(1, n_agents):
            for p in range(n_agents):
                if adjacency_matrix[j, p] == 0:
                    continue
                else:
                    # 计算位置误差(考虑编队形状)
                    error = ((positions[j] - edge[j]) - (positions[p] - edge[p]))

                    # 更新积分误差
                    integral_error[j] = integral_error[j] + error * dt

                    # 一致性控制律(包含积分作用)
                    u[j] = u[j] - adjacency_matrix[j, p] * (
                            error + alpha * (velocities[j] - velocities[p]) + 0.1 * integral_error[j])

            # 更新速度和位置
            velocities[j] = velocities[j] + u[j] * dt
            positions[j] = positions[j] + velocities[j] * dt

        # 保存位置和速度历史
        positions_history.append(positions)
        velocities_history.append(velocities)

    return np.array(positions_history), np.array(formation_errors)


def main(server_ip='192.168.1.100', server_port=12345, num_experiments=5):
    # 获取当前脚本文件名
    current_script = os.path.basename(__file__)

    # 生成并发送元数据
    metadata = generate_algorithm_metadata(current_script)
    send_data_to_server(server_ip, server_port, metadata)

    # 获取本地IP
    local_ip = get_local_ip()
    print(f"本机IP地址: {local_ip}")

    for experiment in range(num_experiments):
        print(f"\n第 {experiment + 1} 次实验...")

        # 设置参数
        np.random.seed(200 + experiment)
        n_agents = 5
        agents_positions = np.random.rand(n_agents, 3) * 10
        agents_velocities = np.zeros((n_agents, 3))

        # 定义期望编队形状 (相对于领航者的位置)
        desired_formation = np.array([
            [0, 0, 0],  # 领航者位置
            [-20, 0, -2],  # 跟随者1位置
            [0, -20, -2],  # 跟随者2位置
            [-40, 0, -4],  # 跟随者3位置
            [0, -40, -4]  # 跟随者4位置
        ])

        # 运行算法
        positions_history, formation_errors = leader_follower_formation_control(
            agents_positions, agents_velocities, desired_formation, max_iterations=200
        )

        # 准备发送的实验数据
        experiment_data = {
            "experiment_number": experiment + 1,
            "local_ip": local_ip,
            "final_positions": positions_history[-1].tolist(),
            "formation_errors": formation_errors.tolist()
        }

        # 将实验数据转换为JSON并发送
        experiment_json = json.dumps(experiment_data, ensure_ascii=False, indent=4)
        send_data_to_server(server_ip, server_port, experiment_json)

        # 等待一段时间再进行下一次实验
        time.sleep(2)


def main(server_ip='192.168.1.100', server_port=12345, num_experiments=5, 
         remote_http_ip='180.1.80.3', remote_http_port=8192, report_interval=30):
    """
    主函数，集成HTTP状态上报功能
    """
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建HTTP状态上报器
    http_reporter = HTTPStatusReporter(remote_http_ip, remote_http_port)
    
    # 获取当前脚本文件名
    current_script = os.path.basename(__file__)
    algorithm_name = "一致性编队算法"
    
    # 构建算法详细信息
    algorithm_info = {
        "category": "内置组件",
        "class": "协同控制类",
        "subcategory": "编队控制类",
        "version": "1.0",
        "creator": "system",
        "description": "基于一致性理论的多智能体编队控制算法",
        "inputs": [
            {"name": "agents_positions", "type": "numpy.ndarray", "description": "智能体初始位置"},
            {"name": "agents_velocities", "type": "numpy.ndarray", "description": "智能体初始速度"},
            {"name": "desired_formation", "type": "numpy.ndarray", "description": "期望编队形状"}
        ],
        "outputs": [
            {"name": "positions_history", "type": "numpy.ndarray", "description": "位置历史轨迹"},
            {"name": "formation_errors", "type": "list", "description": "编队误差历史"}
        ],
        "network_info": {
            "port": server_port,
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
        # 生成并发送元数据
        metadata = generate_algorithm_metadata(current_script)
        send_data_to_server(server_ip, server_port, metadata)

        # 获取本地IP
        local_ip = get_local_ip()
        print(f"本机IP地址: {local_ip}")

        for experiment in range(num_experiments):
            if not program_running:
                break
                
            print(f"\n第 {experiment + 1} 次实验...")

            # 设置参数
            np.random.seed(200 + experiment)
            n_agents = 5
            agents_positions = np.random.rand(n_agents, 3) * 10
            agents_velocities = np.zeros((n_agents, 3))

            # 定义期望编队形状 (相对于领航者的位置)
            desired_formation = np.array([
                [0, 0, 0],  # 领航者位置
                [-20, 0, -2],  # 跟随者1位置
                [0, -20, -2],  # 跟随者2位置
                [-40, 0, -4],  # 跟随者3位置
                [0, -40, -4]  # 跟随者4位置
            ])

            # 运行编队控制算法
            positions_history, formation_errors = leader_follower_formation_control(
                agents_positions, agents_velocities, desired_formation, max_iterations=100
            )

            # 发送实验结果到服务器
            experiment_data = {
                "experiment_id": experiment + 1,
                "positions_history": positions_history.tolist(),
                "formation_errors": formation_errors,
                "timestamp": datetime.now().isoformat()
            }
            send_data_to_server(server_ip, server_port, experiment_data)

            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {e}")
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
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 程序已退出")


if __name__ == "__main__":
    # 使用argparse解析命令行参数
    parser = argparse.ArgumentParser(description='一致性编队算法')
    parser.add_argument('--server_ip', default='192.168.1.100', help='服务器IP地址')
    parser.add_argument('--server_port', type=int, default=12345, help='服务器端口')
    parser.add_argument('--num_experiments', type=int, default=5, help='实验次数')
    parser.add_argument('--remote_http_ip', default='180.1.80.3', help='远程HTTP服务器IP')
    parser.add_argument('--remote_http_port', type=int, default=8192, help='远程HTTP服务器端口')
    parser.add_argument('--report_interval', type=int, default=30, help='状态上报间隔(秒)')
    
    args = parser.parse_args()
    
    main(
        server_ip=args.server_ip,
        server_port=args.server_port,
        num_experiments=args.num_experiments,
        remote_http_ip=args.remote_http_ip,
        remote_http_port=args.remote_http_port,
        report_interval=args.report_interval
    )
