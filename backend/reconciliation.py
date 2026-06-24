from datetime import datetime
import json
import os

class PositionReconciliation:
    """Handles position reconciliation and daily reporting"""
    
    def __init__(self, snapshot_dir="position_snapshots"):
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)
        self.previous_snapshot = None
    
    def save_daily_snapshot(self, portfolio_data):
        """
        Save end-of-day position snapshot
        
        Args:
            portfolio_data: From /api/portfolio endpoint
            
        Returns:
            Path to saved snapshot file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{self.snapshot_dir}/positions_{timestamp}.json"
        
        snapshot = {
            "snapshot_time": timestamp,
            "total_value": portfolio_data["total_value"],
            "cash_balance": portfolio_data["cash_balance"],
            "crypto_value": portfolio_data["crypto_value"],
            "positions": portfolio_data["holdings"],
            "market_prices": portfolio_data["prices"]
        }
        
        with open(filename, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        # Track for reconciliation
        self.previous_snapshot = snapshot
        
        return filename
    
    def reconcile_with_previous(self, current_holdings, cash_balance):
        """
        Reconcile current positions against previous snapshot
        
        Returns reconciliation report with discrepancies
        """
        if not self.previous_snapshot:
            return {
                "reconciled": False,
                "message": "No previous snapshot available. Save a snapshot first.",
                "discrepancies": [],
                "discrepancy_count": 0,
                "all_match": False
            }
        
        previous_positions = self.previous_snapshot["positions"]
        discrepancies = []
        
        # Build lookup dicts
        current_by_symbol = {h["symbol"]: h for h in current_holdings}
        previous_by_symbol = {p["symbol"]: p for p in previous_positions}
        
        # Check for missing positions (were held, now gone)
        for symbol, prev_pos in previous_by_symbol.items():
            if symbol not in current_by_symbol:
                discrepancies.append({
                    "type": "missing_position",
                    "symbol": symbol,
                    "previous_quantity": prev_pos["quantity"],
                    "current_quantity": 0,
                    "difference": -prev_pos["quantity"],
                    "severity": "high"
                })
        
        # Check for new positions (not held before, now held)
        for symbol, curr_pos in current_by_symbol.items():
            if symbol not in previous_by_symbol:
                discrepancies.append({
                    "type": "new_position",
                    "symbol": symbol,
                    "previous_quantity": 0,
                    "current_quantity": curr_pos["quantity"],
                    "difference": curr_pos["quantity"],
                    "severity": "low"
                })
        
        # Check for quantity changes
        for symbol, curr_pos in current_by_symbol.items():
            if symbol in previous_by_symbol:
                prev_qty = previous_by_symbol[symbol]["quantity"]
                curr_qty = curr_pos["quantity"]
                diff = curr_qty - prev_qty
                
                # Tolerance for rounding (0.000001)
                if abs(diff) > 0.000001:
                    discrepancies.append({
                        "type": "quantity_change",
                        "symbol": symbol,
                        "previous_quantity": prev_qty,
                        "current_quantity": curr_qty,
                        "difference": diff,
                        "severity": "medium"
                    })
        
        # Calculate value comparison
        previous_total = self.previous_snapshot["total_value"]
        current_crypto_value = sum(h["value"] for h in current_holdings)
        current_total = current_crypto_value + cash_balance
        
        value_diff = current_total - previous_total
        value_change_pct = (value_diff / previous_total * 100) if previous_total > 0 else 0
        
        return {
            "reconciled": True,
            "snapshot_comparison": {
                "previous_snapshot_time": self.previous_snapshot["snapshot_time"],
                "previous_total_value": previous_total,
                "current_total_value": current_total,
                "value_change": value_diff,
                "value_change_percent": value_change_pct
            },
            "discrepancies": discrepancies,
            "discrepancy_count": len(discrepancies),
            "all_match": len(discrepancies) == 0,
            "reconciliation_time": datetime.now().isoformat()
        }
    
    def generate_daily_report_csv(self, portfolio_data):
        """
        Generate CSV daily position report
        
        Returns:
            Path to CSV file
        """
        import csv
        
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"{self.snapshot_dir}/daily_report_{timestamp}.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "Report Date",
                "Total Portfolio Value",
                "Cash Balance",
                "Crypto Value"
            ])
            writer.writerow([
                timestamp,
                portfolio_data["total_value"],
                portfolio_data["cash_balance"],
                portfolio_data["crypto_value"]
            ])
            
            # Position details
            writer.writerow([])
            writer.writerow(["Position", "Symbol", "Quantity", "Price (USD)", "Value (USD)", "Name"])
            
            for holding in portfolio_data["holdings"]:
                writer.writerow([
                    "",
                    holding["symbol"],
                    holding["quantity"],
                    holding["price"],
                    holding["value"],
                    holding["name"]
                ])
            
            # Footer
            writer.writerow([])
            writer.writerow(["Snapshot Generated At", datetime.now().isoformat()])
        
        return filename
    
    def get_latest_snapshot(self):
        """Get the most recent snapshot file"""
        if not os.path.exists(self.snapshot_dir):
            return None
        
        files = [f for f in os.listdir(self.snapshot_dir) if f.startswith("positions_") and f.endswith(".json")]
        if not files:
            return None
        
        latest_file = sorted(files)[-1]
        latest_path = f"{self.snapshot_dir}/{latest_file}"
        
        with open(latest_path, 'r') as f:
            return json.load(f)