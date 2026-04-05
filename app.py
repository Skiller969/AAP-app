import json
import os
import yfinance as yf
from datetime import datetime
import streamlit as st
import numpy as np

# calcs for rsi and moving averages
def get_techs(prices):
    if len(prices) < 20: 
        return None
        
    p_arr = np.array(prices)
    short_ma = np.mean(p_arr[-5:])
    long_ma = np.mean(p_arr[-20:])
    
    # calc rsi 14
    diffs = np.diff(p_arr[-15:])
    gains = diffs[diffs >= 0].sum() / 14
    losses = -diffs[diffs < 0].sum() / 14
    
    if losses == 0:
        rsi_val = 100.0
    else:
        rs = gains / losses
        rsi_val = 100.0 - (100.0 / (1.0 + rs))
        
    return {'short': short_ma, 'long': long_ma, 'rsi': rsi_val}

# check if we should buy or sell
def check_signals(techs, sentiment):
    if not techs:
        return "HOLD", "not enough data points"
        
    total_score = 0
    why = []
    
    # moving average cross
    if techs['short'] > techs['long']:
        total_score += 1
        why.append("bullish ma")
    elif techs['short'] < techs['long']:
        total_score -= 1
        why.append("bearish ma")
        
    # rsi extremes
    if techs['rsi'] < 30:
        total_score += 1
        why.append("oversold")
    elif techs['rsi'] > 70:
        total_score -= 1
        why.append("overbought")
        
    # add sentiment
    if sentiment > 0:
        total_score += 1
        why.append("good news")
    elif sentiment < 0:
        total_score -= 1
        why.append("bad news")
        
    if total_score >= 2:
        return "BUY", " and ".join(why)
    if total_score <= -2:
        return "SELL", " and ".join(why)
    
    return "HOLD", "nothing special"


def get_logs():
    if not os.path.exists("trading_log.json"): 
        return []
    try:
        with open("trading_log.json", "r") as f:
            return json.load(f)
    except:
        # just return empty if file is messed up
        return []

def safe_log(act, pr, reasons, sym):
    logs = get_logs()
    
    # check if we already logged this exact thing recently
    if len(logs) > 0:
        latest = logs[-1]
        if latest['action'] == act and latest['symbol'] == sym:
            last_t = datetime.fromisoformat(latest['timestamp'])
            if (datetime.now() - last_t).total_seconds() < 3600:
                # print("skipping log to avoid spam")
                return 
                
    curr_trade = {
        "timestamp": datetime.now().isoformat(),
        "symbol": sym,
        "action": act,
        "price": pr,
        "reason": reasons
    }
    logs.append(curr_trade)
    
    with open("trading_log.json", "w") as f:
        json.dump(logs, f, indent=2)


st.set_page_config(page_title="My Trading Bot", layout="wide")

st.title("Trading Bot Dashboard")
st.write("check your stocks or crypto here.")

with st.sidebar:
    st.header("Settings")
    sym = st.text_input("Ticker (AAPL, BTC-USD etc):", value="AAPL").upper().strip()
    
    # basic check for crypto/forex
    if "=" in sym or "-" in sym:
        m_type = "forex"
    else:
        m_type = "stock"
    
    run_btn = st.button("Analyze", use_container_width=True)

if run_btn or sym:
    st.subheader(f"Looking at {sym}")
    
    with st.spinner('Loading data...'):
        try:
            t = yf.Ticker(sym)
            interval = "1h" if m_type == "forex" else "5m"
            
            # get last 5 days
            df = t.history(period="5d", interval=interval)
            
            if df.empty:
                st.error("Couldnt get data. Check symbol.")
            else:
                closing_prices = df["Close"].tolist()
                curr_p = float(closing_prices[-1])
                
                # fake news for sentiment 
                news_titles = [
                    f"volume on {sym} is going up",
                    f"market is crazy affecting {sym}",
                    "waiting for earnings to drop"
                ]
                
                # quick sentiment check 
                pos_words = ['surge', 'gain', 'rally', 'jump', 'rise', 'growth', 'bullish', 'increase']
                neg_words = ['fall', 'drop', 'crash', 'loss', 'decline', 'bearish', 'decrease']
                
                sent_score = 0
                for article in news_titles:
                    words = article.lower()
                    for pw in pos_words:
                        if pw in words: sent_score += 1
                    for nw in neg_words:
                        if nw in words: sent_score -= 1

                tech_data = get_techs(closing_prices)
                
                if not tech_data:
                    st.warning("Not enough data points yet.")
                else:
                    action, why = check_signals(tech_data, sent_score)
                    
                    if action == "BUY" or action == "SELL":
                        safe_log(action, curr_p, why, sym)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Price", f"${curr_p:.2f}")
                    c2.metric("RSI", f"{tech_data['rsi']:.1f}")
                    c3.metric("Short MA", f"${tech_data['short']:.2f}")
                    c4.metric("Long MA", f"${tech_data['long']:.2f}")
                    
                    st.divider()
                    
                    st.subheader("Signal")
                    if action == "BUY":
                        st.success(f"**BUY** - {why}")
                    elif action == "SELL":
                        st.error(f"**SELL** - {why}")
                    else:
                        st.info(f"**HOLD** - {why}")
                        
                    st.line_chart(df["Close"])
                    
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()

st.subheader("Logs")
log_data = get_logs()
if log_data:
    # show newest first
    st.dataframe(log_data[::-1], use_container_width=True)
else:
    st.write("No trades logged yet.")
