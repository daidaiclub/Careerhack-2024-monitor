from abc import abstractmethod, ABC
from datetime import datetime, timedelta
from google.cloud import run_v2
from google.cloud import monitoring_v3, logging_v2
from google.cloud.monitoring_v3.query import Query

import os
import dotenv

dotenv.load_dotenv()

# Time Range interface
class TimeRange(ABC):

    @abstractmethod
    def get_minutes(self) -> int:
        self.end_time = 0
        pass

    @abstractmethod
    def get_time_range_iso(self) -> (str, str):
        pass

class UntilNowTimeRange(TimeRange):
    def __init__(self, days: int, hours: int, minutes: int) -> None:
        self.minutes = days * 24 * 60 + hours * 60 + minutes
        self.start_time = datetime.now() - timedelta(minutes=self.minutes)
        self.end_time = datetime.now()

    def get_minutes(self) -> int:
        return self.minutes
    
    def get_time_range_iso(self) -> (str, str):
        return self.start_time.isoformat(), self.end_time.isoformat()

class SpecificTimeRange(TimeRange):
    def __init__(self, start_time: str, end_time: str) -> None:
        self.start_time = datetime.fromisoformat(start_time)
        self.end_time = datetime.fromisoformat(end_time)

    def get_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds()) // 60
    
    def get_time_range_iso(self) -> (str, str):
        return self.start_time.isoformat(), self.end_time.isoformat()

class CloudRun:
    def __init__(self, region: str, project_id: str, service_name: str) -> None:
        self.region = region
        self.project_id = project_id
        self.service_name = service_name

    def get_full_server_name(self):
        return f"projects/{self.project_id}/locations/{self.egion}/services/{self.service_name}"


class CloudRunResourceManager:
  
    def __init__(self, service_name: str):
        self.region = os.getenv('REGION', 'us-central1')
        self.project_id = os.getenv('PROJECT_ID', 'tsmccareerhack2024-icsd-grp3')
        self.service_name = service_name
        self.client = run_v2.ServicesClient()
        
    def _parse_resource_value(self, value: str):
        if value[-1] == 'm':
            return int(value[:-1]) / 1000
        elif value[-2:] == 'Gi':
            return int(value[:-2]) * 1024
        elif value[-2:] == 'Mi':
            return int(value[:-2])
        else:
            raise Exception('Invalid value')
        
    def _check_resourse_constraints(self, cpu: str, memory: str):
        cpu = self._parse_resource_value(cpu)
        memory = self._parse_resource_value(memory)
        
        cpu_to_memory_min = {4: 2048, 6: 4096, 8: 4096}
        memory_to_cpu_min = {4096: 2, 8192: 4, 16384: 6, 24576: 8}
        
        if cpu in cpu_to_memory_min and memory < cpu_to_memory_min[cpu]:
            raise Exception('Memory is too small')
        elif memory in memory_to_cpu_min and cpu < memory_to_cpu_min[memory]:
            raise Exception('CPU is too small')
        
        return True
        
    def update_resouce(self, cpu: str, memory: str):
        if self._check_resourse_constraints(cpu, memory):
            service = self.client.get_service(name=
                f'projects/{self.project_id}/locations/{self.region}/services/{self.service_name}'
            )

    def _parse_resource_value(self, value: str):
        """
        Parses the given resource value and returns the corresponding numeric value.

        Args:
          value (str): The resource value to be parsed.

        Returns:
          float: The parsed numeric value.

        Raises:
          Exception: If the value is invalid.
        """
        if value[-1] == "m":
            return int(value[:-1]) / 1000
        elif value[-2:] == "Gi":
            return int(value[:-2]) * 1024
        elif value[-2:] == "Mi":
            return int(value[:-2])
        else:
            raise Exception("Invalid value")

    def _check_resourse_constraints(self, cpu: str, memory: str):
        """
        Checks the resource constraints of the cloud instance.

        Args:
          cpu (str): The CPU value of the cloud instance.
          memory (str): The memory value of the cloud instance.

        Raises:
          Exception: If the memory is too small compared to the CPU.
          Exception: If the CPU is too small compared to the memory.

        Returns:
          bool: True if the resource constraints are satisfied.
        """
        cpu = self._parse_resource_value(cpu)
        memory = self._parse_resource_value(memory)

        cpu_to_memory_min = {4: 2048, 6: 4096, 8: 4096}
        memory_to_cpu_min = {4096: 2, 8192: 4, 16384: 6, 24576: 8}

        if cpu in cpu_to_memory_min and memory < cpu_to_memory_min[cpu]:
            raise Exception("Memory is too small")
        elif memory in memory_to_cpu_min and cpu < memory_to_cpu_min[memory]:
            raise Exception("CPU is too small")

        return True

    def update_resouce(self, cpu: str, memory: str):
        """
        Update the resource constraints of the service.

        Args:
          cpu (str): The CPU limit for the service.
          memory (str): The memory limit for the service.
        """
        if self._check_resourse_constraints(cpu, memory):
            full_server_name = self.cloud_run_info.get_full_server_name()
            service = self.client.get_service(name=full_server_name)

            request = run_v2.UpdateServiceRequest(
                service=service,
            )

            request.service.template.containers[0].resources.limits = {
                "cpu": cpu,
                "memory": memory,
            }

            self.client.update_service(request=request)

    def get_resource(self):
        """
        Retrieves the resource limits for the first container in the service template.

        Returns:
          The resource limits for the container.
        """
        full_server_name = self.cloud_run_info.get_full_server_name()
        service = self.client.get_service(name=full_server_name)

        resource = service.template.containers[0].resources.limits
        return resource


class CloudRunPerformanceMonitor:
    def __init__(self, cloud_run_info: CloudRun) -> None:
        self.cloud_run_info = cloud_run_info
        self.monitoring_client = monitoring_v3.MetricServiceClient()

        self.logging_client = logging_v2.Client(project=cloud_run_info.project_id)

    def get_metric(self, metric_type: str, time_range: TimeRange):
        """
        Retrieves the metric data from the Cloud Monitoring API.

        Args:
          metric_type (str): The metric type to be retrieved.
          hours (int): The number of hours to be retrieved.

        Returns:
          The metric data.
        """
        query = Query(
            self.monitoring_client, 
            project=self.cloud_run_info.project_id,
            metric_type=metric_type,
            end_time=time_range.end_time,
            # end_time=datetime.fromisoformat("2024-01-26 11:41:00.000000"),
            minutes=time_range.get_minutes(),
        )

        query = query.select_resources(zone=self.cloud_run_info.region)
        query = query.select_resources(resource_type="cloud_run_revision")
        query = query.select_resources(service_name=self.cloud_run_info.service_name)

        result = query.as_dataframe()
        return result


if __name__ == "__main__":
    cr = CloudRun("us-central1", "tsmccareerhack2024-icsd-grp3", "sso-tsmc-2")
    # crm = CloudRunResourceManager(cr)
    # crm.update_resouce("4000m", "2Gi")
    # print(crm.get_resource())

    crpm = CloudRunPerformanceMonitor(cr)

    metrics_type = 'run.googleapis.com/request_count'
    # metrics_type = 'run.googleapis.com/container/cpu/utilizations'
    time_range = UntilNowTimeRange(days=0, hours=0, minutes=10)
    result = crpm.get_metric(metrics_type, time_range)

    print(result)

    
