from unittest.mock import MagicMock
import pytest
from genAI.cloud import CloudRunResourceManager
from genAI import cloud
from google.cloud import run_v2

@pytest.fixture
def mock_run_services_client(monkeypatch):
    mock_client = MagicMock(spec=run_v2.ServicesClient)
    monkeypatch.setattr(run_v2, 'ServicesClient', lambda: mock_client)
    return mock_client

@pytest.fixture
def mock_update_service_request(monkeypatch):
    mock_request = MagicMock()
    mock_service = MagicMock()
    mock_template = MagicMock()
    mock_container = MagicMock()
    mock_resources = MagicMock()
    
    mock_resources.limits = {
        'cpu': 'mock_cpu_value',
        'memory': 'mock_memory_value',
    }
    mock_container.resources = mock_resources
    mock_containers  = [mock_container]
    mock_template.containers = mock_containers
    mock_service.template = mock_template
    mock_request.service = mock_service
    
    monkeypatch.setattr(run_v2, 'UpdateServiceRequest', lambda service: mock_request)

@pytest.fixture
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('REGION', 'test-region')
    monkeypatch.setenv('PROJECT_ID', 'test-project-id')
    
@pytest.fixture
def resource_manager(mock_run_services_client, set_environment_variables):
    mock_service = MagicMock()
    mock_run_services_client.get_service.return_value = mock_service

    return CloudRunResourceManager('test-service')

class TestCloudRunResourceManager():
    @pytest.mark.parametrize(("value"), ["1000m", "10Gi", "1000Mi"])
    def test_parse_resource_value(self, resource_manager, value):
        assert isinstance(resource_manager._parse_resource_value(value), (int, float))
        
    @pytest.mark.parametrize(("value"), ["invalid", "1000M", "10gi", "1000mi"])
    def test_parse_resource_value(self, resource_manager, value):
        with pytest.raises(Exception) as excinfo:
            resource_manager._parse_resource_value(value)
        assert "Invalid value" in str(excinfo.value)
        
    def test_check_resource_constraints_valid(self, resource_manager):
        assert resource_manager._check_resourse_constraints('4000m', '2Gi') == True
        assert resource_manager._check_resourse_constraints('8000m', '4Gi') == True

    def test_check_resource_constraints_memory_too_small(self, resource_manager):
        with pytest.raises(Exception) as excinfo:
            resource_manager._check_resourse_constraints('4000m', '1Gi')
        assert "Memory is too small" in str(excinfo.value)

    def test_check_resource_constraints_cpu_too_small(self, resource_manager):
        with pytest.raises(Exception) as excinfo:
            resource_manager._check_resourse_constraints('1000m', '4Gi')
        assert "CPU is too small" in str(excinfo.value)
        
    def test_update_resource(self, resource_manager, mock_update_service_request, monkeypatch):
        monkeypatch.setattr(CloudRunResourceManager, "_check_resourse_constraints", lambda self, cpu, memory: True)
        
        resource_manager.update_resouce('4000m', '2Gi')

        resource_manager.client.get_service.assert_called_once()
        resource_manager.client.update_service.assert_called_once()

    def test_get_resource(self, resource_manager):
        resource_manager.get_resource()
        
        resource_manager.client.get_service.assert_called_once()