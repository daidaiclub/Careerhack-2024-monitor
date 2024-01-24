from google.cloud import monitoring_v3
from google.cloud.monitoring_v3.query import Query
import datetime

def fetch_metric(project_id="tsmccareerhack2024-icsd-grp3", metric_type="run.googleapis.com/request_count", hours=1):
  client = monitoring_v3.MetricServiceClient()

  # 創建查詢
  query = Query(client, 
                      project="tsmccareerhack2024-icsd-grp3", 
                      metric_type="run.googleapis.com/request_count", 
                      hours=100)
  # 增加篩選條件：地區和資源類型
  query = query.select_resources(zone='us-central1')
  query = query.select_resources(resource_type='cloud_run_revision')

  # 增加篩選條件：服務名稱
  query = query.select_resources(service_name='sso-tsmc')
  result = query.as_dataframe()
  return result

if __name__ == '__main__':
  result = fetch_metric()
  result.to_csv('metric.csv')
  print(result)