# Robinhood Crypto Trading Dashboard

A full-stack dashboard built for Robinhood's crypto trading platform. Tracks portfolio value, PnL, and drawdown in real time. Can automatically liquidate crypto positions when a max-loss threshold is reached. Generates daily position reports and reconciles positions against prior snapshots and flags missing positions/discrepancies as well.

Docker support included as well.

## Features
- Live portfolio tracking for crypto holdings and buying power (Can't access account balance using Robinhood's Api currently)
- PnL and drawdown monitoring with a configurable risk limit.
- Automated liquidation when portfolio drawdown exceeds the threshhold
- Daily position snapshots and reconciliation reports
- CSV export for position reporting and auditing
- Web dashboard for viewing holdings, risk status, and order history

## How it Works
- The backend authenticates with Robinhood's Crypto Trading API
- Pulls account data, holdings, orders, and current market data
- Risk enginge calculates features like portfolio value, PnL, peak portfolio value, and drawdown
- If drawdown hits the configured drawdown limit % sell orders will be submitted to liquidate positons
- Reconciliation module saves daily snapshots and compares current positions to prior snapshots
- Frontend displays everything in a dashboard

## Project Structure
```bash
robinhood_crypto_dashboard/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── robinhood_client.py
│   ├── risk_engine.py
│   ├── reconciliation.py
│   ├── requirements.txt
│   ├── .env.example
│   └── __init__.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── position_snapshots/
├── run.py
└── README.md
```

## Setup
1. Clone the repository and change into the project directory:

```bash
git clone https://github.com/<username>/robinhood_crypto_dashboard.git
cd robinhood_crypto_dashboard
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Copy the example environment file and update the values:

```bash
cp backend/.env.example backend/.env
```

4. Set your Robinhood API credentials in `backend/.env`:

```bash
ROBINHOOD_API_KEY=your_api_key
ROBINHOOD_PRIVATE_KEY=your_private_key
MAX_DRAWDOWN_PERCENT=5.0
PORT=5000
```

## Running the app
From the project root, start the full dashboard with:

```bash
python run.py
```

Then open the dashboard in a browser at:

```text
http://localhost:5000
```

## Docker
Or if you want to try it using Docker:

Build the image from the repo root:

```bash
docker build -t robinhood-crypto-dashboard .
```

Run the container with your environment file mounted:

```bash
docker run --rm -p 5000:5000 --env-file backend/.env robinhood-crypto-dashboard
```

A minimal `docker-compose.yml` for convenience:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:5000
```

## Notes
- The backend serves the frontend statically and exposes `/api/*` endpoints for the dashboard.
- `position_snapshots/` is used to store daily snapshots and generated reports.
- PnL is calculated from actual cost basis and current crypto market prices, so new purchases do not inflate profit calculations.
- The dashboard uses a lightweight chart view, risk monitoring, reconciliation, and order history display.



