import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from terminate_service_manager import start_terminate_service, get_terminate_service

print("="*60)
print("测试终止服务集成")
print("="*60)

print("\n[测试1] 导入终止服务管理器...")
try:
    from terminate_service_manager import start_terminate_service, get_terminate_service
    print("[成功] 终止服务管理器导入成功")
except ImportError as e:
    print(f"[失败] 导入失败: {e}")
    sys.exit(1)

print("\n[测试2] 启动终止服务...")
if start_terminate_service(port=8081):
    print("[成功] 终止服务已启动在端口 8081")
    print(f"[当前PID] {os.getpid()}")
else:
    print("[失败] 终止服务启动失败")
    sys.exit(1)

print("\n[测试3] 获取服务实例...")
service = get_terminate_service()
if service:
    print(f"[成功] 服务实例获取成功，端口: {service.port}")
else:
    print("[失败] 无法获取服务实例")

print("\n[测试4] 模拟算法运行...")
print("算法运行中...")
import time
for i in range(5):
    print(f"迭代 {i+1}/5")
    time.sleep(1)

print("\n[测试5] 显示请求日志...")
service.print_logs()

print("\n[完成] 测试成功！")
print("="*60)

