# Path: genAI/main.py

from llm import gen_solution
import pandas as pd
from functools import reduce
import os
import time

def simulate_realtime_csv():
  csv_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ICSD Cloud Resource Sample'))

  cpu_utilization = pd.read_csv(os.path.join(csv_dir, 'Container CPU Utilization.csv'))
  memory_utilization = pd.read_csv(os.path.join(csv_dir, 'Container Memory Utilization.csv'))
  startup_latenecy = pd.read_csv(os.path.join(csv_dir, 'Container Startup Latency.csv'))
  instance_count = pd.read_csv(os.path.join(csv_dir, 'Instance Count.csv'))
  request_count = pd.read_csv(os.path.join(csv_dir, 'Request Count.csv'))
  request_latency = pd.read_csv(os.path.join(csv_dir, 'Request Latency.csv'))
  
  data_frames = [
    cpu_utilization,
    memory_utilization,
    startup_latenecy,
    instance_count,
    request_count,
    request_latency,
  ]
  
  data_frames = list(map(lambda df: df.assign(Time=pd.to_datetime(df['Time'])), data_frames))

  merged_data = reduce(lambda left, right: pd.merge(left, right, on=['Time'], how='outer'), data_frames)
  merged_data = merged_data.set_index('Time')
  
  for index, row in merged_data.iterrows():
    yield row.to_dict()
    time.sleep(0.02)

# {'Container CPU Utilization (%)': 16.0875, 'Container Memory Utilization (%)': 56.99, 'Container Startup Latency (ms)': nan, 'Instance Count (active)': 1.0, 'Instance Count (idle)': 1.0, 'Request Count (1xx)': 0.0, 'Request Count (2xx)': 5.0, 'Request Count (3xx)': 0.0, 'Request Count (4xx)': 4.0, 'Request Latency (ms)': 31.2701591}
# 檢查指標是否異常
def check_metrics_abnormalities(metrics):
  if metrics['Container CPU Utilization (%)'] > 60 or metrics['Container Memory Utilization (%)'] > 60:
    return True
  
  if metrics['Container Startup Latency (ms)'] > 0:
    return True
  
  if metrics['Instance Count (active)'] > 2:
    return True
  
  if metrics['Request Count (4xx)'] > 5:
    return True
  
  return False
  
if __name__ == '__main__':
  for i in simulate_realtime_csv():
    print(i)
    if check_metrics_abnormalities(i):
      gen_solution('', str(i))
      # break