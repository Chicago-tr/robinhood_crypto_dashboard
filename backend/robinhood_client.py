import requests
import base64
import time
import uuid
import nacl.signing
from config import Config

class RobinhoodCryptoApi:
    """
    Base URL: https://trading.robinhood.com
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.api_key = Config.ROBINHOOD_API_KEY
        self.private_key_base64 = Config.ROBINHOOD_PRIVATE_KEY
        self._setup_session()
    
    def _setup_session(self):
        """Sets session headers, internal use"""

        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def _generate_signature(self, path: str, method: str, body: dict | None = None):
        """
        Creates the API signatures needed for requests
        Check Robinhood API documentation for details on the process

        Returns:
            tuple: (cur_timestamp, signature)
        """
        if body is None:
            body = {}

        cur_timestamp = str(int(time.time()))
        
        # Decode private key from base64
        private_key_seed = base64.b64decode(self.private_key_base64)
        private_key = nacl.signing.SigningKey(private_key_seed)
        private_key_seed = None
        
        # Sign message
        message = f"{self.api_key}{cur_timestamp}{path}{method}{body}"
        signed = private_key.sign(message.encode("utf-8"))
        
        # Generate signature header
        signature = base64.b64encode(signed.signature).decode("utf-8")
        
        return cur_timestamp, signature
    
    def _make_request(self, path: str, method: str = "GET", body: dict | None = None):
        """ 
        Args:
            path: API path endpoint
            method: HTTP method (Get/Post only)
            body: Request body
            
        Returns:
            Response json data as dict
        """
        if body is None:
            body = {}

        # Get the signature
        cur_timestamp, signature = self._generate_signature(path, method, body)
        
        
        headers = {
            "x-api-key": self.api_key,
            "x-signature": signature,
            "x-timestamp": cur_timestamp,
            "Content-Type": "application/json"
        }
        
        
        url = f"{Config.BASE_URL}{path}"
        
        if method == "GET":
            response = self.session.get(url, headers=headers)
        elif method == "POST":
            response = self.session.post(url, headers=headers, json=body if body else None)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        # Check for errors
        if response.status_code != 200 and response.status_code != 201:
            raise Exception(f"API request failed ({response.status_code}): {response.text}")
        
        return response.json()
    
    def get_crypto_account(self):
        """
        Obtain account information
        """
        path = "/api/v1/crypto/trading/accounts/"
        return self._make_request(path, "GET")
    
    def get_crypto_holdings(self):
        """
        Get all crypto holdings with quantities
        """
        path = "/api/v1/crypto/trading/holdings/"
        data = self._make_request(path, "GET")

        return data.get("results", [])
    
    def get_crypto_price(self, symbol: str):
        """
        Get best bid/ask price for a crypto asset

        Args:
            symbol: Crypto symbol ('BTC', 'ETH', etc.)
            
        Returns:
            Current bid price
        """
        path = f"/api/v1/crypto/marketdata/best_bid_ask/?symbol={symbol}-USD"
        data = self._make_request(path, "GET")
        
        # Extract bid price
        market_data = data.get("results", [])
        if market_data:
            return float(market_data[0].get("price", 0))
        return 0.0
    
    def get_mult_crypto_prices(self, symbols = None):
        """
        Get prices for multiple crypto assets
        
        Args:
            symbols: List of crypto symbols (default: get all USD pairs)
            
        Returns:
            Dict mapping symbol to price
        """
        #builds the path with every symbol pair 
        if symbols:
            symbol_params = "&".join([f"symbol={s}-USD" for s in symbols])
            path = f"/api/v1/crypto/marketdata/best_bid_ask/?{symbol_params}"
        else:
            # Get all available symbols
            path = "/api/v1/crypto/marketdata/best_bid_ask/"
        
        data = self._make_request(path, "GET")
        
        prices = {}
        for result in data.get("results", []):
            symbol = result.get("symbol", "").replace("-USD", "")

            price = float(result.get("price", 0))
            prices[symbol] = price
        
        return prices
    
    def get_order_history(self):
        """
        Crypto orders only
        """
        path = "/api/v1/crypto/trading/orders/"
        data = self._make_request(path, "GET")
        return data.get("results", [])
    
    def place_crypto_sell_order(
        self, 
        symbol: str, 
        quantity: float, 
    ):
        """
        Place a market sell order for crypto
        
        Args:
            symbol: Crypto symbol ('BTC', 'ETH', etc.)
            quantity: Amount to sell
            order_type: 'market' or 'limit'
            
        Returns:
            Order confirmation
        """
        path = "/api/v1/crypto/trading/orders/"
        
        # Build request body
        body = {
            "symbol": f"{symbol}-USD",
            "client_order_id": str(uuid.uuid4()),
            "side": "sell",
            "type": "market",
            "market_order_config":{"quantity": str(quantity)},
        }
        
        return self._make_request(path, "POST", body)
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending crypto order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        path = f"/api/v1/crypto/trading/orders/{order_id}/cancel"
        resp = self._make_request(path, "POST")

        if resp.status_code != 200:
            raise ValueError("Failed to cancel order")
        
        return True
    
    def get_portfolio_value(self) -> float:
        """
        Calculate total portfolio value in USD
        
        Combines crypto holdings + cash balance
        """
        account = self.get_crypto_account()
        holdings = self.get_crypto_holdings()
        prices = self.get_mult_crypto_prices()
        
        # Cash balance (from account)
        cash = float(account.get("balance", 0))
        
        # Crypto value
        crypto_value = 0
        for holding in holdings:
            symbol = holding.get("symbol", "").replace("-USD", "")
            quantity = float(holding.get("quantity", 0))
            price = prices.get(symbol, 0)
            crypto_value += quantity * price
        
        return cash + crypto_value
    
    def get_account_balance(self) -> float:
        """
        Get buying power (proxy for balance, can't pull actual balance) from account
        
        Returns:
            Cash balance in USD
        """
        account = self.get_crypto_account()
        return float(account.get("buying_power", 0))