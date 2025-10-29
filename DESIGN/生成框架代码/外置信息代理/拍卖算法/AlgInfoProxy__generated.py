import numpy as np
import time
import socket
import json
import os
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
    """
    生成算法元数据信息

    参数:
        filename: 当前脚本的文件名

    返回:
        JSON格式的算法元数据
    """
    current_time = datetime.now()

    metadata = {
        "无人机任务拍卖算法": {
            "category": "分布式任务分配",
            "subcategory": "多无人机协同",
            "version": "1.3",
            "creator": "AI研究团队",
            "create_time": "2025/3/20 17:45",
            "maintainer": "吴刚",
            "update_time": current_time.strftime("%Y/%m/%d %H:%M"),
            "description": "基于拍卖机制的多无人机任务动态分配算法",
            "system_info": {
                "local_ip": get_local_ip(),
                "script_name": filename
            },
            "inputs": [
                {
                    "name": "无人机参数",
                    "type": "对象",
                    "description": "无人机数量、位置、速度、电池等信息"
                },
                {
                    "name": "任务参数",
                    "type": "对象",
                    "description": "任务数量、位置、时间窗口等信息"
                }
            ],
            "outputs": [
                {
                    "name": "任务分配结果",
                    "type": "矩阵",
                    "description": "无人机与任务的分配映射"
                },
                {
                    "name": "社会福利",
                    "type": "浮点数",
                    "description": "任务分配的整体效益"
                }
            ]
        }
    }

    return json.dumps(metadata, ensure_ascii=False, indent=4)


def generate_random_scenarios(num_scenarios=5, seed=None):
    """
    生成随机任务分配场景

    参数:
        num_scenarios: 生成的场景数量
        seed: 随机数种子

    返回:
        场景列表
    """
    if seed is not None:
        np.random.seed(seed)

    scenarios = []
    for _ in range(num_scenarios):
        # 随机生成无人机和任务数量
        UAV_count = np.random.randint(3, 8)
        task_count = np.random.randint(5, 10)

        # 生成无人机参数
        UAV_positions = np.random.uniform(0, 100, (UAV_count, 2))
        UAV_speeds = np.random.uniform(8.0, 15.0, UAV_count)
        UAV_battery = np.random.uniform(800, 1500, UAV_count)

        # 生成任务参数
        task_positions = np.random.uniform(0, 100, (task_count, 2))
        task_time_required = np.random.uniform(80, 200, task_count)

        # 生成任务时间窗口
        current_time = np.random.uniform(50, 200)
        task_time_window_start = current_time + np.random.uniform(50, 150, task_count)
        task_time_window_end = task_time_window_start + np.random.uniform(100, 300, task_count)

        scenario = {
            "UAV_count": UAV_count,
            "task_count": task_count,
            "UAV_positions": UAV_positions.tolist(),
            "task_positions": task_positions.tolist(),
            "UAV_speeds": UAV_speeds.tolist(),
            "UAV_battery": UAV_battery.tolist(),
            "task_time_required": task_time_required.tolist(),
            "task_time_window_start": task_time_window_start.tolist(),
            "task_time_window_end": task_time_window_end.tolist(),
            "communication_range": np.random.uniform(100, 250),
            "current_time": current_time
        }

        scenarios.append(scenario)

    return scenarios


# 直接复制原有的类和方法定义
class InputParameters:
    # 原有的 InputParameters 类定义保持不变
    pass


class OutputResults:
    # 原有的 OutputResults 类定义保持不变
    pass


class AuctionAlgorithm:
    # 原有的 AuctionAlgorithm 类的完整定义保持不变
    pass


def main(server_ip='180.1.80.3', server_port=8192, num_experiments=5):
    """
    主执行函数，包含实验循环和网络通信

    参数:
        server_ip: 接收结果的服务器IP
        server_port: 服务器端口
        num_experiments: 实验循环次数
    """
    # 获取当前脚本文件名
    current_script = os.path.basename(__file__)

    # 生成并发送元数据
    metadata = generate_algorithm_metadata(current_script)
    send_data_to_server(server_ip, server_port, metadata)

    # 获取本地IP
    local_ip = get_local_ip()
    print(f"本机IP地址: {local_ip}")

    # 生成随机场景
    scenarios = generate_random_scenarios(num_scenarios=num_experiments, seed=42)

    for experiment, scenario in enumerate(scenarios):
        print(f"\n第 {experiment + 1} 次实验...")

        # 创建输入参数
        input_params = InputParameters(
            UAV_count=scenario['UAV_count'],
            task_count=scenario['task_count'],
            UAV_positions=np.array(scenario['UAV_positions']),
            task_positions=np.array(scenario['task_positions']),
            UAV_speeds=np.array(scenario['UAV_speeds']),
            UAV_battery=np.array(scenario['UAV_battery']),
            task_time_required=np.array(scenario['task_time_required']),
            task_time_window_start=np.array(scenario['task_time_window_start']),
            task_time_window_end=np.array(scenario['task_time_window_end']),
            communication_range=scenario['communication_range'],
            current_time=scenario['current_time']
        )

        # 执行拍卖算法
        auction = AuctionAlgorithm(input_params)
        auction.auction_process()

        # 获取结果
        results = auction.get_results()

        # 准备发送的实验数据
        experiment_data = {
            "experiment_number": experiment + 1,
            "local_ip": local_ip,
            "scenario": scenario,
            "allocation_matrix": results.allocation_matrix.tolist(),
            "payment_vector": results.payment_vector.tolist(),
            "social_welfare": results.social_welfare,
            "convergence_time": results.convergence_time,
            "conflict_flag": bool(results.conflict_flag)
        }

        # 将实验数据转换为JSON并发送
        experiment_json = json.dumps(experiment_data, ensure_ascii=False, indent=4)
        send_data_to_server(server_ip, server_port, experiment_json)

        # 等待一段时间再进行下一次实验
        time.sleep(2)


if __name__ == "__main__":
    # 默认服务器IP和端口，可根据实际情况修改
    main(server_ip='180.1.80.3', server_port=8192, num_experiments=5)
