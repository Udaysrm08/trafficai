import random, math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

def label(r):
    if r['packet_loss']>4.5: return 'Packet Loss Risk'
    if r['latency']>130: return 'High Latency Risk'
    if r['bandwidth']>82 and r['pps']>6500: return 'Congestion Risk'
    if r['cpu']>88 or r['memory']>91: return 'Device Overload Risk'
    return 'No Fault'

def metric_at(ts, force_event=None):
    hour=ts.hour+ts.minute/60; load=48+22*math.sin((hour-8)*math.pi/12)+random.gauss(0,5)
    event=force_event or (random.choice(['spike','loss','latency','overload']) if random.random()<.07 else None)
    bw=float(np.clip(load+(random.uniform(25,45) if event=='spike' else 0),8,99))
    latency=max(4,18+bw*.38+random.gauss(0,4)+(random.uniform(75,130) if event=='latency' else 0))
    loss=max(.01,random.gauss(.18, .11)+(random.uniform(4,10) if event=='loss' else 0)+(1.2 if bw>88 else 0))
    cpu=float(np.clip(22+bw*.62+random.gauss(0,6)+(random.uniform(20,36) if event=='overload' else 0),5,100))
    mem=float(np.clip(30+bw*.45+random.gauss(0,5)+(random.uniform(15,30) if event=='overload' else 0),8,99))
    jitter=max(.2,2+bw*.10+random.gauss(0,1)+(random.uniform(10,25) if event in ('loss','latency') else 0))
    r={'timestamp':ts.isoformat(timespec='seconds'),'bandwidth':round(bw,2),'upload':round(bw*random.uniform(.20,.38),2),'download':round(bw*random.uniform(.62,.80),2),'latency':round(latency,2),'packet_loss':round(loss,2),'jitter':round(jitter,2),'connections':int(90+bw*7+random.gauss(0,25)),'pps':round(max(200,bw*75+random.gauss(0,250)),1),'cpu':round(cpu,1),'memory':round(mem,1),'error_rate':round(max(.01,loss*.22+random.random()*.12),3),'status':'Warning' if event else 'Healthy'}
    r['fault_label']=label(r); return r

def historical(n=1200):
    now=datetime.now(); return pd.DataFrame([metric_at(now-timedelta(minutes=5*(n-i))) for i in range(n)])

