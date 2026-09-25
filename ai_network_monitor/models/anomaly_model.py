import joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest

FEATURES = ['bandwidth','latency','packet_loss','jitter','pps','error_rate']

class AnomalyModel:
    def __init__(self, path): self.path = Path(path); self.model = None
    def train(self, df):
        self.model = IsolationForest(contamination=.055, random_state=42, n_estimators=160)
        self.model.fit(df[FEATURES]); joblib.dump(self.model, self.path)
    def load(self): self.model = joblib.load(self.path)
    def predict(self, row): return int(self.model.predict([[row[x] for x in FEATURES]])[0]) == -1

