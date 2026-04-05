import json
import os
from datetime import datetime
import streamlit as st
import numpy as np
import yfinance as yf

# -------------- BOT LOGIC ----------------

def get_technical_indicators(prices):
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

def evaluate(indicators, sentiment_score):
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

def _load_history():
    if not os.path.exists("trading_log.json"):
        return []
    try:
        with open("trading_log.json", "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def _save_trade(action, price, reason, symbol):
    log = _load_history()
    # Prevent duplicate identical consecutive trades
    if log:
        if log[-1]['action'] == action and log[-1]['symbol'] == symbol:
            last_time = datetime.fromisoformat(log[-1]['timestamp'])
            if (datetime.now() - last_time).total_seconds() < 3600:
                return # Don't log again
                
    trade = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "action": action,
        "price": price,
        "reason": reason
    }
    log.append(trade)
    with open("trading_log.json", "w") as f:
        json.dump(log, f, indent=2)

# -------------- WEB UI ----------------

st.set_page_config(page_title="AI Trading Bot", page_icon="📈", layout="wide")

st.title("🤖 AI Trading Bot Dashboard")
st.markdown("Analyze technicals, RSI, and sentiment instantly!")

# Sidebar for controls
with st.sidebar:
    st.header("Search Settings")
    symbol = st.text_input("Enter Symbol (e.g. AAPL, MSFT, BTC-USD):", value="AAPL").upper().strip()
    market_type = "forex" if "=" in symbol or "-" in symbol else "stock"
    analyze_button = st.button("Run Analysis Now", use_container_width=True)

# Main App Body
if analyze_button or symbol:
    st.subheader(f"Current Analysis for {symbol}")
    
    with st.spinner('Fetching latest market data...'):
        try:
            ticker = yf.Ticker(symbol)
            intv = "1h" if market_type == "forex" else "5m"
            
            # Instead of waiting 20 minutes to gather 20 data points like the terminal bot, 
            # we instantly fetch the last 5 days of history to calculate RSI/MA right away!
            data = ticker.history(period="5d", interval=intv)
            
            if data.empty:
                st.error("Failed to fetch data. Make sure the ticker symbol is correct.")
            else:
                prices = data["Close"].tolist()
                current_price = float(prices[-1])
                
                # Fetch dummy news (As in your original script)
                news = [
                    f"{symbol} trading volume increases",
                    f"Market volatility affects {symbol}",
                    "Investors await upcoming earnings reports"
                ]
                
                # Sentiment processing
                positive = {'surge', 'gain', 'rally', 'jump', 'rise', 'growth', 'bullish', 'increase'}
                negative = {'fall', 'drop', 'crash', 'loss', 'decline', 'bearish', 'decrease'}
                sentiment_score = 0
                for article in news:
                    text = article.lower()
                    sentiment_score += sum(1 for w in positive if w in text)
                    sentiment_score -= sum(1 for w in negative if w in text)

                # Get Indicators
                ind = get_technical_indicators(prices)
                
                if not ind:
                    st.warning("Not enough market data to calculate technical indicators.")
                else:
                    action, reason = evaluate(ind, sentiment_score)
                    
                    # Log the trade if it's Buy or Sell
                    if action in ["BUY", "SELL"]:
                        _save_trade(action, current_price, reason, symbol)
                    
                    # --- DISPLAY RESULTS STATS ---
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Current Price", f"${current_price:.2f}")
                    col2.metric("RSI (14)", f"{ind['rsi']:.1f}")
                    col3.metric("Short MA (5)", f"${ind['short_ma']:.2f}")
                    col4.metric("Long MA (20)", f"${ind['long_ma']:.2f}")
                    
                    st.divider()
                    
                    # --- DISPLAY THE BOT SIGNAL ---
                    st.subheader("Bot Recommendation:")
                    if action == "BUY":
                        st.success(f"### 🟩 **BUY** \n**Reason:** {reason}")
                    elif action == "SELL":
                        st.error(f"### 🟥 **SELL** \n**Reason:** {reason}")
                    else:
                        st.info(f"### 🟨 **HOLD** \n**Reason:** {reason}")
                        
                    # --- DISPLAY CHART ---
                    st.subheader("Recent Price Chart")
                    st.line_chart(data["Close"])
                    
        except Exception as e:
            st.error(f"An error occurred: {e}")

st.divider()

# --- DISPLAY TRADING LOGS ---
st.subheader("Trade Log History")
history = _load_history()
if history:
    # Reverse so newest is first
    st.dataframe(history[::-1], use_container_width=True)
else:
    st.write("No trades have been executed yet.")
