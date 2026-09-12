import yfinance as yf
import pandas as pd
import numpy as np
import ta
from textblob import TextBlob
import warnings
warnings.filterwarnings('ignore')

def get_live_swing_score(symbol):
    print(f"\n==========================================")
    print(f" LIVE ANALYSE OPHALEN VOOR: {symbol}")
    print(f"==========================================")
    
    ticker = yf.Ticker(symbol)
    
    # Live/Daily Data
    df = ticker.history(period="60d", interval="1d")
    if df.empty or len(df) < 20:
        print(f"Geen data voor {symbol}")
        return None
        
    info = ticker.info
    live_price = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2]
    day_change_pct = ((live_price - prev_close) / prev_close) * 100
    
    # Volume
    current_volume = df['Volume'].iloc[-1]
    avg_vol_20d = df['Volume'].rolling(20).mean().iloc[-1]
    vol_ratio = current_volume / avg_vol_20d if avg_vol_20d > 0 else 1.0
    
    # Indicatoren
    ema5 = ta.trend.ema_indicator(df['Close'], window=5).iloc[-1]
    ema15 = ta.trend.ema_indicator(df['Close'], window=15).iloc[-1]
    rsi = ta.momentum.rsi(df['Close'], window=14).iloc[-1]
    macd_diff = ta.trend.MACD(df['Close']).macd_diff().iloc[-1]
    
    # Opties Put/Call
    pcr_volume = 1.0
    pcr_status = "NEUTRAAL"
    try:
        if ticker.options:
            nearest_exp = ticker.options[0]
            opt_chain = ticker.option_chain(nearest_exp)
            calls_vol = opt_chain.calls['volume'].sum()
            puts_vol = opt_chain.puts['volume'].sum()
            if calls_vol > 0:
                pcr_volume = puts_vol / calls_vol
                if pcr_volume < 0.7: pcr_status = "BULLISH (Call heavy)"
                elif pcr_volume > 1.3: pcr_status = "BEARISH (Put heavy)"
    except Exception:
        pass

    # Sentiment
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
    
    # AI Scoring (1-10)
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

    print(f" Sector: {sector}")
    print(f" Live Koers: ${entry} ({'+' if day_change_pct >= 0 else ''}{round(day_change_pct, 2)}%)")
    print(f" Volume Ratio: {round(vol_ratio, 2)}x | RSI (14): {round(rsi, 1)}")
    print(f" Put/Call Ratio: {round(pcr_volume, 2)} -> {pcr_status}")
    print(f" LIVE SWING AI SCORE: {live_ai_score} / 10")
    print(f" Advies: {'BUY / LONG' if live_ai_score >= 6.8 else ('WATCH' if live_ai_score >= 5.0 else 'AVOID / SHORT')}")
    print(f" Setup: Entry ${entry} | SL: ${sl} | TP1: ${tp1} | TP2: ${tp2}")
    
    return live_ai_score

if __name__ == "__main__":
    # Pas deze lijst aan naar de aandelen die je wilt scannen:
    watchlist = ["NVDA", "TSLA", "PLTR", "AMD", "AAPL", "AMZN", "MSFT", "META"]
    for t in watchlist:
        get_live_swing_score(t)
