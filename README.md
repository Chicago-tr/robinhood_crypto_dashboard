# Robinhood Crypto Trading Dashboard

A full-stack dashboard built for Robinhood's crypto trading platform. Tracks portfolio value, PnL, and drawdown in real time. Can automatically liquidate crypto positions when a max-loss threshold is reached. Generates daily positions reports and reconciles positions against prior snapshots and flags missing positions/discrepancies as well.

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
│   └── reconciliation.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── position_snapshots/
├── .env.example
└── README.md
```

Screenshots coming soon...