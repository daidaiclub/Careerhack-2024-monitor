import pytest
from vertexai.preview.language_models import TextGenerationModel
from genAI.llm import LLMSingleton, LLMFactory, LLM, llm_task
from genAI import llm
from unittest.mock import Mock, MagicMock

def get_parameters():
    return {
        "temperature": 0.3,
        "max_output_tokens": 1024,
        "top_p": .8,
        "top_k": 40,
    }

class TestLLMSingleton:

    @pytest.fixture
    def llm_singleton(self):
        return LLMSingleton("prompt", get_parameters())

    def test_init(self, llm_singleton):
        assert llm_singleton.prompt == "prompt"
        assert llm_singleton.parameters == get_parameters()

    def test_gen(self, llm_singleton, monkeypatch):
        class MockResponse:
            def __init__(self, text):
                self.text = text
                
        def mock_predict(combined_prompt, *args, **kwargs):
            return MockResponse("response text")

        monkeypatch.setattr(TextGenerationModel, "predict", mock_predict)

        assert llm_singleton.gen("data") == "response text"

    def test_set_prompt(self, llm_singleton):
        new_prompt = "new prompt"
        llm_singleton.set_prompt(new_prompt)
        assert llm_singleton.prompt == new_prompt

class TestLLMFactory:
    def test_get_instance(self):
        task_name = "task_name"
        prompt = "prompt"
        parameters = get_parameters()

        instance = LLMFactory.get_instance(task_name, prompt, parameters)

        assert isinstance(instance, LLMSingleton)
        assert instance.prompt == prompt
        assert instance.parameters == parameters

    def test_get_instance_same_task_name(self):
        task_name = "task_name"
        prompt = "prompt"
        parameters = get_parameters()

        instance1 = LLMFactory.get_instance(task_name, prompt, parameters)
        instance2 = LLMFactory.get_instance(task_name)

        assert instance1 == instance2
        
    def test_get_instance_for_no_prompt(self):
        task_name = "new_task_name"
        prompt = None
        parameters = get_parameters()

        with pytest.raises(Exception) as excinfo:
            LLMFactory.get_instance(task_name, prompt, parameters)
            
        assert str(excinfo.value) == "prompt is required"

def test_llm_task(monkeypatch):
    task_name = "task_name"
    prompt = "prompt"
    parameters = get_parameters()

    def mock_get_instance(task_name, prompt, parameters):
        return "instance"

    monkeypatch.setattr(LLMFactory, "get_instance", mock_get_instance)

    instance = llm_task(task_name, prompt, parameters)

    assert instance == "instance"
    
class TestLLM:
    @pytest.fixture
    def mock_llm_task(self, monkeypatch):
        def mock_llm_task_impl(task_name, prompt, parameters):
            return MagicMock(spec=LLMSingleton)
        
        monkeypatch.setattr(llm, "llm_task", mock_llm_task_impl)
        
        return mock_llm_task_impl
    
    def test_analysis_error(self, mock_llm_task):
        llm = LLM()
        assert isinstance(llm.AnalysisError, LLMSingleton)
        
    def test_check_error(self, mock_llm_task):
        llm = LLM()
        assert isinstance(llm.CheckError, LLMSingleton)