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


class TerminateHttpServer:
    def __init__(self, port=8080, debug=True):
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

def main():
    parser = argparse.ArgumentParser(description='HTTP终止服务器')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口')
    args = parser.parse_args()
    
    # 启动HTTP服务器
    server = None
    try:
        server = TerminateHttpServer(port=args.port)
        server_thread = server.start()
        
        logger.info(f"服务器已启动，监听端口: {server.port}")  # 使用实际启动的端口
        logger.info("使用 Ctrl+C 停止服务器")
        
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")
    finally:
        # 确保资源被正确释放
        if server and hasattr(server, 'server_thread') and server.server_thread:
            logger.info("正在清理资源...")
            try:
                server.stop()
            except Exception as e:
                logger.error(f"关闭服务器时出错: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()