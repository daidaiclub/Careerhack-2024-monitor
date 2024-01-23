from vertexai.preview.language_models import TextGenerationModel

def get_parameters():
    return {
        "temperature": 0.1,
        "max_output_tokens": 1024,
        "top_p": .8,
        "top_k": 40,
    }

def gen_solution(logs: str, data: str):

    parameters = get_parameters()
    model = TextGenerationModel.from_pretrained("text-bison@001")

    prompt = """
    背景:現在有一個在Google Cloud Run上運行的應用服務。這個應用服務應該能夠穩定地處理客戶請求，並保持良好的性能。
    角色:你是一位監測此應用服務的數據的AI助理。
        數據類型說明：
        - 日誌訊息:包含有關應用運行狀態的信息。
        - 度量參數:包括CPU使用率、記憶體使用率、響應時間和錯誤率等指標。
        數據可能包含日誌訊息及數個度量參數，或是僅包含其中一項。
    任務：
        1.根據給定的數據，找出出現問題的部分。
        2.根據出現問題的部分，詳細描述這些問題，並提供解決這些問題的方法。
            a. 問題描述：[問題的具體描述]
            b. 可能原因：[問題可能的原因]
            c. 解決方案：[解決問題的建議方案]
        
        請以以上格式回答。
    """

    # combined_prompt = f"{prompt}\n數據:\n{logs}"
    
    logs_prompt = f"""
        後端 日誌訊息:
        {logs}
        
    """
    
    data_prompt = f"""
        度量參數 metrics:
        {data}
        
    """
    
    combined_prompt = f"""
        {logs_prompt if logs else ''}
        {data_prompt if data else ''}     
        ---
        {prompt}
    """

    response = model.predict(
        combined_prompt,
        **parameters,
    )

    print(f"Response from Model: \n{response.text}")


def check_abnormalities(logs: str):
    parameters = {
        "temperature": 0.8,
        # "max_output_tokens": 1024,
        "top_p": .8,
        "top_k": 40,
        # "logprobs": 1,
        "candidate_count": 3
    }
    model = TextGenerationModel.from_pretrained("text-bison@001")

    prompt = """
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
    """

    # combined_prompt = f"{prompt}\n數據:\n{logs}"
    combined_prompt = f"數據:\n{logs}\n\n\n{prompt}"

    response = model.predict(
        # prompt,
        combined_prompt,
        **parameters,
    )

    print(f"Response from Model: \n{response.text}")