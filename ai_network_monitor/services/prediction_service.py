def recommendation(kind):
    return {'Congestion Risk':'Investigate bandwidth-intensive connections and review network capacity.','High Latency Risk':'Check routing paths, uplinks, and latency-sensitive services.','Packet Loss Risk':'Inspect physical links, interface errors, and packet queues.','Device Overload Risk':'Reduce device load and review CPU-intensive processes.','No Fault':'Network conditions are stable. Continue routine monitoring.'}.get(kind,'Continue monitoring.')
def risk(prob, kind): return 'Low' if kind=='No Fault' else ('High' if prob>=.65 else 'Medium')

