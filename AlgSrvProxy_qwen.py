import socket
import json
import threading
import time

# 配置
SERVER_IP = '180.1.80.241'  # 你的IP地址
SERVER_PORT = 5555
BUFFER_SIZE = 8192  # 消息缓冲区大小
TIMEOUT = 30  # 接收超时时间(秒)

# 用于重组分段消息
message_buffer = {}
message_lock = threading.Lock()


def receive_messages(client_socket):
    """接收来自服务器的消息"""
    complete_responses = {}  # 存储完整响应

    try:
        while True:
            try:
                # 接收数据
                data, addr = client_socket.recvfrom(BUFFER_SIZE)

                try:
                    # 尝试解析JSON数据
                    response_data = json.loads(data.decode('utf-8'))

                    # 检查是否是分段消息
                    if "chunk" in response_data:
                        chunk = response_data["chunk"]
                        part = response_data["part"]
                        total = response_data["total"]
                        is_last = response_data["is_last"]

                        # 生成唯一的消息ID (使用接收时间)
                        msg_time = time.time()
                        msg_id = f"{addr[0]}:{addr[1]}:{int(msg_time)}"

                        with message_lock:
                            # 初始化消息缓冲区(如果不存在)
                            if msg_id not in message_buffer:
                                message_buffer[msg_id] = {
                                    "parts": {},
                                    "total": total,
                                    "last_update": time.time()
                                }

                            # 添加新的部分
                            message_buffer[msg_id]["parts"][part] = chunk
                            message_buffer[msg_id]["last_update"] = time.time()

                            # 检查消息是否完整
                            if len(message_buffer[msg_id]["parts"]) == total:
                                # 重组完整消息
                                complete_msg = ""
                                for i in range(1, total + 1):
                                    complete_msg += message_buffer[msg_id]["parts"][i]

                                # 显示完整消息
                                print("\n大模型响应:")
                                print("-" * 50)
                                print(complete_msg)
                                print("-" * 50)
                                print("输入消息: ", end="", flush=True)

                                # 清理缓冲区
                                del message_buffer[msg_id]
                    else:
                        # 不是JSON或不包含预期字段，直接显示
                        print("\n服务器消息:", data.decode('utf-8'))
                        print("输入消息: ", end="", flush=True)

                except json.JSONDecodeError:
                    # 不是JSON格式，可能是简单的确认消息
                    print("\n服务器消息:", data.decode('utf-8'))
                    print("输入消息: ", end="", flush=True)

            except socket.timeout:
                # 检查并清理过期的消息片段
                current_time = time.time()
                with message_lock:
                    expired_messages = []
                    for msg_id, msg_data in message_buffer.items():
                        if current_time - msg_data["last_update"] > TIMEOUT:
                            expired_messages.append(msg_id)

                    for msg_id in expired_messages:
                        del message_buffer[msg_id]
                        print(f"\n警告: 消息 {msg_id} 接收超时，部分内容可能丢失")
                        print("输入消息: ", end="", flush=True)

    except Exception as e:
        print(f"\n接收消息时出错: {str(e)}")


def main():
    """主客户端函数"""
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(5)  # 设置接收超时

    try:
        print(f"准备与服务器 {SERVER_IP}:{SERVER_PORT} 通信")

        # 开始接收线程
        receive_thread = threading.Thread(target=receive_messages, args=(client,))
        receive_thread.daemon = True
        receive_thread.start()

        # 发送测试消息
        test_message = "连接测试"
        client.sendto(test_message.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        print("已发送连接测试消息")

        # 主循环，发送消息
        while True:
            message = input("输入消息: ")
            if message.lower() == 'exit':
                break

            # 发送消息
            client.sendto(message.encode('utf-8'), (SERVER_IP, SERVER_PORT))
            print("消息已发送，等待响应...")

    except KeyboardInterrupt:
        print("\n客户端关闭中...")
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        client.close()


if __name__ == "__main__":
    main()