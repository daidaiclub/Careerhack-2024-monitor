""" Cloud Run Performance Monitor and Resource Manager """

from abc import abstractmethod, ABC
from datetime import datetime, timedelta
from typing import Tuple
import pandas as pd
from google.cloud import run_v2
from google.cloud import monitoring_v3, logging_v2
from google.cloud.monitoring_v3.query import Query

import dotenv
dotenv.load_dotenv()

# Time Range interface
class TimeRange(ABC):
    """
    Abstract base class representing a time range.
    """
    start_time = None
    end_time = None

    @abstractmethod
    def get_minutes(self) -> int:
        """
        Abstract method to get the duration of the time range in minutes.
        
        Returns:
            int: The duration of the time range in minutes.
        """

    @abstractmethod
    def get_time_range_iso(self) -> Tuple[str, str]:
        """
        Abstract method to get the time range in ISO format.
        
        Returns:
            Tuple[str, str]: A tuple containing the start and end time of the range in ISO format.
        """

class UntilNowTimeRange(TimeRange):
    """
    Represents a time range from a specified number of 
        days, hours, and minutes ago until the current time.

    Args:
        days (int): The number of days ago.
        hours (int): The number of hours ago.
        minutes (int): The number of minutes ago.

    Attributes:
        minutes (int): The total number of minutes in the time range.
        start_time (datetime): The start time of the time range.
        end_time (datetime): The end time of the time range.

    Methods:
        get_minutes(): Returns the total number of minutes in the time range.
        get_time_range_iso(): Returns a tuple of ISO-formatted 
            start and end times of the time range.
    """

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
    """
    Represents a time range from a specified start time to a specified end time.
    """

    def __init__(self, start_time: str, end_time: str) -> None:
        """
        Initializes a SpecificTimeRange object.

        Args:
            start_time (str): The start time of the time range in ISO format.
            end_time (str): The end time of the time range in ISO format.
        """
        self.start_time = datetime.fromisoformat(start_time)
        self.end_time = datetime.fromisoformat(end_time)

    def get_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds()) // 60

    def get_time_range_iso(self) -> Tuple[str, str]:
        return self.start_time.isoformat(), self.end_time.isoformat()


class CloudRun:
    """
    Represents a Cloud Run service.
    """

    def __init__(self, region: str, project_id: str, service_name: str) -> None:
        """
        Initializes a CloudRun object.

        Args:
            region (str): The region where the service is located.
            project_id (str): The ID of the project.
            service_name (str): The name of the service.
        """
        self.region = region
        self.project_id = project_id
        self.service_name = service_name

    def get_full_service_name(self):
        """
        Returns the full service name in the format 
            'projects/{project_id}/locations/{region}/services/{service_name}'.

        Returns:
            str: The full service name.
        """
        return f'projects/{self.project_id}/locations/{self.region}/services/{self.service_name}'


class CloudRunResource:
    """
    Represents a cloud resource for running applications.

    Attributes:
        value (int): The current value of the resource.
        parent: The parent object of the resource.

    Methods:
        __init__(self, parent): Initializes a new instance of the CloudRunResource class.
        scale_up(self): Scales up the resource by doubling its value.
        scale_down(self): Scales down the resource by halving its value.
    """

    value: int

    def __init__(self, parent) -> None:
        self.parent = parent

    def scale_up(self):
        """
        Scales up the resource by doubling its value.
        If an exception occurs during scaling, the resource value is reverted to its original value.
        """
        self.parent.init_resource()
        origin = self.value
        try:
            self.value = self.value * 2
            self.parent.update_resouce()
        except Exception:
            self.value = origin

    def scale_down(self):
        """
        Scales down the resource by halving its value.
        If an exception occurs during scaling, the resource value is reverted to its original value.
        """
        self.parent.init_resource()
        origin = self.value
        try:
            self.value = self.value // 2
            self.parent.update_resouce()
        except Exception:
            self.value = origin


class CloudRunResourceManager:
    """
    A class that manages the resource constraints of a Cloud Run service.

    Attributes:
        cloud_run_info (CloudRun): The CloudRun object containing information 
            about the Cloud Run service.
        client (run_v2.ServicesClient): The client for interacting with the Cloud Run API.
        is_init_resource (bool): Flag indicating whether the resource values have been initialized.

    Methods:
        init_resource(): Initializes the resource values for CPU and memory.
        update_resouce(): Updates the resource constraints of the service.
        get_resource() -> Dict[str, str]: Retrieves the resource limits for 
            the first container in the service template.
    """

    def __init__(self, cloud_run_info: CloudRun) -> None:
        self.cloud_run_info = cloud_run_info
        self.client = run_v2.ServicesClient()
        self.is_init_resource = False

        self.cpu = CloudRunResource(self)
        self.memory = CloudRunResource(self)

    def init_resource(self):
        """
        Initializes the resource values for CPU and memory.

        If the resource values have not been initialized yet, 
        this method retrieves the resource information
        and updates the CPU and memory values accordingly.

        Returns:
            None
        """
        if not self.is_init_resource:
            resource = self.get_resource()

            self.cpu.value = self._parse_resource_value_to_int(resource['cpu'])
            self.memory.value = self._parse_resource_value_to_int(
                resource['memory'])

    def _parse_resource_value_to_int(self, value: str) -> int | Exception:
        """
        Parses a resource value string to an integer.

        Args:
            value (str): The resource value string.

        Returns:
            int: The parsed resource value as an integer.

        Raises:
            Exception: If the value is invalid.
        """
        print(value)
        if value[-1] == 'm':
            return int(value[:-1]) // 1000
        if value[-2:] == 'Gi':
            return int(value[:-2]) * 1024
        if value[-2:] == 'Mi':
            return int(value[:-2])
        raise Exception('Invalid value')

    def _parse_resource_value_to_str(self, value: int) -> str:
        """
        Parses a resource value integer to a string.

        Args:
            value (int): The resource value integer.

        Returns:
            str: The parsed resource value as a string.
        """
        # this is cpu
        if value < 16:
            return f'{value * 1000}m'
        # below is memory
        if value % 1024 == 0:
            return f'{value // 1024}Gi'
        return f'{value}Mi'

    def _check_resourse_constraints(self, cpu: int, memory: int) -> bool:
        """
        Checks if the given CPU and memory values are within valid constraints.

        Args:
            cpu (int): The CPU value.
            memory (int): The memory value.

        Returns:
            bool: True if the values are within valid constraints, False otherwise.
        """
        if cpu < 1 or cpu > 8:
            return False
        elif memory < 512 or memory > 24576:
            return False

        return True

    def _auto_update_resource_constraints(self, cpu: int, memory: int) -> Tuple[int, int]:
        """
        Automatically adjusts the CPU and memory values based on predefined constraints.

        Args:
            cpu (int): The CPU value.
            memory (int): The memory value.

        Returns:
            Tuple[int, int]: The adjusted CPU and memory values.
        """
        cpu_to_memory_min = {4: 2048, 6: 4096, 8: 4096}
        memory_to_cpu_min = {4096: 2, 8192: 4, 16384: 6, 24576: 8}

        if cpu in cpu_to_memory_min and memory < cpu_to_memory_min[cpu]:
            memory = cpu_to_memory_min[cpu]
        elif memory in memory_to_cpu_min and cpu < memory_to_cpu_min[memory]:
            cpu = memory_to_cpu_min[memory]

        return cpu, memory

    def update_resouce(self) -> None | Exception:
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

    def get_resource(self) -> dict[str, str]:
        '''
        Retrieves the resource limits for the first container in the service template.

        Returns:
          Dict[str, str]: The resource limits for the container.
        '''

        full_service_name = self.cloud_run_info.get_full_service_name()
        service = self.client.get_service(name=full_service_name)

        resource = service.template.containers[0].resources.limits
        return resource


class CloudRunPerformanceMonitor:
    """
    A class that monitors the performance of a Cloud Run service.

    Attributes:
        cloud_run_info (CloudRun): The CloudRun object containing information 
            about the Cloud Run service.
        monitoring_client (monitoring_v3.MetricServiceClient): The client for 
            interacting with the Cloud Monitoring API.
        logging_client (logging_v2.Client): The client for interacting with the Cloud Logging API.
        scalar_type (list[str]): A list of scalar metric types.
        distribution_type (list[str]): A list of distribution metric types.

    Methods:
        get_scalar_query(self, query): Returns a modified query object 
            with alignment and reduction applied.
        get_distrbution_query(self, query): Returns a modified query object 
            with alignment and reduction applied.
        get_metric(self, metric_type, time_range, options): Retrieves the metric 
            from the Cloud Monitoring API.
        get_logs(self, time_range): Retrieves the logs from the Cloud Logging API.
    """

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
            except Exception:
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
        """
        Retrieves a metric based on the specified metric type and time range.

        Parameters:
        - metric_type (str): The type of metric to retrieve.
        - time_range (TimeRange): The time range for the metric data.
        - options (dict, optional): Additional options for processing the metric data.

        Returns:
        - DataFrame: The processed metric data as a pandas DataFrame.
        """
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
