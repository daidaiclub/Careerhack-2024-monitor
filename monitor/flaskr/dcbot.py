import pandas as pd
import os
from flaskr.genAI.llm import LLM
from functools import reduce
# 檢查指標是否異常
class MetrixUtil:
    @staticmethod
    def check_metrics_abnormalities(metrics: list):
        metric = metrics[-1]

        if metric['Container Startup Latency (ms)'] > 0:
            return True

        if metric['Instance Count (active)'] > 4:
            return True

        if metric['Request Count (4xx)'] > 5:
            return True
        
        if metric['Request Count (5xx)'] > 5:
            return True

        times_dict = {'cpu': 0, 'memory': 0}

        if len(metrics) >= 2:
            for metric in metrics[-2:]:
                cpu_abnormal = metric['Container CPU Utilization (%)'] > 60
                memory_abnormal = metric['Container Memory Utilization (%)'] > 80

                if cpu_abnormal:
                    times_dict['cpu'] += 1
                else:
                    times_dict['cpu'] = 0

                if memory_abnormal:
                    times_dict['memory'] += 1
                else:
                    times_dict['memory'] = 0

        return times_dict['cpu'] >= 2 or times_dict['memory'] >= 2


def gen(temp_dir: str):
    data_frames = []
    for entry in os.listdir(temp_dir):
        data_frames.append(pd.read_csv(os.path.join(temp_dir, entry)))
    data_frames = list(map(lambda df: df.assign(Time=pd.to_datetime(df['Time'])), data_frames))
    merged_data = reduce(lambda left, right: pd.merge(
        left, right, on=['Time'], how='outer'), data_frames)
    merged_data = merged_data.set_index('Time')
    mdpdf = "報告書\n"
    for i in range(2, len(merged_data) - 1):
        metrics = [item.to_dict() for item in merged_data.iloc[i-2:i]]
        if MetrixUtil.check_metrics_abnormalities(metrics):
            mdpdf += f'## 異常時間: {merged_data.index[i]}\n'
            mdpdf += LLM.AnalysisError.gen(data=f'指標：{metrics[i-2:i].to_dict()}')
    return mdpdf