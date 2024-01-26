from vertexai.preview.language_models import TextGenerationModel
import vertexai

vertexai.init(
    project='tsmccareerhack2024-icsd-grp3',
)
def get_parameters():
    return {
        "temperature": 0.3,
        "max_output_tokens": 1024,
        "top_p": .8,
        "top_k": 40,
    }

class LLMSingleton:
    def __init__(self, prompt: str, parameters: object):
        self.model = TextGenerationModel.from_pretrained("text-bison@001")
        self.prompt = prompt
        self.parameters = parameters
    
    def gen(self, data: str):
        combined_prompt = f"""
        {data}
        ---
        {self.prompt}
        """     
        response = self.model.predict(
            combined_prompt,
            **self.parameters,
        )
        return response.text
    
    def set_prompt(self, prompt: str):
        self.prompt = prompt
        return self

class LLMFactory:
    _instance: dict = {}
    
    @staticmethod
    def get_instance(task_name: str, prompt: str=None, parameters: object={}) -> LLMSingleton:
        if task_name not in LLMFactory._instance:
            if prompt is None:
                raise Exception('prompt is required')
            LLMFactory._instance[task_name] = LLMSingleton(prompt, parameters)
            
        return LLMFactory._instance[task_name]

def llm_task(task_name: str, prompt: str=None, parameters: object=get_parameters()) -> LLMSingleton:
    return LLMFactory.get_instance(task_name, prompt, parameters)

class LLM:
    AnalysisError = llm_task('analysis error', """
背景:現在有一個在Google Cloud Run上運行的應用服務。這個應用服務應該能夠穩定地處理客戶請求，並保持良好的性能。
角色:你是一位監測此應用服務的數據的AI助理。

數據類型說明：
    - 日誌訊息:包含有關應用運行狀態的信息。
    - 度量參數:包括CPU使用率、記憶體使用率、響應時間和錯誤率等指標。
數據可能包含日誌訊息及數個度量參數，或是僅包含其中一項。

任務：
1.根據給定的數據，找出出現問題的部分。
2.根據出現問題的部分，詳細描述這些問題，並提供解決這些問題的方法。

- 問題描述：[問題的具體描述]
- 可能原因：[問題可能的原因]
- 解決方案：[解決問題的建議方案]

---

嚴格使用 markdown 格式回答。
請一步一步思考，這對我的事業很重要。若回答對我有幫助，我會給予你小費。
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