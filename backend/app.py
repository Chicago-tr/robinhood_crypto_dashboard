from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from pathlib import Path
import threading
import time



from backend.config import Config
from backend.robinhood_client import RobinhoodCryptoApi
from backend.risk_engine import RiskEngine
from backend.reconciliation import PositionReconciliation

FRONTEND_DIR = Path(__file__).resolve().parent.parent / 'frontend'
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path='')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

# Initialize clients
app.robinhood_client = None
app.risk_engine = None
app.reconciliation = PositionReconciliation()
app.risk_status_cache = None
app.cache_lock = threading.Lock()

def initialize_system():
    """Initialize Robinhood client, risk engine, and reconciliation"""
    try:
        Config.validate()
        app.robinhood_client = RobinhoodCryptoApi()
        app.risk_engine = RiskEngine(max_drawdown_percent=Config.MAX_DRAWDOWN_PERCENT)
        print("System initialized successfully")
        print(f"Reconciliation snapshots saved to: {app.reconciliation.snapshot_dir}")
    except Exception as e:
        print(f"Initialization failed: {e}")
        
        app.robinhood_client = None
        app.risk_engine = None

def update_risk_status():
    """Background task to update risk status periodically"""
    while True:
        try:
            if app.robinhood_client and app.risk_engine:
                portfolio_value = app.robinhood_client.get_portfolio_value()
                
                with app.cache_lock:
                    status = app.risk_engine.update_portfolio_value(portfolio_value)
                    app.risk_status_cache = status
                    
                    if status["liquidation_triggered"]:
                        execute_liquidation()
        except Exception as e:
            print(f"Risk update error: {e}")
        
        time.sleep(30)

def execute_liquidation():
    """Execute liquidation of all positions"""
    try:
        holdings = app.robinhood_client.get_crypto_holdings()
        to_liquidate = app.risk_engine.get_holdings_to_liquidate(holdings)
        
        liquidation_results = []
        for position in to_liquidate:
            try:
                order = app.robinhood_client.place_crypto_sell_order(
                    position["symbol"],
                    position["quantity"]
                )
                liquidation_results.append({
                    "symbol": position["symbol"],
                    "quantity": position["quantity"],
                    "order_id": order.get("id"),
                    "status": "success"
                })
            except Exception as e:
                liquidation_results.append({
                    "symbol": position["symbol"],
                    "status": "failed",
                    "error": str(e)
                })
        
        print(f"Liquidation complete: {liquidation_results}")
        app.risk_engine.reset_peak()
        
    except Exception as e:
        print(f"Liquidation error: {e}")

# ============ API ENDPOINTS ============

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "initialized": app.robinhood_client is not None and app.risk_engine is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/portfolio')
def get_portfolio():
    """Get current portfolio data"""
    if not app.robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        
        holdings = app.robinhood_client.get_crypto_holdings()
        

        prices = app.robinhood_client.get_mult_crypto_prices()
        

        account = app.robinhood_client.get_crypto_account()
        
        portfolio_value = app.robinhood_client.get_portfolio_value()
       
        cash_balance = float(account.get("balance", 0))
        crypto_value = portfolio_value - cash_balance
        cost_basis = app.robinhood_client.get_crypto_cost_basis()

        holdings_with_value = []
        for holding in holdings:
            symbol = holding["asset_code"]
            quantity = float(holding.get("total_quantity", 0))
            price = prices.get(symbol, 0)
            value = quantity * price
            
            holdings_with_value.append({
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "value": value,
                "name": holding.get("asset_code", symbol)
            })
        # Calculate PnL based on cost basis, not portfolio injection
        pnl = 0
        pnl_percent = 0
        if cost_basis > 0:
            pnl = crypto_value - cost_basis
            pnl_percent = (pnl / cost_basis) * 100

        return jsonify({
            "total_value": portfolio_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "cash_balance": cash_balance,
            "crypto_value": crypto_value,
            "cost_basis": cost_basis,
            "holdings": holdings_with_value,
            "prices": prices,
            "peak_value": app.risk_engine.peak_value if app.risk_engine and app.risk_engine.peak_value else portfolio_value,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/risk')
def get_risk_status():
    """Get current risk metrics"""
    with app.cache_lock:
        if app.risk_status_cache:
            return jsonify(app.risk_status_cache)
        return jsonify({"error": "No data available"}), 404

@app.route('/api/risk/settings', methods=['POST'])
def update_risk_settings():
    """Update risk settings"""
    if not app.risk_engine:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        data = request.json
        max_drawdown = data.get("max_drawdown_percent")
        
        if max_drawdown:
            app.risk_engine.max_drawdown_percent = float(max_drawdown)
        
        return jsonify({
            "success": True,
            "max_drawdown_percent": app.risk_engine.max_drawdown_percent
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders')
def get_orders():
    """Get order history"""
    if not app.robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        orders = app.robinhood_client.get_order_history()
        return jsonify({
            "orders": orders[:50],
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reset-peak')
def reset_peak():
    """Reset peak value (manual intervention)"""
    if not app.risk_engine:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        app.risk_engine.reset_peak()
        return jsonify({"success": True, "message": "Peak value reset"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ RECONCILIATION ENDPOINTS ============

@app.route('/api/snapshot')
def save_snapshot():
    """Save current positions as daily snapshot"""
    if not app.robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        portfolio = app.robinhood_client.get_portfolio()
        snapshot_path = app.reconciliation.save_daily_snapshot(portfolio)
        
        return jsonify({
            "success": True,
            "snapshot_path": snapshot_path,
            "timestamp": datetime.now().isoformat(),
            "total_value": portfolio["total_value"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reconcile')
def reconcile_positions():
    """Reconcile current positions against previous snapshot"""
    if not app.robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        portfolio = app.robinhood_client.get_portfolio()
        reconciliation_report = app.reconciliation.reconcile_with_previous(
            portfolio["holdings"],
            portfolio["cash_balance"]
        )
        
        return jsonify(reconciliation_report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/daily-report')
def generate_daily_report():
    """Generate CSV daily position report"""
    if not app.robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        portfolio = app.robinhood_client.get_portfolio()
        report_path = app.reconciliation.generate_daily_report_csv(portfolio)
        
        return jsonify({
            "success": True,
            "report_path": report_path,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/latest-snapshot')
def get_latest_snapshot():
    """Get the most recent snapshot"""
    try:
        snapshot = app.reconciliation.get_latest_snapshot()
        
        if snapshot:
            return jsonify({
                "success": True,
                "snapshot": snapshot
            })
        else:
            return jsonify({
                "success": False,
                "message": "No snapshots found"
            }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/test-connection')
def test_connection():
    if not app.robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    try:
        account = app.robinhood_client.get_crypto_account()
        return jsonify({
            "success": True,
            "account": account
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def start_dashboard():
    print("=== Starting Flask app ===")
    initialize_system()
    print("=== Finished initialize_system() ===")
    if app.robinhood_client and app.risk_engine:
        update_thread = threading.Thread(target=update_risk_status, daemon=True)
        update_thread.start()
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)

if __name__ == '__main__':
    start_dashboard()