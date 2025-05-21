# ai_executor/executor.py
import openai # 导入 openai 库，DashScope 兼容 OpenAI API
from logger.logger import get_logger
from config.settings import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_NAME, MODEL_PARAMS

logger = get_logger(__name__)

class AIExecutorError(Exception):
    """AI 执行器相关的自定义异常"""
    pass

class AIExecutor:
    def __init__(self):
        if not DASHSCOPE_API_KEY:
            logger.error("DASHSCOPE_API_KEY 未设置，无法初始化 AIExecutor。请检查 .env 文件。")
            raise AIExecutorError("API Key is missing.")

        # 初始化 OpenAI 客户端，指向 DashScope 兼容 API
        self.client = openai.OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL
        )
        self.model_name = MODEL_NAME
        self.model_params = MODEL_PARAMS
        logger.info(f"AIExecutor 已初始化，使用模型：{self.model_name}，Base URL：{DASHSCOPE_BASE_URL}")

    def generate_completion(self, messages: list, **kwargs) -> str:
        """
        执行大模型文本补全推理。
        Args:
            messages (list): 聊天消息列表，例如：
                             [{"role": "user", "content": "你好"}]
            **kwargs: 额外的模型参数，将覆盖 MODEL_PARAMS 中的默认值。
        Returns:
            str: 模型生成的文本回复。
        Raises:
            AIExecutorError: 模型调用失败时抛出。
        """
        merged_params = {**self.model_params, **kwargs}
        try:
            logger.info(f"正在调用模型 {self.model_name}，消息：{messages[:1]}...") # 仅记录部分消息
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **merged_params
            )
            completion_content = response.choices[0].message.content
            logger.info(f"模型调用成功，输出长度：{len(completion_content)}")
            return completion_content
        except openai.APIError as e:
            logger.error(f"大模型 API 调用失败: {e.status_code} - {e.response}", exc_info=True)
            raise AIExecutorError(f"大模型 API 错误: {e.response}") from e
        except openai.APITimeoutError as e:
            logger.error(f"大模型 API 请求超时: {e}", exc_info=True)
            raise AIExecutorError("大模型 API 请求超时") from e
        except Exception as e:
            logger.error(f"执行大模型推理时发生未知错误: {e}", exc_info=True)
            raise AIExecutorError(f"未知推理错误: {e}") from e

# 简单的测试用例（仅用于本地验证，实际应用中会有更完善的单元测试）
if __name__ == '__main__':
    # 确保 .env 文件中的 DASHSCOPE_API_KEY 已设置
    # export DASHSCOPE_API_KEY="YOUR_API_KEY"
    # export DASHSCOPE_BASE_URL="YOUR_BASE_URL" # 如果与默认值不同

    try:
        executor = AIExecutor()
        messages = [{"role": "user", "content": "用中文写一首关于春天的五言绝句"}]
        response_text = executor.generate_completion(messages, temperature=0.9)
        print("\n--- 模型生成结果 ---")
        print(response_text)
    except AIExecutorError as e:
        print(f"\n--- 错误 ---")
        print(f"AIExecutor 初始化或调用失败: {e}")
    except Exception as e:
        print(f"\n--- 未知错误 ---")
        print(f"发生未知错误: {e}")