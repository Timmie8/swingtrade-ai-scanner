import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from textblob import TextBlob
import warnings
warnings.filterwarnings('ignore')

# Streamlit Pagina Configuratie
st.set_page_config(
    page_title="AI Swingtrade Scanner (1-5 Dagen)",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Live AI Swingtrade Scanner (1–5 Dagen)")
st.caption("Live analyse op basis van Sentiment, Volume Breakouts, Opties (PCR), Short Interest en Technische Indicatoren.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("⚙️ Instellingen & Watchlist")
user_input = st.sidebar.text_input(
    "Vul tickers in (gescheiden door komma's):",
    value="NVDA, TSLA, AMD, PLTR, AAPL"
)

tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

scan_button = st.sidebar.button("🚀 Start Live Scan", type="primary")

# --- CORE ANALYSE FUNCTIE ---
def get_live_swing_data(symbol):
    ticker = yf.Ticker(symbol)
    
    # 1. Live/Daily Data
    df = ticker.history(period="60d", interval="1d")
    if df.empty or len(df) < 20:
        return None
        
    info = ticker.info
    live_price = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2]
    day_change_pct = ((live_price - prev_close) / prev_close) * 100
    
    # 2. Volume Spike
    current_volume = df['Volume'].iloc[-1]
    avg_vol_20d = df['Volume'].rolling(20).mean().iloc[-1]
    vol_ratio = current_volume / avg_vol_20d if avg_vol_20d > 0 else 1.0
    
    # 3. Technische Indicatoren
    ema5 = ta.trend.ema_indicator(df['Close'], window=5).iloc[-1]
    ema15 = ta.trend.ema_indicator(df['Close'], window=15).iloc[-1]
    rsi = ta.momentum.rsi(df['Close'], window=14).iloc[-1]
    macd_diff = ta.trend.MACD(df['Close']).macd_diff().iloc[-1]
    
    # 4. Opties Put/Call Ratio
    pcr_volume = 1.0
    pcr_status = "Neutraal"
    try:
        if ticker.options:
            nearest_exp = ticker.options[0]
            opt_chain = ticker.option_chain(nearest_exp)
            calls_vol = opt_chain.calls['volume'].sum()
            puts_vol = opt_chain.puts['volume'].sum()
            if calls_vol > 0:
                pcr_volume = puts_vol / calls_vol
                if pcr_volume < 0.7: pcr_status = "Bullish (Call Heavy)"
                elif pcr_volume > 1.3: pcr_status = "Bearish (Put Heavy)"
    except Exception:
        pass

    # 5. Sentiment
    sentiment_score = 0
    try:
        news = ticker.news
        if news:
            scores = [TextBlob(item.get('title', '')).sentiment.polarity for item in news[:5]]
            sentiment_score = np.mean(scores)
    except Exception:
        pass
        
    short_pct = info.get('shortPercentOfFloat', 0) or 0
    sector = info.get('sector', 'Onbekend')
    
    # 6. AI Swing Scoring Model (1 - 10)
    score = 5.0
    if live_price > ema5 > ema15: score += 1.5
    elif live_price < ema5 < ema15: score -= 1.5
    
    if 48 <= rsi <= 62: score += 1.0
    elif rsi > 70: score -= 0.5
    elif rsi < 30: score += 0.5
    
    if macd_diff > 0: score += 1.0
    else: score -= 1.0
    
    if vol_ratio >= 1.5: score += 1.5
    elif vol_ratio >= 1.2: score += 0.8
    elif vol_ratio < 0.7: score -= 0.5
    
    if pcr_volume < 0.7: score += 1.0
    elif pcr_volume > 1.3: score -= 1.0
    
    if sentiment_score > 0.1: score += 0.5
    if short_pct > 0.12 and vol_ratio > 1.3: score += 1.0

    live_ai_score = round(max(1.0, min(10.0, score)), 1)
    
    entry = round(live_price, 2)
    sl = round(live_price * 0.965, 2)
    tp1 = round(live_price * 1.045, 2)
    tp2 = round(live_price * 1.085, 2)

    return {
        "Ticker": symbol,
        "Sector": sector,
        "Koers": f"${entry}",
        "Verandering": f"{round(day_change_pct, 2)}%",
        "AI Score": live_ai_score,
        "Signaal": "BUY / LONG" if live_ai_score >= 6.8 else ("WATCH" if live_ai_score >= 5.0 else "AVOID / SHORT"),
        "Volume Ratio": f"{round(vol_ratio, 2)}x",
        "RSI": round(rsi, 1),
        "EMA Trend": "Bullish" if ema5 > ema15 else "Bearish",
        "Put/Call Ratio": f"{round(pcr_volume, 2)} ({pcr_status})",
        "Short Float": f"{round(short_pct * 100, 1)}%",
        "Entry": f"${entry}",
        "Stop Loss (-3.5%)": f"${sl}",
        "TP1 (1-3d)": f"${tp1}",
        "TP2 (3-5d)": f"${tp2}"
    }

# --- HOOFDSCHERM LOGICA ---
if scan_button or tickers:
    st.write(f"### Analyseren van: {', '.join(tickers)}")
    results = []
    
    progress_bar = st.progress(0)
    for idx, ticker in enumerate(tickers):
        data = get_live_swing_data(ticker)
        if data:
            results.append(data)
        progress_bar.progress((idx + 1) / len(tickers))
    progress_bar.empty()
    
    if results:
        df_res = pd.DataFrame(results)
        df_res = df_res.sort_values(by="AI Score", ascending=False)
        
        # Welke kolommen tonen in het overzicht
        st.subheader("📊 Ranking & AI Scores")
        
        # Color formatting voor de AI Score
        def highlight_score(val):
            if isinstance(val, (int, float)):
                if val >= 6.8: return 'background-color: #1b4332; color: #00ff87'
                elif val < 5.0: return 'background-color: #4a0e17; color: #ff4d4d'
            return ''

        st.dataframe(
            df_res[["Ticker", "AI Score", "Signaal", "Koers", "Verandering", "Volume Ratio", "RSI", "Put/Call Ratio", "Short Float"]],
            use_container_width=True
        )
        
        st.subheader("🎯 Concrete Trade Setups (1-5 Dagen)")
        for item in results:
            with st.expander(f"{item['Ticker']} — AI Score: {item['AI Score']}/10 ({item['Signaal']})"):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Entry Level", item["Entry"])
                col2.metric("Stop Loss", item["Stop Loss (-3.5%)"])
                col3.metric("Take Profit 1", item["TP1 (1-3d)"])
                col4.metric("Take Profit 2", item["TP2 (3-5d)"])
                
                st.write(f"**Sector:** {item['Sector']} | **EMA Trend:** {item['EMA Trend']} | **Volume Ratio:** {item['Volume Ratio']}")
