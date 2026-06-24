from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import threading
import time

from config import Config
from robinhood_client import RobinhoodCryptoApi
from risk_engine import RiskEngine
from reconciliation import PositionReconciliation

app = Flask(__name__)
CORS(app)

# Initialize clients
robinhood_client = None
risk_engine = None
reconciliation = PositionReconciliation()
risk_status_cache = None
cache_lock = threading.Lock()

def initialize_system():
    """Initialize Robinhood client, risk engine, and reconciliation"""
    try:
        Config.validate()
        robinhood_client = RobinhoodCryptoApi()
        risk_engine = RiskEngine(max_drawdown_percent=Config.MAX_DRAWDOWN_PERCENT)
        print("System initialized successfully")
        print(f"Reconciliation snapshots saved to: {reconciliation.snapshot_dir}")
    except Exception as e:
        print(f"Initialization failed: {e}")
        robinhood_client = None
        risk_engine = None

def update_risk_status():
    """Background task to update risk status periodically"""
    while True:
        try:
            if robinhood_client and risk_engine:
                portfolio_value = robinhood_client.get_portfolio_value()
                
                with cache_lock:
                    status = risk_engine.update_portfolio_value(portfolio_value)
                    risk_status_cache = status
                    
                    if status["liquidation_triggered"]:
                        execute_liquidation()
        except Exception as e:
            print(f"Risk update error: {e}")
        
        time.sleep(30)

def execute_liquidation():
    """Execute liquidation of all positions"""
    try:
        holdings = robinhood_client.get_crypto_holdings()
        to_liquidate = risk_engine.get_holdings_to_liquidate(holdings)
        
        liquidation_results = []
        for position in to_liquidate:
            try:
                order = robinhood_client.place_crypto_sell_order(
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
        risk_engine.reset_peak()
        
    except Exception as e:
        print(f"Liquidation error: {e}")

# ============ API ENDPOINTS ============

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "initialized": robinhood_client is not None and risk_engine is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/portfolio')
def get_portfolio():
    """Get current portfolio data"""
    if not robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        holdings = robinhood_client.get_crypto_holdings()
        prices = robinhood_client.get_crypto_prices()
        account = robinhood_client.get_crypto_account()
        
        portfolio_value = robinhood_client.get_portfolio_value()
        
        holdings_with_value = []
        for holding in holdings:
            symbol = holding["symbol"].replace("-USD", "")
            quantity = float(holding.get("quantity", 0))
            price = prices.get(symbol, 0)
            value = quantity * price
            
            holdings_with_value.append({
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "value": value,
                "name": holding.get("symbol", symbol)
            })
        
        return jsonify({
            "total_value": portfolio_value,
            "cash_balance": float(account.get("balance", 0)),
            "crypto_value": portfolio_value - float(account.get("balance", 0)),
            "holdings": holdings_with_value,
            "prices": prices,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/risk')
def get_risk_status():
    """Get current risk metrics"""
    with cache_lock:
        if risk_status_cache:
            return jsonify(risk_status_cache)
        return jsonify({"error": "No data available"}), 404

@app.route('/api/risk/settings', methods=['POST'])
def update_risk_settings():
    """Update risk settings"""
    if not risk_engine:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        data = request.json
        max_drawdown = data.get("max_drawdown_percent")
        
        if max_drawdown:
            risk_engine.max_drawdown_percent = float(max_drawdown)
        
        return jsonify({
            "success": True,
            "max_drawdown_percent": risk_engine.max_drawdown_percent
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders')
def get_orders():
    """Get order history"""
    if not robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        orders = robinhood_client.get_order_history()
        return jsonify({
            "orders": orders[:50],
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reset-peak')
def reset_peak():
    """Reset peak value (manual intervention)"""
    if not risk_engine:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        risk_engine.reset_peak()
        return jsonify({"success": True, "message": "Peak value reset"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ RECONCILIATION ENDPOINTS ============

@app.route('/api/snapshot')
def save_snapshot():
    """Save current positions as daily snapshot"""
    if not robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        portfolio = robinhood_client.get_portfolio()
        snapshot_path = reconciliation.save_daily_snapshot(portfolio)
        
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
    if not robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        portfolio = robinhood_client.get_portfolio()
        reconciliation_report = reconciliation.reconcile_with_previous(
            portfolio["holdings"],
            portfolio["cash_balance"]
        )
        
        return jsonify(reconciliation_report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/daily-report')
def generate_daily_report():
    """Generate CSV daily position report"""
    if not robinhood_client:
        return jsonify({"error": "System not initialized"}), 500
    
    try:
        portfolio = robinhood_client.get_portfolio()
        report_path = reconciliation.generate_daily_report_csv(portfolio)
        
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
        snapshot = reconciliation.get_latest_snapshot()
        
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

if __name__ == '__main__':
    initialize_system()
    
    if robinhood_client and risk_engine:
        update_thread = threading.Thread(target=update_risk_status, daemon=True)
        update_thread.start()
    
    app.run(host='0.0.0.0', port=Config.PORT, debug=True)