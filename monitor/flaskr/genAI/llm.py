""" Language Model Manager """

import time
import vertexai
from vertexai.preview.language_models import TextGenerationModel

vertexai.init(
    project='tsmccareerhack2024-icsd-grp3',
)

def get_default_parameters():
    """
    Returns a dictionary of default parameters for the AI model.

    Returns:
        dict: A dictionary containing the default parameters.
    """
    return {
        "temperature": 0.3,
        "max_output_tokens": 1024,
        "top_p": .8,
        "top_k": 40,
    }

class LLMSingleton:
    """
    Singleton class for managing a single instance of TextGenerationModel.
    """

    def __init__(self, prompt: str, parameters: object):
        """
        Initializes an instance of LLMSingleton.

        Args:
            prompt (str): The prompt to be used for text generation.
            parameters (object): The parameters to be passed to the text generation model.
        """
        self.model = TextGenerationModel.from_pretrained("text-bison@001")
        self.prompt = prompt
        self.parameters = parameters

    def gen(self, data: str):
        """
        Generates text based on the given data and the prompt.

        Args:
            data (str): The data to be used for text generation.

        Returns:
            str: The generated text.
        """
        combined_prompt = f"""
        {data}
        ---
        {self.prompt}
        """
        try:
            response = self.model.predict(
                combined_prompt,
                **self.parameters,
            )
        except Exception:
            time.sleep(50)
            response = self.model.predict(
                combined_prompt,
                **self.parameters,
            )

        return response.text

    def set_prompt(self, prompt: str):
        """
        Sets a new prompt for text generation.

        Args:
            prompt (str): The new prompt to be set.

        Returns:
            LLMSingleton: The LLMSingleton instance with the updated prompt.
        """
        self.prompt = prompt
        return self

class LLMFactory:
    """
    Factory class for creating and managing instances of LLMSingleton.
    """

    _instance: dict = {}

    @staticmethod
    def get_instance(task_name: str, parameters: object, prompt: str=None) -> LLMSingleton:
        """
        Get an instance of LLMSingleton for the given task_name.

        Args:
            task_name (str): The name of the task.
            prompt (str, optional): The prompt for the LLMSingleton instance. Defaults to None.
            parameters (object, optional): Additional parameters for the LLMSingleton instance.

        Returns:
            LLMSingleton: The instance of LLMSingleton for the given task_name.
        
        Raises:
            ValueError: If prompt is None.
        """
        if task_name not in LLMFactory._instance:
            if prompt is None:
                raise ValueError('prompt is required')
            LLMFactory._instance[task_name] = LLMSingleton(prompt, parameters)

        return LLMFactory._instance[task_name]

def llm_task(task_name: str, prompt: str=None, parameters: object=None) -> LLMSingleton:
    """
    Create an instance of LLMSingleton for the specified task.

    Args:
        task_name (str): The name of the task.
        prompt (str, optional): The prompt for the task. Defaults to None.
        parameters (object, optional): The parameters for the task. 
            Defaults to get_default_parameters().

    Returns:
        LLMSingleton: An instance of LLMSingleton for the specified task.
    """
    if parameters is None:
        parameters = get_default_parameters()
    return LLMFactory.get_instance(
        task_name=task_name,
        prompt=prompt,
        parameters=parameters)

class LLM:
    """ 
    Large Language Model (LLM) for generating text.
    """
    AnalysisError = llm_task('analysis error',
                             """
背景：目前在 Google Cloud Run 上運行的一款應用服務，本應能穩定處理客戶請求並維持優異性能。然而，最近發現一些指標異常，需要進行分析和處理。

角色：你是一位專門監控此應用服務的 AI 助理。

數據類型說明：
- 日誌訊息：提供有關應用運行狀態的信息。
- 度量參數：涵蓋 CPU 使用率、記憶體使用率、響應時間及錯誤率等。

數據分析任務：
1. 分析數據，辨識出以下異常指標：
   - Container Startup Latency (ms)
   - Instance Count (active) 大於 2
   - Request Count (4xx) 大於 5
   - Request Count (5xx) 大於 5
   - Container CPU Utilization (%) 大於 60
   - Container Memory Utilization (%) 大於 60
2. 在問題描述中，對問題提出具體描述，並用列點的形式呈現，並在問題描述的最後進行問題的總結。

任務輸出格式：
- 問題描述：[針對特定異常指標的具體描述]
- 可能原因：[該異常指標可能的原因]
- 解決方案：[針對該異常指標的建議解決方案]
                             """)
    CheckError = llm_task('check error', """
背景:現在有一個在Google Cloud Run上運行的應用服務。這個應用服務應該能夠穩定地處理客戶請求，並保持良好的性能。
角色:你是一位監測此應用服務的數據的AI助理。
    數據類型說明：
    - 日誌訊息:包含有關應用運行狀態的信息。
    - 度量參數:包括CPU使用率、記憶體使用率、響應時間和錯誤率等指標。
    數據可能包含日誌訊息及數個度量參數，或是僅包含其中一項。
任務：
    1.根據給定的數據，分析這些數據來判斷系統是否發生問題。
        - 如果系統沒有發生問題，回答: 0
        - 如果系統有發生問題，回答: 1
    
    請以以上格式回答。
""")


#  """
# 背景:現在有一個在Google Cloud Run上運行的應用服務。這個應用服務應該能夠穩定地處理客戶請求，並保持良好的性能。
# 角色:你是一位監測此應用服務的數據的AI助理。

# 數據類型說明：
#     - 日誌訊息:包含有關應用運行狀態的信息。
#     - 度量參數:包括CPU使用率、記憶體使用率、響應時間和錯誤率等指標。
# 數據可能包含日誌訊息及數個度量參數，或是僅包含其中一項。

# 任務：
# 1.根據給定的數據，找出出現問題的部分。
# 2.根據出現問題的部分，詳細描述這些問題，並提供解決這些問題的方法。

# - 問題描述：[問題的具體描述]
# - 可能原因：[問題可能的原因]
# - 解決方案：[解決問題的建議方案]

# ---

# 嚴格使用 markdown 格式回答。
# 請一步一步思考，這對我的事業很重要。若回答對我有幫助，我會給予你小費。
# """