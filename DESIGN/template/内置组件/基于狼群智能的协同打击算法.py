import socket
import json
import os
from datetime import datetime
import sys
import requests
import psutil
import pynvml
import threading
import argparse
import signal
import time

# 添加http_connect.py的路径
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
from http_connect import HTTPStatusReporter


def create_result_directory():
    """创建结果存储目录"""
    base_dir = "wolf_pack_strike_results"
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

    # 生成简要报告
    report = f"""
实验报告：第 {data.get('experiment_number', 'N/A')} 次实验
=============================
本机IP地址：{data.get('local_ip', 'N/A')}
目标总数：{len(data.get('targets', []))}
打击平台数量：{data.get('n_wolves', 'N/A')}
成功打击目标数：{data.get('total_qualified', 'N/A')}
打击成功率：{data.get('success_rate', 'N/A'):.2%}

目标详细状态：
"""
    for i, target_status in enumerate(data.get('final_targets_status', [])):
        report += f"目标 {i + 1}：初始健康值 {target_status['initial_health']:.2f}, "
        report += f"最终健康值 {target_status['final_health']:.2f}, "
        report += f"伤害百分比 {target_status['damage_percentage']:.2f}%\n"

    # 生成报告文件
    report_filename = os.path.join(base_dir, f"report_{timestamp}.txt")
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"报告已保存到 {report_filename}")


# 全局变量
program_running = True


def signal_handler(sig, frame):
    """信号处理器"""
    global program_running
    print("\n收到中断信号，正在关闭程序...")
    program_running = False


def start_server(host='0.0.0.0', port=12345, remote_http_ip='180.1.80.3', remote_http_port=8192, report_interval=30):
    """启动服务器接收实验数据，集成HTTP状态上报功能"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建HTTP状态上报器
    http_reporter = HTTPStatusReporter(remote_http_ip, remote_http_port)
    
    # 算法信息
    algorithm_name = "基于狼群智能的协同打击算法"
    algorithm_info = {
        "category": "内置组件",
        "class": "协同控制类",
        "subcategory": "打击算法类",
        "version": "1.0",
        "creator": "system",
        "description": "基于狼群智能的多智能体协同打击算法",
        "inputs": [
            {"name": "target_positions", "type": "list", "description": "目标位置列表"},
            {"name": "wolf_count", "type": "int", "description": "狼群数量"},
            {"name": "attack_params", "type": "dict", "description": "攻击参数"}
        ],
        "outputs": [
            {"name": "attack_result", "type": "dict", "description": "攻击结果"},
            {"name": "success_rate", "type": "float", "description": "攻击成功率"}
        ],
        "network_info": {
            "port": port,
            "status": "空闲",
            "is_remote": False,
            "cpu_usage": f"{http_reporter.get_cpu_usage():.2f}",
            "gpu_usage": [{'usage': f"{http_reporter.get_gpu_usage():.2f}", "index": 0, "name": "GPU-0", "memory_used_mb": 10, "memory_total_mb": 100}],
            "memory_usage": f"{http_reporter.get_memory_usage():.2f}",
            "last_update_timestamp": datetime.now().isoformat(),
            "gpu_new": "",
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
                    if "协同打击算法" in parsed_data:
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
    parser = argparse.ArgumentParser(description='基于狼群智能的协同打击算法')
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
