from abc import abstractmethod, ABC
import pandas as pd
from datetime import datetime, timedelta
from google.cloud import run_v2
from google.cloud import monitoring_v3, logging_v2
from google.cloud.monitoring_v3.query import Query

import os
import dotenv
from typing import Tuple

dotenv.load_dotenv()


# Time Range interface
class TimeRange(ABC):
    @abstractmethod
    def get_minutes(self) -> int:
        self.start_time = 0
        self.end_time = 0
        pass

    @abstractmethod
    def get_time_range_iso(self) -> Tuple[str, str]:
        pass


class UntilNowTimeRange(TimeRange):
    def __init__(self, days: int = 0, hours: int = 0, minutes: int = 0) -> None:
        self.minutes = days * 24 * 60 + hours * 60 + minutes
        now = datetime.now().replace(second=0, microsecond=0)
        self.start_time = now - timedelta(minutes=self.minutes)
        self.end_time = now

    def get_minutes(self) -> int:
        return self.minutes

    def get_time_range_iso(self) -> Tuple[str, str]:
        return self.start_time.isoformat(), self.end_time.isoformat()


class SpecificTimeRange(TimeRange):
    def __init__(self, start_time: str, end_time: str) -> None:
        self.start_time = datetime.fromisoformat(start_time)
        self.end_time = datetime.fromisoformat(end_time)

    def get_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds()) // 60

    def get_time_range_iso(self) -> Tuple[str, str]:
        return self.start_time.isoformat(), self.end_time.isoformat()


class CloudRun:
    def __init__(self, region: str, project_id: str, service_name: str) -> None:
        self.region = region
        self.project_id = project_id
        self.service_name = service_name

    def get_full_service_name(self):
        return f'projects/{self.project_id}/locations/{self.region}/services/{self.service_name}'

class CloudRunResource:
    value: int

    def __init__(self, parent) -> None:
        self.parent = parent

    def scale_up(self):
        self.parent.init_resource()
        origin = self.value
        try:
            self.value = self.value * 2
            self.parent.update_resouce()
        except:
            self.value = origin

    def scale_down(self):
        self.parent.init_resource()
        origin = self.value
        try:
            self.value = self.value // 2
            self.parent.update_resouce()
        except:
            self.value = origin
    pass

class CloudRunResourceManager:

    def __init__(self, cloud_run_info: CloudRun) -> None:
        self.cloud_run_info = cloud_run_info
        self.client = run_v2.ServicesClient()
        self.is_init_resource = False

        self.cpu = CloudRunResource(self)
        self.memory = CloudRunResource(self)

    def init_resource(self):
        if not self.is_init_resource:
            resource = self.get_resource()

            self.cpu.value = self._parse_resource_value_to_int(resource['cpu'])
            self.memory.value = self._parse_resource_value_to_int(resource['memory'])
    
    # if value is memory, return Mi
    def _parse_resource_value_to_int(self, value: str) -> int:
        print(value)
        if value[-1] == 'm':
            return int(value[:-1]) // 1000
        elif value[-2:] == 'Gi':
            return int(value[:-2]) * 1024
        elif value[-2:] == 'Mi':
            return int(value[:-2])
        else:
            raise Exception('Invalid value')
        
    def _parse_resource_value_to_str(self, value: int) -> str:
        # this is cpu
        if value < 16:
            return f'{value * 1000}m'
        # below is memory
        elif value % 1024 == 0:
            return f'{value // 1024}Gi'
        else:
            return f'{value}Mi'

    def _check_resourse_constraints(self, cpu: int, memory: int):
        if cpu < 1 or cpu > 8:
            return False
        elif memory < 512 or memory > 24576:
            return False

        return True
    
    def _auto_update_resource_constraints(self, cpu: int, memory: int):

        cpu_to_memory_min = {4: 2048, 6: 4096, 8: 4096}
        memory_to_cpu_min = {4096: 2, 8192: 4, 16384: 6, 24576: 8}

        if cpu in cpu_to_memory_min and memory < cpu_to_memory_min[cpu]:
            memory = cpu_to_memory_min[cpu]
        elif memory in memory_to_cpu_min and cpu < memory_to_cpu_min[memory]:
            cpu = memory_to_cpu_min[memory]

        return cpu, memory

    def update_resouce(self):
        '''
        Update the resource constraints of the service.

        Args:
          cpu (str): The CPU limit for the service.
          memory (str): The memory limit for the service.
        '''
        cpu = self.cpu.value
        memory = self.memory.value
        if self._check_resourse_constraints(cpu, memory):
            cpu, memory = self._auto_update_resource_constraints(cpu, memory)
            full_service_name = self.cloud_run_info.get_full_service_name()
            service = self.client.get_service(name=full_service_name)

            request = run_v2.UpdateServiceRequest(
                service=service,
            )

            request.service.template.containers[0].resources.limits = {
                'cpu': self._parse_resource_value_to_str(cpu),
                'memory': self._parse_resource_value_to_str(memory),
            }

            self.client.update_service(request=request)
        else:
            raise Exception('Invalid resource constraints')

    def get_resource(self):
        '''
        Retrieves the resource limits for the first container in the service template.

        Returns:
          The resource limits for the container.
        '''

        # TODO: 優先從 資料庫抓？ 沒有的話再從 GCP 抓
        full_service_name = self.cloud_run_info.get_full_service_name()
        service = self.client.get_service(name=full_service_name)

        resource = service.template.containers[0].resources.limits
        return resource


class CloudRunPerformanceMonitor:
    def __init__(self, cloud_run_info: CloudRun) -> None:
        self.cloud_run_info = cloud_run_info
        self.monitoring_client = monitoring_v3.MetricServiceClient()

        self.logging_client = logging_v2.Client(
            project=cloud_run_info.project_id)

        self.scalar_type = [
            'run.googleapis.com/request_count',
            'run.googleapis.com/container/instance_count'
        ]

        self.distribution_type = [
            'run.googleapis.com/request_latencies',
            'run.googleapis.com/container/cpu/utilizations',
            'run.googleapis.com/container/memory/utilizations',
            'run.googleapis.com/container/startup_latencies'
        ]

    def _get_metric_query(self, metric_type: str, time_range: TimeRange) -> Query:
        '''
        Retrieves the metric query from the Cloud Monitoring API.

        Args:
          time_range (TimeRange): The time range to be retrieved.

        Returns:
          The metric query.
        '''
        query = Query(
            self.monitoring_client,
            project=self.cloud_run_info.project_id,
            metric_type=metric_type,
            end_time=time_range.end_time,
            minutes=time_range.get_minutes(),
        )

        query = (
            query.select_resources(zone=self.cloud_run_info.region)
            .select_resources(resource_type='cloud_run_revision')
            .select_resources(service_name=self.cloud_run_info.service_name)
        )

        return query

    def _process_pd_dataframe(self, df: pd.DataFrame, options: dict = None):
        '''
        Processes the Pandas dataframe.

        Args:
            df (pd.DataFrame): The dataframe to be processed.
            metric_label (str): The metric label to be processed.

        Returns:
            The processed dataframe.
        '''
        metric_label = options.get('metric_label', None)
        metric_new_label = options.get('metric_new_label', None)
        multiply = options.get('multiply', 1)

        if not metric_label is None:
            if metric_new_label is None:
                metric_new_label = metric_label
            try:
                values = df.columns.get_level_values(metric_label).values
                df.columns = [f'{metric_new_label} ({i})' for i in values]
            except:
                if not df.empty:
                    df.columns = [f'{metric_new_label}']

        df = df * multiply

        df.index = df.index.map(lambda x: x.strftime('%Y-%m-%d %H:%M:00'))
        return df

    def get_scalar_query(
        self, query: Query
    ) -> Query:
        """
        Returns a modified query object with alignment and reduction applied.

        Args:
            query (Query): The original query object.

        Returns:
            Query: The modified query object.
        """
        query = query.align(
            monitoring_v3.Aggregation.Aligner.ALIGN_MEAN, seconds=10)

        query = query.reduce(
            monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
            'metric.label.state',
            'metric.label.response_code_class',
        )
        return query

    def get_distrbution_query(
        self, query: Query
    ) -> Query:
        """
        Returns a modified query object with alignment and reduction applied.

        Args:
            query (Query): The original query object.

        Returns:
            Query: The modified query object with alignment and reduction applied.
        """
        query = query.align(
            monitoring_v3.Aggregation.Aligner.ALIGN_PERCENTILE_50, seconds=10
        )
        query = query.reduce(monitoring_v3.Aggregation.Reducer.REDUCE_MEAN)
        return query

    def get_metric(self, metric_type: str, time_range: TimeRange, options: dict = None):
        query = self._get_metric_query(metric_type, time_range)

        if metric_type in self.scalar_type:
            query = self.get_scalar_query(query)
        elif metric_type in self.distribution_type:
            query = self.get_distrbution_query(query)

        df = query.as_dataframe()
        return self._process_pd_dataframe(df, options)

    def get_logs(self, time_range: TimeRange):
        '''
        Retrieves the logs from the Cloud Logging API.

        Args:
          time_range (TimeRange): The time range to be retrieved.

        Returns:
          The logs.
        '''

        start, end = time_range.get_time_range_iso()
        print(start, end)

        filter_str = f'''
resource.type="cloud_run_revision"
resource.labels.service_name="{self.cloud_run_info.service_name}"
timestamp>="{start}Z"
timestamp<="{end}Z"
ERROR
severity!="ERROR"
'''

        print(filter_str)

        entries = self.logging_client.list_entries(filter_=filter_str)

        logs = []
        for entry in entries:
            logs.append(entry.payload)

        return logs


if __name__ == '__main__':
    cr = CloudRun('us-central1', 'tsmccareerhack2024-icsd-grp3', 'sso-tsmc-2')
    # crm = CloudRunResourceManager(cr)
    # crm.update_resouce('4000m', '2Gi')
    # print(crm.get_resource())

    crpm = CloudRunPerformanceMonitor(cr)
    time_range = UntilNowTimeRange(minutes=35)

    tmp = crpm.get_metric('run.googleapis.com/container/instance_count',
                          time_range, 'state', 'Instance Count')
    print(tmp)

    # metries_datas = []
    # metries_types_and_name = [
    #     ('run.googleapis.com/request_count', 'response_code_class'),
    #     ('run.googleapis.com/request_latencies', 'latency'),
    #     ('run.googleapis.com/container/instance_count', 'instance_count'),
    #     ('run.googleapis.com/container/cpu/utilizations', 'cpu_utilization'),
    #     ('run.googleapis.com/container/memory/utilizations', 'memory_utilization'),
    #     ('run.googleapis.com/container/startup_latencies', 'startup_latency')
    # ]

    # for metric_type, metric_label in metries_types_and_name:
    #     metries_datas.append(
    #         crpm.get_metric(metric_type, time_range, metric_label)
    #     )

    # res = pd.concat(metries_datas, axis=1)
    # ignore_dropna_fields = ['startup_latency']
    # res = res.dropna(subset=[col for col in res.columns if not col in ignore_dropna_fields])
    # print(res)
