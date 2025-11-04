import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from terminate_service_manager import start_terminate_service, get_terminate_service


def my_algorithm():
    print("算法正在运行...")
    for i in range(100):
        print(f"迭代 {i+1}/100")
        time.sleep(1)


def main():
    print("="*60)
    print("算法启动示例")
    print("="*60)
    
    print("\n[1] 启动终止服务...")
    if start_terminate_service(port=8081, allowed_ips=None):
        print("[成功] 终止服务已启动在 8081 端口")
        print("[提示] 可以通过 POST http://localhost:8081/terminate 来终止此进程")
        print(f"[当前PID] {os.getpid()}\n")
    else:
        print("[失败] 终止服务启动失败")
        return
    
    print("[2] 开始执行算法...")
    try:
        my_algorithm()
    except KeyboardInterrupt:
        print("\n[用户中断] 算法被手动停止")
    finally:
        service = get_terminate_service()
        print("\n[3] 显示请求日志:")
        service.print_logs()


if __name__ == "__main__":
    main()

