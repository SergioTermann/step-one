import numpy as np
import socket
import json
import os
import time
from datetime import datetime


def send_data_to_server(server_ip, server_port, data):
    """
    将数据发送到指定服务器

    参数:
        server_ip: 服务器IP地址
        server_port: 服务器端口号
        data: 要发送的数据（字符串）
    """
    try:
        # 创建socket对象
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 设置超时时间
        client_socket.settimeout(10)

        # 连接服务器
        client_socket.connect((server_ip, server_port))

        # 发送数据长度
        data_bytes = data.encode('utf-8')
        length = len(data_bytes)
        client_socket.send(f"{length:<10}".encode('utf-8'))

        # 发送数据
        client_socket.send(data_bytes)

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
    # 获取当前时间
    current_time = datetime.now()

    # 从JSON文件加载算法数据
    try:
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'algorithm_data.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # 更新动态信息
        for algo_name in metadata:
            metadata[algo_name]["update_time"] = current_time.strftime("%Y/%m/%d %H:%M")
            metadata[algo_name]["system_info"] = {
                "local_ip": get_local_ip(),
                "script_name": filename
            }

        return json.dumps(metadata, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"读取算法数据文件时出错: {e}")
        # 如果文件读取失败，返回一个基本的元数据结构
        return json.dumps({"error": f"无法加载算法元数据: {str(e)}"}, ensure_ascii=False)


class AlgInfoProxy_YOLO:
    def __init__(self, initial_state, initial_covariance, process_noise, measurement_noise):
        self.state = initial_state
        self.covariance = initial_covariance
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise

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


def generate_random_scenarios(num_scenarios=5, seed=None):
    if seed is not None:
        np.random.seed(seed)

    scenarios = []
    for _ in range(num_scenarios):
        # 生成随机初始状态和噪声参数
        initial_speed = np.random.uniform(5.0, 15.0)
        initial_position = np.random.uniform(0.0, 50.0)

        # 随机生成控制输入和测量序列
        control_inputs = np.random.uniform(0.5, 2.0, 10)
        measurements = np.cumsum(control_inputs) + np.random.normal(0, 0.5, 10)

        scenario = {
            "initial_state": [initial_position, initial_speed],
            "initial_covariance": np.eye(2).tolist(),
            "process_noise": np.diag([0.1, 0.1]).tolist(),
            "measurement_noise": [[0.5]],
            "control_inputs": control_inputs.tolist(),
            "measurements": measurements.tolist()
        }

        scenarios.append(scenario)

    return scenarios


def AlgInfoProxy_YOLO(init_state: list, init_corn: list):
    # 获取当前脚本文件名
    current_script = os.path.basename(__file__)

    # 设置默认参数
    server_ip = '180.1.80.3'
    server_port = 8192
    num_experiments = 5

    # 生成并发送元数据
    metadata = generate_algorithm_metadata(current_script)
    send_data_to_server(server_ip, server_port, metadata)

    # 获取本地IP
    local_ip = get_local_ip()
    print(f"本机IP地址: {local_ip}")

    # 生成随机场景
    scenarios = generate_random_scenarios(num_scenarios=num_experiments, seed=42)


    # 返回最终结果
    return


if __name__ == "__main__":
    # 测试算法
    # 加入对主函数的引用
    print("算法执行结束")
