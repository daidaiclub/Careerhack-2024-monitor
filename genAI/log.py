from google.cloud import logging
from datetime import datetime, timedelta

def fetch_logs(project_id="tsmccareerhack2024-icsd-grp3", service_name="sso-tsmc", start_time=None, end_time=None, page_size=100):
  """
  預設回傳過去一小時內指定服務的日誌。
  :param project_id: Google Cloud 專案ID，預設為 'tsmccareerhack2024-icsd-grp3'。
  :param service_name: Cloud Run 服務名稱，預設為 'sso-tsmc'。
  :param start_time: 查詢的開始時間，預設為當前時間減一小時。
  :param end_time: 查詢的結束時間，預設為當前時間。
  :param page_size: 每頁日誌的數量。
  :return: 日誌列表。
  """
  # 如果未提供時間，則設置預設時間範圍為過去一小時
  if not start_time:
    start_time = datetime.utcnow() - timedelta(hours=1)
  if not end_time:
    end_time = datetime.utcnow()

  # 創建 Logging 客戶端
  logging_client = logging.Client(project=project_id)

  # 建立過濾器字符串
  filter_str = f"""
  resource.type="cloud_run_revision"
  resource.labels.service_name="{service_name}"
  timestamp>="{start_time.isoformat()}Z"
  timestamp<="{end_time.isoformat()}Z"
  ERROR
  severity!="ERROR"
  """

  # 查詢日誌
  entries = logging_client.list_entries(filter_=filter_str, page_size=page_size)
  
  # 收集日誌項目
  logs = []
  for entry in entries:
    logs.append(entry.payload)

  return logs

# 直接使用函數，不需提供任何參數
if __name__ == '__main__':
  logs = fetch_logs()
  for log in logs:
    print(log)
