import joblib
import pandas as pd
import sklearn
from pathlib import Path
from sklearn.ensemble import IsolationForest

FEATURES = ['bandwidth','latency','packet_loss','jitter','pps','error_rate']

class AnomalyModel:
    def __init__(self, path): self.path = Path(path); self.model = None
    def train(self, df):
        self.model = IsolationForest(contamination=.055, random_state=42, n_estimators=160)
        self.model.fit(df[FEATURES]); joblib.dump({'model':self.model,'sklearn_version':sklearn.__version__},self.path)
    def load(self):
        saved = joblib.load(self.path)
        if not isinstance(saved, dict) or saved.get('sklearn_version') != sklearn.__version__: return False
        self.model = saved['model']; return True
    def predict(self, row): return int(self.model.predict(pd.DataFrame([[row[x] for x in FEATURES]], columns=FEATURES))[0]) == -1

