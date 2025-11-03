
# -*- coding: utf-8 -*-
import os
import sys
import argparse
import threading
import socket
import time
import signal
import json
import logging
from flask import Flask, request, jsonify

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('TerminateServer')


# HTTP服务类
class TerminateHttpServer:
    def __init__(self, port=8080):
        self.app = Flask("TerminateHttpServer")
        self.port = port
        self.server_thread = None
        
        # 设置Flask的日志级别
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        # 注册API路由
        @self.app.route('/status', methods=['GET'])
        def get_status():
            return jsonify({
                "status": "500",
                "server": "TerminateHttpServer",
                "pid": os.getpid()
            })
        
        @self.app.route('/terminate', methods=['POST'])
        def terminate():
            data = request.json
            if not data:
                return jsonify({"status": "500", "message": "请求数据为空"}), 500
            
            # 检查目标IP是否是本机
            target_ip = data.get('ip')
            if not target_ip:
                return jsonify({"status": "500", "message": "缺少目标IP参数"}), 500
            
            # 获取本机IP
            local_ip = self.get_local_ip()
            
            # 如果目标IP不是本机IP，不处理请求
            if target_ip != local_ip:
                return jsonify({
                    "status": "500",
                    "message": f"目标IP({target_ip})不是本机IP({local_ip})，请求被忽略"
                }), 200
            
            process_number = data.get('port')
            if not process_number:
                return jsonify({"status": "500", "message": "缺少进程编号参数"}), 500

            name = data.get('name')
            if not name:
                return jsonify({"status": "500", "message": "缺少进程编号参数"}), 500
            
            # 终止进程
            threading.Thread(target=self._exit_process, args=(process_number,), daemon=True).start()
            return jsonify({"status": "200", "message": f"正在终止进程 {process_number}"}), 200
    
    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"  # 如果获取失败，返回本地回环地址
    
    def _exit_process(self, process_number):
        """安全终止进程"""
        print(f"收到终止指令，正在终止进程 {process_number}...")
        try:
            # 尝试通过进程号终止进程
            pid = int(process_number)
            os.kill(pid, signal.SIGTERM)
            print(f"已发送终止信号到进程 {pid}")
        except ValueError:
            # 如果process_number不是数字，可能是进程名称
            print(f"进程编号 '{process_number}' 不是有效的PID，尝试通过名称查找")
            self._terminate_by_name(process_number)
        except Exception as e:
            print(f"终止进程时出错: {e}")
    
    def _terminate_by_name(self, process_name):
        """通过进程名称终止进程"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if process_name.lower() in proc.info['name'].lower():
                    print(f"找到匹配的进程: {proc.info['name']} (PID: {proc.info['pid']})")
                    os.kill(proc.info['pid'], signal.SIGTERM)
                    print(f"已发送终止信号到进程 {proc.info['pid']}")
                    return
            print(f"未找到名为 '{process_name}' 的进程")
        except Exception as e:
            print(f"通过名称终止进程时出错: {e}")
    
    def start(self):
        """启动HTTP服务"""
        max_retries = 5
        current_port = self.port
        
        # 尝试从8080开始，避开常用端口
        if current_port < 1024:
            current_port = 8080
            
        for attempt in range(max_retries):
            try:
                # 使用localhost而不是IP地址，避免权限问题
                self.server_thread = threading.Thread(
                    target=lambda: self.app.run(host='localhost', port=current_port, debug=False, use_reloader=False),
                    daemon=True
                )
                self.server_thread.start()
                self.port = current_port  # 更新实际使用的端口
                logger.info(f"HTTP终止服务已启动在端口: {current_port}")
                return self.server_thread
            except OSError as e:
                error_msg = str(e).lower()
                if "address already in use" in error_msg or "权限不允许" in error_msg or "permission denied" in error_msg:
                    # 尝试更高的端口号
                    current_port += 1000
                    logger.warning(f"端口访问受限，尝试使用更高端口: {current_port}")
                    if attempt == max_retries - 1:
                        logger.error(f"无法启动HTTP服务，已尝试 {max_retries} 次")
                        raise
                else:
                    logger.error(f"启动HTTP服务时出错: {e}")
                    raise
                    
    def stop(self):
        """停止HTTP服务"""
        if hasattr(self, 'server_thread') and self.server_thread:
            logger.info("正在关闭HTTP终止服务...")
            # Flask没有直接的停止方法，但可以通过发送SIGINT信号来模拟Ctrl+C
            if sys.platform.startswith('win'):
                # Windows平台
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.GenerateConsoleCtrlEvent(0, 0)  # 发送Ctrl+C信号
            else:
                # Unix平台
                os.kill(os.getpid(), signal.SIGINT)
            logger.info("HTTP终止服务已关闭")


def add_terminate_support():
    print("Termination server support added")


def get_terminator():
    return ProcessTerminator()


def register_current_process(process_number):
    print(f"Process {process_number} registered")


class ProcessTerminator:
    def __init__(self):
        self.process_number = os.getpid()
        print(f"Process terminator initialized, PID: {self.process_number}")
    
    def terminate_process(self, target_ip=None):
        local_ip = socket.gethostbyname(socket.gethostname())
        
        if target_ip and target_ip != local_ip:
            print(f"Target IP ({target_ip}) does not match local IP ({local_ip}), ignoring termination request")
            return False
        
        print(f"Terminating process {self.process_number}...")
        threading.Thread(target=self._delayed_terminate).start()
        return True
    
    def _delayed_terminate(self):
        time.sleep(1)
        os.kill(self.process_number, signal.SIGTERM)
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
        return round(process.memory_percent(), 2)

    def get_cpu_usage(self):
        """获取当前进程CPU使用率"""
        process = psutil.Process(os.getpid())
        return round(process.cpu_percent(interval=1), 2)

    def get_gpu_usage(self):
        """获取当前GPU使用率"""
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_percent = utilization.gpu
            return round(gpu_percent, 2)
        except Exception:
            return 0

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
            "subcategory": algorithm_info.get("subcategory", "聚类分析类"),
            "version": algorithm_info.get("version", "1.0"),
            "description": algorithm_info.get("description", "K-means聚类算法，用于数据聚类分析"),
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
                timeout=(15, 30)  # 连接超时15秒，读取超时30秒
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
    return round(process.memory_percent(), 2)


def get_cpu_usage():
    """获取当前进程CPU使用率"""
    process = psutil.Process(os.getpid())
    return round(process.cpu_percent(interval=1), 2)


def get_gpu_usage():
    """获取当前GPU使用率"""
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    gpu_percent = utilization.gpu
    return round(gpu_percent, 2)


class AlgorithmStatusClient:
    def __init__(self, server_ip='127.0.0.1', server_port=8011):
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


class AlgSrv_Notspecified:
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
    global client, program_running, status_thread

    parser = argparse.ArgumentParser(description='算法状态发送客户端')
    parser.add_argument('--server', default='180.1.80.3', help='服务器IP地址')
    parser.add_argument('--port', type=int, default=8192, help='服务器端口')
    parser.add_argument('--file', default='algorithms.json', help='存储算法信息的JSON文件路径')
    parser.add_argument('--name', default='K_means算法', help='要加载的算法名称')
    parser.add_argument('--algo-ip', default='180.1.80.244', help='算法服务IP地址')
    parser.add_argument('--algo-port', type=int, default=8080, help='算法服务端口')
    parser.add_argument('--interval', type=float, default=2.0, help='发送间隔(秒)')
    parser.add_argument('--count', type=int, default=0, help='发送次数(0表示无限发送)')
    parser.add_argument('--status', default='running', help='算法状态')
    parser.add_argument('--remote', action='store_true', default=True, help='是否为远程算法')
    # 添加HTTP状态上报相关参数
    parser.add_argument('--http-server', default='180.1.80.3', help='HTTP状态上报服务器IP地址')
    parser.add_argument('--http-port', type=int, default=8192, help='HTTP状态上报服务器端口')
    parser.add_argument('--report-interval', type=int, default=30, help='HTTP状态上报间隔(秒)')
    # 添加终止服务器支持
    parser.add_argument('--terminate-port', type=int, default=8080, help='终止服务器端口')

    args = parser.parse_args()
    config_param = "{'category': '内置服务', 'class': '认知识别类', 'subcategory': '聚类分析类', 'version': '1.3', 'creator': '陈五', 'create_time': '2025/1/10 09:15', 'maintainer': '陈五', 'update_time': '2025-04-07 10:13:36', 'description': 'K-means算法是一种常用的聚类分析算法，旨在将数据点分为K个簇，使得每个点都属于距离最近的簇。', 'inputs': [{'name': '惯性数据', 'symbol': 'IMU', 'type': 'double', 'dimension': '1', 'description': 'mxn'}, {'name': 'GPS数据', 'symbol': 'GPS', 'type': 'double', 'dimension': '1', 'description': 'GPS位置数据'}, {'name': '图像地址', 'symbol': 'img_path', 'type': 'int8', 'dimension': '1', 'description': '图像文件路径'}, {'name': '时间戳', 'symbol': 't', 'type': 'vector', 'dimension': '秒', 'description': '数据采集时间戳'}, {'name': '簇数量', 'symbol': 'K', 'type': 'std::vector<int>', 'dimension': '1', 'description': '期望的聚类数量'}], 'outputs': [{'name': '物体类别标签', 'symbol': 'labels', 'type': 'vector', 'dimension': '1', 'description': '识别的物体类别标签'}, {'name': '物体绝对位置', 'symbol': 'positions', 'type': 'double', 'dimension': '位置', 'description': '各物体的绝对位置坐标'}, {'name': '物体加速度', 'symbol': 'accel', 'type': 'double', 'dimension': '米每平方秒', 'description': '各物体的加速度'}, {'name': '置信度', 'symbol': 'confidence', 'type': 'vector', 'dimension': '1', 'description': '各物体识别的置信度'}], 'network_info': {'ip': '127.0.0.1', 'status': '空闲', 'is_remote': False}}"

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
    client = AlgorithmStatusClient(args.server, args.port)

    # 创建HTTP状态上报器
    http_reporter = HTTPStatusReporter(args.http_server, args.http_port)
    
    # 构建详细的算法信息
    algorithm_info = {
        "category": "内置服务",
        "class": "数据分析类",
        "subcategory": "聚类算法类",
        "version": "1.0",
        "creator": "system",
        "description": "K-means聚类算法，用于数据聚类和模式识别",
        "inputs": ["数据集", "聚类数量K"],
        "outputs": ["聚类中心", "聚类结果"],
        "network_info": {
            "port": args.algo_port,
            "status": "运行中"
        }
    }
    
    # 启动HTTP状态上报
    http_reporter.start_periodic_reporting(args.name, algorithm_info, args.report_interval)
    
    # 启动终止服务器
    terminate_server = TerminateHttpServer(port=args.terminate_port)
    terminate_server.start()
    print(f"终止服务器已启动，监听端口: {args.terminate_port}")

    # 初始化时发送空闲状态
    updated_info = update_algorithm_info(config_param, ip=args.algo_ip, port=args.algo_port, status="空闲")
    client.send_algorithm_info(updated_info)

    # 初始化算法模板类
    algorithm = AlgSrv_Notspecified()

    # 设置信号处理器，用于捕获程序终止信号
    def signal_handler_with_http(sig, frame):
        global program_running
        print(f"\n接收到信号 {sig}，正在关闭程序...")
        program_running = False
        # 发送离线状态
        algorithm_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.name, algorithm_info)
        http_reporter.stop_reporting()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler_with_http)
    signal.signal(signal.SIGTERM, signal_handler_with_http)

    # 启动状态监控线程
    status_thread = threading.Thread(target=status_monitoring_thread, args=(client, config_param, algorithm, args), daemon=True)
    status_thread.start()

    try:
        count = 0
        algorithm.is_running = True
        while program_running and (args.count == 0 or count < args.count):
            # 算法执行，这将设置is_running为True
            algorithm.run()
            # 状态监控线程会自动处理状态发送

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
        algorithm_info["network_info"]["status"] = "离线"
        http_reporter.send_status_message(args.name, algorithm_info)
        http_reporter.stop_reporting()

        # 等待状态监控线程完成
        if status_thread:
            status_thread.join(timeout=2.0)

            # 关闭客户端
        if client:
            client.close()

        print("程序已正常退出")


if __name__ == "__main__":
    # 启动终止服务器
    parser = argparse.ArgumentParser(description='临时解析器获取终止端口')
    parser.add_argument('--terminate-port', type=int, default=8080, help='终止服务器端口')
    args, _ = parser.parse_known_args()
    print(f"终止服务器端口: {args.terminate_port}")

    # 启动HTTP服务器监听8080端口
    http_server = TerminateHttpServer(port=8080)
    http_server.start()
    print(f"HTTP服务器已启动，监听端口: 8080")

    from process_terminator import get_terminator, register_current_process
    # 获取算法名称作为进程编号
    process_number = args.name if hasattr(args, 'name') else os.path.basename(__file__).split('.')[0]
    # 启动进程终止服务
    terminator = get_terminator(port=args.terminate_port if hasattr(args, 'terminate_port') else 0000)
    # 注册当前进程
    register_current_process(process_number)
    print(f"已启动进程终止HTTP服务，进程编号: {process_number}")
    
    main()