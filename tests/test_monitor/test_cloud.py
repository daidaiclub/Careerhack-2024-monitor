from datetime import datetime, timedelta
from unittest.mock import MagicMock
import pytest

from google.cloud import run_v2
from monitor.flaskr.genAI.cloud import CloudRunResourceManager, UntilNowTimeRange, SpecificTimeRange, CloudRun, CloudRunResource

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
    def test_parse_resource_value_success(self, resource_manager, value):
        assert isinstance(resource_manager._parse_resource_value(value), (int, float))
        
    @pytest.mark.parametrize(("value"), ["invalid", "1000M", "10gi", "1000mi"])
    def test_parse_resource_value_fail(self, resource_manager, value):
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

class TestUntilNowTimeRange:
    def test_get_minutes(self):
        time_range = UntilNowTimeRange(days=1, hours=2, minutes=30)
        assert time_range.get_minutes() == 1590

    def test_get_time_range_iso(self):
        now = datetime.now().replace(second=0, microsecond=0)
        start_time = now - timedelta(days=1, hours=2, minutes=30)
        end_time = now
        time_range = UntilNowTimeRange(days=1, hours=2, minutes=30)
        assert time_range.get_time_range_iso() == (start_time.isoformat(), end_time.isoformat())

class TestSpecificTimeRange:
    def test_get_minutes(self):
        start_time = "2022-01-01T00:00:00"
        end_time = "2022-01-01T01:30:00"
        time_range = SpecificTimeRange(start_time, end_time)
        assert time_range.get_minutes() == 90

    def test_get_time_range_iso(self):
        start_time = "2022-01-01T00:00:00"
        end_time = "2022-01-01T01:30:00"
        time_range = SpecificTimeRange(start_time, end_time)
        assert time_range.get_time_range_iso() == (start_time, end_time)

class TestCloudRun:
    def test_get_full_service_name(self):
        cloud_run = CloudRun(region='test-region', project_id='test-project-id', service_name='test-service')
        expected_name = 'projects/test-project-id/locations/test-region/services/test-service'
        assert cloud_run.get_full_service_name() == expected_name

class TestCloudRunResource:
    def test_scale_up_success(self):
        parent = MagicMock()
        resource = CloudRunResource(parent)
        resource.value = 10

        resource.scale_up()

        assert resource.value == 20
        parent.init_resource.assert_called_once()
        parent.update_resouce.assert_called_once()

    def test_scale_up_exception(self):
        parent = MagicMock()
        resource = CloudRunResource(parent)
        resource.value = 10
        parent.update_resouce.side_effect = Exception()

        resource.scale_up()

        assert resource.value == 10
        parent.init_resource.assert_called_once()
        parent.update_resouce.assert_called_once()

    def test_scale_down_success(self):
        parent = MagicMock()
        resource = CloudRunResource(parent)
        resource.value = 10

        resource.scale_down()

        assert resource.value == 5
        parent.init_resource.assert_called_once()
        parent.update_resouce.assert_called_once()

    def test_scale_down_exception(self):
        parent = MagicMock()
        resource = CloudRunResource(parent)
        resource.value = 10
        parent.update_resouce.side_effect = Exception()

        resource.scale_down()

        assert resource.value == 10
        parent.init_resource.assert_called_once()
        parent.update_resouce.assert_called_once()