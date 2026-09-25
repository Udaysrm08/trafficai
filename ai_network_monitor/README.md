# Sentinel NOC — AI-Powered Network Traffic Analysis and Fault Prediction

A polished, live Flask prototype for a B.Tech 7th Semester minor project. It simulates realistic traffic, stores events in SQLite, detects anomalies with Isolation Forest, and predicts fault categories with a Random Forest classifier.

## Requirements

- Windows 10/11 and Python 3.10+ (select **Add Python to PATH** during installation)
- VS Code (recommended)

## Run locally (Windows / VS Code)

Open this `ai_network_monitor` folder in VS Code, then open its integrated PowerShell terminal and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, run this once in that terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then open http://127.0.0.1:5000. Stop the server with `Ctrl+C`.

## What happens on first startup

1. SQLite tables are created in `database/network_monitor.db`.
2. Historical, daily-pattern traffic data is generated.
3. `models/anomaly.joblib` (Isolation Forest) and `models/fault.joblib` (Random Forest) are trained and saved.
4. A background simulator adds a new telemetry interval every five seconds.
5. Every interval is analyzed, persisted, and reflected in the dashboard automatically.

## Sign in and domain isolation

The application now includes session-based login. Every operator is assigned to one domain; all metrics, alerts, anomaly history, fault predictions, and managed PCs/devices are automatically filtered to that domain. A `user_devices` assignment table also ensures that the **My PCs & Devices** page returns only endpoints assigned to the signed-in user, even if more operators are later added to the same domain.

| Username | Password | Domain |
| --- | --- | --- |
| `north.operator` | `Demo@123` | North Campus |
| `lab.operator` | `Demo@123` | Research Lab |
| `corp.operator` | `Demo@123` | Corporate Office |

For production, set a strong secret key before launching: `$env:SENTINEL_SECRET_KEY='your-long-random-secret'`.

## REST API

`/api/dashboard`, `/api/metrics`, `/api/traffic`, `/api/anomalies`, `/api/fault-prediction`, `/api/devices`, `/api/alerts`, and `/api/simulate` return JSON. Use `/api/simulate` to immediately generate one telemetry interval for demonstration.

## Project layout

- `services/traffic_simulator.py` — realistic traffic + labelled training data
- `models/` — ML training, persistence, and inference classes
- `app.py` — Flask application, SQLite persistence, APIs, and simulator lifecycle
- `templates/` and `static/` — responsive NOC operator dashboard

The dashboard intentionally keeps model performance details off the main operator page; they appear under Fault Prediction.

