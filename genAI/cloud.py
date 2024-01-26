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
        pass

    @abstractmethod
    def get_time_range_iso(self) -> (str, str):
        pass

class UntilNowTimeRange(TimeRange):
    def __init__(self, days: int, hours: int, minutes: int) -> None:
        self.minutes = days * 24 * 60 + hours * 60 + minutes
        self.start_time = datetime.utcnow() - timedelta(minutes=self.minutes)
        self.end_time = datetime.utcnow()

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

      request = run_v2.UpdateServiceRequest(
        service=service,
      )
      
      request.service.template.containers[0].resources.limits = {
        'cpu': cpu,
        'memory': memory,
      }
      
      self.client.update_service(request=request)
    
  def get_resource(self):
    service = self.client.get_service(name=
      f'projects/{self.project_id}/locations/{self.region}/services/{self.service_name}'
    )
    resource = service.template.containers[0].resources.limits
    return resource
  
if __name__ == '__main__':
  crm = CloudRunResourceManager('sso-tsmc')
  crm.update_resouce('4000m', '2Gi')
  print(crm.get_resource())
