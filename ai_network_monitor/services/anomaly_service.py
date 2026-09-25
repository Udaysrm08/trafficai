def explain(r):
    if r['packet_loss']>4: return 'Critical packet loss detected'
    if r['latency']>110: return 'Abnormal latency increase'
    if r['bandwidth']>85: return 'Sudden bandwidth spike / congestion'
    if r['error_rate']>1: return 'Elevated interface error rate'
    return 'Unusual traffic pattern detected'
def severity(r):
    score=(r['packet_loss']*8)+(max(0,r['latency']-60)/3)+max(0,r['bandwidth']-75)
    return 'High' if score>65 else 'Medium' if score>28 else 'Low'

