import requests
import json


class LocalLLMClient:
    def __init__(self, base_url="http://localhost:8000"):
        """
        初始化本地大模型API客户端

        :param base_url: 本地模型API的基础URL
        """
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def generate_text(self, prompt, max_tokens=200, temperature=0.7):
        """
        生成文本的方法

        :param prompt: 输入提示词
        :param max_tokens: 生成文本的最大长度
        :param temperature: 控制生成文本的随机性
        :return: 生成的文本
        """
        endpoint = f"{self.base_url}/v1/completions"

        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                data=json.dumps(payload)
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析响应
            result = response.json()
            return result.get('choices', [{}])[0].get('text', '')

        except requests.RequestException as e:
            print(f"API调用错误: {e}")
            return None

    def chat_completion(self, messages, model="local-chat-model"):
        """
        聊天补全方法

        :param messages: 对话消息列表
        :param model: 使用的模型名称
        :return: 模型生成的回复
        """
        endpoint = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": messages
        }

        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                data=json.dumps(payload)
            )

            response.raise_for_status()

            result = response.json()
            return result.get('choices', [{}])[0].get('message', {}).get('content', '')

        except requests.RequestException as e:
            print(f"聊天API调用错误: {e}")
            return None


def main():
    # 创建本地LLM客户端实例
    client = LocalLLMClient()

    for i in range(50):
        # 文本生成示例
        print("文本生成示例:")
        text_prompt = "解释量子计算的基本原理"
        generated_text = client.generate_text(text_prompt)
        print(generated_text)

        # 聊天对话示例
        print("\n聊天对话示例:")
        chat_messages = [
            {"role": "system", "content": "你是一个有帮助的助手"},
            {"role": "user", "content": "今天天气不错啊"}
        ]
        chat_response = client.chat_completion(chat_messages)
        print(chat_response)


if __name__ == "__main__":
    main()
