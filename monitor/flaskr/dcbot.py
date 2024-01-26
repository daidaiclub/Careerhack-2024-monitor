from genAi import MetrixUtil
import pandas as pd
import os
from functools import reduce
def gen(temp_dir: str):
  data_frames = []
  for entry in os.listdir(temp_dir):
    data_frames.append(pd.read_csv(os.path.join(temp_dir, entry)))
  data_frames = list(map(lambda df: df.assign(Time=pd.to_datetime(df['Time'])), data_frames))
  merged_data = reduce(lambda left, right: pd.merge(
      left, right, on=['Time'], how='outer'), data_frames)
  merged_data = merged_data.set_index('Time')
  
  pass
  
