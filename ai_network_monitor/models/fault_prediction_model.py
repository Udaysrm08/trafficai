import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from .anomaly_model import FEATURES

class FaultModel:
    def __init__(self, path): self.path=Path(path); self.model=None; self.metrics={}
    def train(self, df):
        x, y = df[FEATURES], df['fault_label']
        a,b,c,d=train_test_split(x,y,test_size=.2,random_state=42,stratify=y)
        self.model=RandomForestClassifier(n_estimators=180,random_state=42,class_weight='balanced')
        self.model.fit(a,c); p=self.model.predict(b)
        pr,re,f,_=precision_recall_fscore_support(d,p,average='weighted',zero_division=0)
        self.metrics={'accuracy':round(accuracy_score(d,p)*100,1),'precision':round(pr*100,1),'recall':round(re*100,1),'f1':round(f*100,1)}
        joblib.dump({'model':self.model,'metrics':self.metrics},self.path)
    def load(self):
        obj=joblib.load(self.path); self.model=obj['model']; self.metrics=obj.get('metrics',{})
    def predict(self,row):
        x=[[row[k] for k in FEATURES]]; probs=self.model.predict_proba(x)[0]; i=probs.argmax()
        return self.model.classes_[i], float(probs[i])

