from datetime import datetime

class RiskEngine:
    """Risk management engine tracking PnL, drawdown, and liquidation"""
    
    def __init__(self, max_drawdown_percent: float = 5.0):
        self.max_drawdown_percent = max_drawdown_percent
        self.peak_value = None
        self.initial_value = None
        self.current_value = 0
        self.drawdown_percent = 0.0
        self.liquidation_triggered = False
        self.liquidation_history = []
    
    def update_portfolio_value(self, current_value: float):
        """Update portfolio value and calculate risk metrics"""
        self.current_value = current_value
        
        if self.peak_value is None:
            self.peak_value = current_value
            self.initial_value = current_value
        
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        if self.peak_value > 0:
            self.drawdown_percent = (
                (self.peak_value - current_value) / self.peak_value
            ) * 100
        
        pnl = 0
        pnl_percent = 0
        if self.initial_value and self.initial_value > 0:
            pnl = current_value - self.initial_value
            pnl_percent = (pnl / self.initial_value) * 100
        
        liquidation_triggered = self.drawdown_percent >= self.max_drawdown_percent
        
        risk_status = {
            "current_value": current_value,
            "peak_value": self.peak_value,
            "initial_value": self.initial_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "drawdown_percent": self.drawdown_percent,
            "max_drawdown_allowed": self.max_drawdown_percent,
            "liquidation_triggered": liquidation_triggered,
            "timestamp": datetime.now().isoformat()
        }
        
        if liquidation_triggered and not self.liquidation_triggered:
            self.liquidation_triggered = True
            self.liquidation_history.append({
                "event": "liquidation_triggered",
                "drawdown": self.drawdown_percent,
                "timestamp": datetime.now().isoformat()
            })
        
        return risk_status
    
    def reset_peak(self):
        """Reset peak value after manual intervention"""
        self.peak_value = self.current_value
        self.liquidation_triggered = False
    
    def get_holdings_to_liquidate(self, holdings):
        """Determine which holdings to sell during liquidation"""
        if not self.liquidation_triggered:
            return []
        
        to_liquidate = []
        for holding in holdings:
            symbol = holding["symbol"].upper()
            quantity = float(holding.get("quantity", 0))
            
            if quantity > 0:
                to_liquidate.append({
                    "symbol": symbol,
                    "quantity": quantity,
                    "holding_data": holding
                })
        
        return to_liquidate