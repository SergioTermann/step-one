import socket
import json
import os
import time
import threading


class AlgorithmStatusRegistrar:
    def __init__(self, algorithm_data_path='algorithm_data.json'):
        self.listen_port = 12345
        self.algorithm_data_path = os.path.join(os.path.dirname(__file__), algorithm_data_path)
        self.stop_event = threading.Event()

    def start_listener(self):
        """启动UDP监听服务"""
        listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listener_socket.bind(('180.1.80.3', self.listen_port))
        listener_socket.settimeout(1)  # 设置超时以便定期检查停止标志
        print(f"启动算法状态监听服务，端口：{self.listen_port}")

        while not self.stop_event.is_set():
            try:
                # 接收算法注册信号
                data, addr = listener_socket.recvfrom(65535)
                algorithm_info = json.loads(data.decode('utf-8'))

                # 处理注册信息
                self.register_algorithm(algorithm_info)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"接收数据时发生错误: {e}")

        listener_socket.close()
        print("状态监听服务已停止")

    def register_algorithm(self, algorithm_info):
        """注册算法到algorithm_data.json，对于重名算法自动添加来源后缀"""
        try:
            # 读取现有算法数据
            with open(self.algorithm_data_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}

        # 获取算法名称与IP
        original_name = algorithm_info.get('name', '未命名算法')
        ip_address = algorithm_info.get('network_info', {}).get('ip', '未知网络地址')

        # 添加时间戳
        current_timestamp = time.time()

        # 创建新的算法条目
        new_algorithm_entry = {
            "category": algorithm_info.get('category', '未分类'),
            "class": algorithm_info.get('class', '未知类'),
            "subcategory": algorithm_info.get('subcategory', '未知子类'),
            "version": algorithm_info.get('version', '1.0'),
            "creator": algorithm_info.get('creator', '未知'),
            "create_time": algorithm_info.get('create_time', ''),
            "maintainer": algorithm_info.get('maintainer', ''),
            "update_time": algorithm_info.get('update_time', ''),
            "description": algorithm_info.get('description', ''),
            "inputs": algorithm_info.get('inputs', []),
            "outputs": algorithm_info.get('outputs', []),
            "network_info": {
                "ip": ip_address,
                "port": algorithm_info.get('network_info', {}).get('port'),
                "status": algorithm_info.get('network_info', {}).get('status', '未知'),
                "last_update_timestamp": current_timestamp,  # 添加数字格式的时间戳
                "memory_usage": algorithm_info.get('network_info', {}).get('memory_usage', '未知'),
                "cpu_usage": algorithm_info.get('network_info', {}).get('cpu_usage', '未知'),
                "gpu_usage": algorithm_info.get('network_info', {}).get('gpu_usage', '未知'),
                "is_remote": algorithm_info.get('network_info', {}).get('is_remote', True)  # 内外部算法标识符
            }
        }

        # 将新算法添加到现有数据
        existing_data[original_name] = new_algorithm_entry

        # 写回文件
        with open(self.algorithm_data_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)

        print(f"成功注册算法: {original_name} 来自 {ip_address}")


def main():
    registrar = AlgorithmStatusRegistrar()

    # 启动监听线程
    listener_thread = threading.Thread(target=registrar.start_listener, daemon=True)
    listener_thread.start()

    # 保持CMD窗口运行
    print("算法状态注册服务已启动，按Ctrl+C退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("服务已停止")


if __name__ == "__main__":
    main()
