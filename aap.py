import json
import logging
import os
import sys
import time
from datetime import datetime

import numpy as np
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class TradingBot:
    def __init__(self, symbol="AAPL", market_type="stock", interval=60):
        self.symbol = symbol
        self.market_type = market_type
        self.interval = interval
        self.log_file = "trading_log.json"
        
        self.price_history = []
        self.trade_log = self._load_history()
        self.last_news = []
        self.last_news_time = 0

    def _load_history(self):
        if not os.path.exists(self.log_file):
            return []
        try:
            with open(self.log_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _save_trade(self, action, price, reason):
        trade = {
            "timestamp": datetime.now().isoformat(),
            "symbol": self.symbol,
            "action": action,
            "price": price,
            "reason": reason
        }
        self.trade_log.append(trade)
        with open(self.log_file, "w") as f:
            json.dump(self.trade_log, f, indent=2)

    def fetch_price(self):
        try:
            # yfinance occasionally outputs warnings to stdout/stderr
            ticker = yf.Ticker(self.symbol)
            period = "1d"
            intv = "1h" if self.market_type == "forex" else "5m"
            data = ticker.history(period=period, interval=intv)
            if data.empty:
                return None
            return float(data["Close"].iloc[-1])
        except Exception as e:
            logging.error(f"Failed to fetch price data: {e}")
            return None

    def fetch_news(self):
        # Simulated news headlines; in a real app, integrate a news API here
        return [
            f"{self.symbol} trading volume increases",
            f"Market volatility affects {self.symbol}",
            "Investors await upcoming earnings reports"
        ]

    def analyze_sentiment(self, news):
        if not news:
            return 0
            
        positive = {'surge', 'gain', 'rally', 'jump', 'rise', 'growth', 'bullish', 'increase'}
        negative = {'fall', 'drop', 'crash', 'loss', 'decline', 'bearish', 'decrease'}
        
        score = 0
        for article in news:
            text = article.lower()
            score += sum(1 for w in positive if w in text)
            score -= sum(1 for w in negative if w in text)
        return score

    def get_technical_indicators(self, prices):
        if len(prices) < 20:
            return None
            
        arr = np.array(prices)
        short_ma = np.mean(arr[-5:])
        long_ma = np.mean(arr[-20:])
        
        # 14-period RSI
        deltas = np.diff(arr[-15:])
        gains = deltas[deltas >= 0].sum() / 14
        losses = -deltas[deltas < 0].sum() / 14
        
        if losses == 0:
            rsi = 100.0
        else:
            rs = gains / losses
            rsi = 100.0 - (100.0 / (1.0 + rs))
            
        return {
            'short_ma': short_ma,
            'long_ma': long_ma,
            'rsi': rsi
        }

    def evaluate(self, price, indicators, sentiment_score):
        if not indicators:
            return "HOLD", "Insufficient data"
            
        score = 0
        reasons = []
        
        if indicators['short_ma'] > indicators['long_ma']:
            score += 1
            reasons.append("Bullish MA crossover")
        elif indicators['short_ma'] < indicators['long_ma']:
            score -= 1
            reasons.append("Bearish MA crossover")
            
        if indicators['rsi'] < 30:
            score += 1
            reasons.append("Oversold RSI")
        elif indicators['rsi'] > 70:
            score -= 1
            reasons.append("Overbought RSI")
            
        if sentiment_score > 0:
            score += 1
            reasons.append("Positive sentiment")
        elif sentiment_score < 0:
            score -= 1
            reasons.append("Negative sentiment")
            
        if score >= 2:
            return "BUY", ", ".join(reasons)
        if score <= -2:
            return "SELL", ", ".join(reasons)
        return "HOLD", "Neutral signals"

    def run(self):
        logging.info(f"Initialized agent for {self.symbol} ({self.market_type})")
        try:
            while True:
                price = self.fetch_price()
                if price is not None:
                    self.price_history.append(price)
                    if len(self.price_history) > 100:
                        self.price_history.pop(0)

                now = time.time()
                if now - self.last_news_time > 300:
                    self.last_news = self.fetch_news()
                    self.last_news_time = now

                if len(self.price_history) >= 20:
                    sentiment = self.analyze_sentiment(self.last_news)
                    indicators = self.get_technical_indicators(self.price_history)
                    action, reason = self.evaluate(price, indicators, sentiment)
                    
                    logging.info(f"Price: ${price:.2f} | RSI: {indicators['rsi']:.1f} | Action: {action}")
                    if action in ("BUY", "SELL"):
                        logging.info(f"Signal reason: {reason}")
                        self.trace_signal(action, price, reason)
                else:
                    logging.info(f"Price: {f'${price:.2f}' if price else 'N/A'} (Gathering data: {len(self.price_history)}/20)")
                    
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            logging.info("Exiting...")
            sys.exit(0)

    def trace_signal(self, action, price, reason):
        # Prevent logging the same trade repeatedly
        if self.trade_log:
            last_trade = self.trade_log[-1]
            if last_trade['action'] == action and last_trade['symbol'] == self.symbol:
                last_time = datetime.fromisoformat(last_trade['timestamp'])
                if (datetime.now() - last_time).total_seconds() < 3600:
                    return
        self._save_trade(action, price, reason)

def main():
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
        market_type = "forex" if "=" in symbol else "stock"
    else:
        symbol = input("Enter symbol to track (e.g. AAPL, MSFT, EURUSD=X): ").strip().upper()
        if not symbol:
            symbol = "AAPL"
        market_type = "forex" if "=" in symbol else "stock"
        
    bot = TradingBot(symbol=symbol, market_type=market_type)
    bot.run()

if __name__ == "__main__":
    main()