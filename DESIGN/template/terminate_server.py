# -*- coding: utf-8 -*-
import os
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request

class TerminateServer:
    def __init__(self):
        self.app = Flask("TerminateServer")
        self.server_thread = None
        
        @self.app.route('/terminate', methods=['POST'])
        def terminate_handler():
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 收到终止指令，正在安全关闭...")
            threading.Thread(target=self._exit_process).start()
            return jsonify({"status": "success", "message": "终止信号已接收"}), 200
    
    def _exit_process(self):
        time.sleep(1)
        os._exit(0)
    
    def start(self, port=8081):
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False),
            daemon=True
        )
        self.server_thread.start()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 终止指令监听服务已启动在端口: {port}")

def add_terminate_support(parser=None):
    if parser:
        parser.add_argument('--terminate-port', type=int, default=8081, help='终止服务监听端口')
        args = parser.parse_args()
        port = args.terminate_port
    else:
        port = 8081
        
    terminate_server = TerminateServer()
    terminate_server.start(port=port)
    return terminate_server
