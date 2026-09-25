import json, os, sqlite3, threading, time
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from services.traffic_simulator import historical, metric_at
from services.anomaly_service import explain, severity
from services.prediction_service import recommendation, risk
from models.anomaly_model import AnomalyModel
from models.fault_prediction_model import FaultModel

ROOT = Path(__file__).parent
DB = ROOT / 'database/network_monitor.db'
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SENTINEL_SECRET_KEY', 'change-this-sentinel-demo-key')
anom = AnomalyModel(ROOT / 'models/anomaly.joblib')
fault = FaultModel(ROOT / 'models/fault.joblib')

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def add_column(c, table, column, definition):
    if column not in [x['name'] for x in c.execute(f'PRAGMA table_info({table})')]:
        c.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')

def init():
    c = conn()
    c.executescript('''
      CREATE TABLE IF NOT EXISTS domains (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, code TEXT UNIQUE NOT NULL);
      CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, display_name TEXT NOT NULL, domain_id INTEGER NOT NULL, role TEXT NOT NULL DEFAULT 'Operator');
      CREATE TABLE IF NOT EXISTS user_devices (user_id INTEGER NOT NULL, device_id INTEGER NOT NULL, PRIMARY KEY (user_id, device_id), FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(device_id) REFERENCES devices(id));
      CREATE TABLE IF NOT EXISTS network_metrics (id INTEGER PRIMARY KEY, timestamp TEXT, data TEXT);
      CREATE TABLE IF NOT EXISTS anomalies (id INTEGER PRIMARY KEY, timestamp TEXT, severity TEXT, cause TEXT, data TEXT);
      CREATE TABLE IF NOT EXISTS fault_predictions (id INTEGER PRIMARY KEY, timestamp TEXT, fault_type TEXT, probability REAL, risk TEXT);
      CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY, name TEXT, ip TEXT, status TEXT, cpu REAL, memory REAL, latency REAL, packet_loss REAL, health REAL);
      CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, timestamp TEXT, category TEXT, message TEXT, unread INTEGER DEFAULT 1);
    ''')
    for table in ('network_metrics', 'anomalies', 'fault_predictions', 'devices', 'alerts'): add_column(c, table, 'domain_id', 'INTEGER DEFAULT 1')
    c.execute("INSERT OR IGNORE INTO domains(id,name,code) VALUES(1,'North Campus','NORTH'),(2,'Research Lab','RESEARCH'),(3,'Corporate Office','CORP')")
    accounts = [('north.operator','North Operator','Demo@123',1), ('lab.operator','Lab Operator','Demo@123',2), ('corp.operator','Corporate Operator','Demo@123',3)]
    for username, name, password, domain_id in accounts:
        if not c.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
            c.execute('INSERT INTO users(username,password_hash,display_name,domain_id,role) VALUES(?,?,?,?,?)', (username, generate_password_hash(password), name, domain_id, 'Operator'))
    c.commit()
    if c.execute('SELECT count(*) FROM network_metrics').fetchone()[0] == 0:
        df = historical(); anom.train(df); fault.train(df)
        for domain_id in (1,2,3):
            for _, row in df.tail(180).iterrows():
                c.execute('INSERT INTO network_metrics(timestamp,data,domain_id) VALUES (?,?,?)', (row['timestamp'], json.dumps(row.to_dict()), domain_id))
        c.commit()
    elif not anom.path.exists() or not fault.path.exists():
        df = historical(); anom.train(df); fault.train(df)
    else: anom.load(); fault.load()
    device_sets = {1:[('Router-N1','10.10.0.1'),('Switch-N1','10.10.0.10'),('PC-NORTH-01','10.10.1.21'),('PC-NORTH-02','10.10.1.22')],2:[('Router-R1','10.20.0.1'),('Lab-Switch-01','10.20.0.10'),('PC-LAB-01','10.20.1.11'),('PC-LAB-02','10.20.1.12')],3:[('Router-C1','10.30.0.1'),('Firewall-C1','10.30.0.254'),('PC-CORP-01','10.30.1.31'),('PC-CORP-02','10.30.1.32')]}
    if c.execute('SELECT count(*) FROM devices').fetchone()[0] < 8:
        for domain_id, devices in device_sets.items():
            c.executemany('INSERT INTO devices(name,ip,status,cpu,memory,latency,packet_loss,health,domain_id) VALUES(?, ?, "Online",30,40,15,.1,94,?)', [(n, ip, domain_id) for n,ip in devices])
        c.commit()
    # In this prototype each operator owns the endpoints in their assigned domain.
    # The mapping keeps device visibility user-scoped if multiple operators share a domain later.
    for user in c.execute('SELECT id, domain_id FROM users').fetchall():
        device_rows = c.execute('SELECT id FROM devices WHERE domain_id=?', (user['domain_id'],)).fetchall()
        c.executemany('INSERT OR IGNORE INTO user_devices(user_id, device_id) VALUES (?,?)', [(user['id'], device['id']) for device in device_rows])
    c.commit()
    c.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify(error='Authentication required'), 401
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

def current_user():
    if not session.get('user_id'): return None
    c=conn(); user=c.execute('SELECT u.*,d.name AS domain_name,d.code AS domain_code FROM users u JOIN domains d ON d.id=u.domain_id WHERE u.id=?',(session['user_id'],)).fetchone(); c.close(); return dict(user) if user else None

def scoped_rows(q, args=()):
    c=conn(); result=[dict(x) for x in c.execute(q, args).fetchall()]; c.close(); return result

def latest_metrics(domain_id, limit=120):
    data=scoped_rows('SELECT data FROM network_metrics WHERE domain_id=? ORDER BY id DESC LIMIT ?', (domain_id,limit))
    return [json.loads(x['data']) for x in reversed(data)]

def simulate_domain(domain_id):
    record=metric_at(datetime.now()); is_anomaly=anom.predict(record); kind, probability=fault.predict(record); level=risk(probability,kind); c=conn()
    c.execute('INSERT INTO network_metrics(timestamp,data,domain_id) VALUES (?,?,?)',(record['timestamp'],json.dumps(record),domain_id))
    if is_anomaly:
        sev, cause=severity(record), explain(record)
        c.execute('INSERT INTO anomalies(timestamp,severity,cause,data,domain_id) VALUES (?,?,?,?,?)',(record['timestamp'],sev,cause,json.dumps(record),domain_id))
        c.execute('INSERT INTO alerts(timestamp,category,message,domain_id) VALUES (?,?,?,?)',(record['timestamp'],'Critical' if sev=='High' else 'Warning',cause,domain_id))
    if kind != 'No Fault' and probability > .52:
        c.execute('INSERT INTO alerts(timestamp,category,message,domain_id) VALUES (?,?,?,?)',(record['timestamp'],'Warning',f'AI predicted {kind} ({probability:.0%})',domain_id))
    c.execute('INSERT INTO fault_predictions(timestamp,fault_type,probability,risk,domain_id) VALUES (?,?,?,?,?)',(record['timestamp'],kind,probability,level,domain_id))
    c.commit(); c.close(); return record

def worker():
    while True:
        time.sleep(5)
        for domain_id in (1,2,3): simulate_domain(domain_id)

@app.route('/login', methods=['GET','POST'])
def login():
    if session.get('user_id'): return redirect(url_for('page'))
    if request.method == 'POST':
        username=request.form.get('username','').strip().lower(); password=request.form.get('password',''); c=conn(); user=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone(); c.close()
        if user and check_password_hash(user['password_hash'],password): session.clear(); session['user_id']=user['id']; return redirect(url_for('page'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
@login_required
def page(): return render_template('dashboard.html',page='dashboard',user=current_user())

@app.route('/<name>')
@login_required
def pages(name):
    if name in ['traffic','anomalies','predictions','devices','alerts','settings']: return render_template(f'{name}.html',page=name,user=current_user())
    return ('Not found',404)

@app.route('/api/metrics')
@login_required
def metrics(): return jsonify(latest_metrics(current_user()['domain_id'],int(request.args.get('limit',120))))

@app.route('/api/dashboard')
@login_required
def dashboard():
    domain=current_user()['domain_id']; m=latest_metrics(domain,1)[-1]; a=scoped_rows('SELECT * FROM anomalies WHERE domain_id=? ORDER BY id DESC LIMIT 6',(domain,)); predictions=scoped_rows('SELECT * FROM fault_predictions WHERE domain_id=? ORDER BY id DESC LIMIT 1',(domain,))
    if predictions: p=predictions[0]
    else:
        kind, probability=fault.predict(m); p={'fault_type':kind,'probability':probability,'risk':risk(probability,kind)}
    health=max(0,round(100-(m['latency']/5)-(m['packet_loss']*5)-(m['bandwidth']*.12)))
    return jsonify(metric=m,health=health,anomalies=a,prediction=p,unread=scoped_rows('SELECT count(*) AS n FROM alerts WHERE unread=1 AND domain_id=?',(domain,))[0]['n'])

@app.route('/api/traffic')
@login_required
def traffic(): return jsonify(metrics=latest_metrics(current_user()['domain_id'],int(request.args.get('limit',240))),protocols={'HTTPS':46,'DNS':18,'TCP':16,'UDP':12,'Other':8})

@app.route('/api/anomalies')
@login_required
def anomalies():
    data=scoped_rows('SELECT * FROM anomalies WHERE domain_id=? ORDER BY id DESC LIMIT 300',(current_user()['domain_id'],)); sev=request.args.get('severity')
    if sev: data=[x for x in data if x['severity']==sev]
    for x in data: x.update(json.loads(x.pop('data')))
    return jsonify(data)

@app.route('/api/fault-prediction')
@login_required
def prediction():
    m=latest_metrics(current_user()['domain_id'],1)[-1]; kind,p=fault.predict(m)
    return jsonify(fault_type=kind,probability=p,risk=risk(p,kind),confidence=round(p*100,1),recommendation=recommendation(kind),factors={'Bandwidth utilization':m['bandwidth'],'Packet loss':m['packet_loss'],'Latency':m['latency'],'CPU utilization':m['cpu']},model_metrics=fault.metrics)

@app.route('/api/devices')
@login_required
def devices():
    return jsonify(scoped_rows('''
        SELECT d.* FROM devices d
        INNER JOIN user_devices ud ON ud.device_id=d.id
        WHERE ud.user_id=? AND d.domain_id=?
    ''', (current_user()['id'], current_user()['domain_id'])))

@app.route('/api/alerts')
@login_required
def alerts(): return jsonify(scoped_rows('SELECT * FROM alerts WHERE domain_id=? ORDER BY id DESC LIMIT 100',(current_user()['domain_id'],)))

@app.route('/api/simulate',methods=['POST','GET'])
@login_required
def api_simulate(): return jsonify(simulate_domain(current_user()['domain_id']))

if __name__=='__main__':
    init(); threading.Thread(target=worker,daemon=True).start(); app.run(debug=False,host='127.0.0.1',port=5000)

