import requests
import json
import sys


def test_status():
    print("\n[测试1] 检查服务状态...")
    try:
        response = requests.get('http://localhost:8081/status')
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.json()
    except Exception as e:
        print(f"[错误] {e}")
        return None


def test_terminate(pid):
    print(f"\n[测试2] 发送终止请求 (PID: {pid})...")
    try:
        response = requests.post(
            'http://localhost:8081/terminate',
            json={'port': str(pid)},
            headers={'Content-Type': 'application/json'}
        )
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.json()
    except Exception as e:
        print(f"[错误] {e}")
        return None


def test_logs():
    print("\n[测试3] 查询请求日志...")
    try:
        response = requests.get('http://localhost:8081/logs')
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"日志数量: {len(data.get('logs', []))}")
        for idx, log in enumerate(data.get('logs', []), 1):
            print(f"\n日志 {idx}:")
            print(f"  时间: {log['timestamp']}")
            print(f"  端点: {log['endpoint']}")
            print(f"  IP: {log['ip']}")
            print(f"  操作: {log['action']}")
            if 'target' in log:
                print(f"  目标: {log['target']}")
        return data
    except Exception as e:
        print(f"[错误] {e}")
        return None


def main():
    print("="*60)
    print("终止服务测试工具")
    print("="*60)
    
    status_data = test_status()
    if not status_data:
        print("\n[失败] 无法连接到服务，请确保服务已启动")
        return
    
    pid = status_data.get('pid')
    client_ip = status_data.get('client_ip')
    
    print(f"\n[信息] 服务进程ID: {pid}")
    print(f"[信息] 客户端IP: {client_ip}")
    
    print("\n" + "="*60)
    choice = input("\n是否要发送终止请求? (yes/no): ").strip().lower()
    
    if choice in ['yes', 'y']:
        test_terminate(pid)
        print("\n[提示] 终止信号已发送，服务进程应该会关闭")
    else:
        print("\n[取消] 未发送终止请求")
    
    test_logs()


if __name__ == "__main__":
    main()

