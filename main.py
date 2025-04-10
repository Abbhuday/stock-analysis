import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- Helper Functions ---
def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="5y")
    return stock, info, hist

def calculate_ratios(info):
    try:
        roe = info['returnOnEquity']
        roa = info['returnOnAssets']
        gross_margin = info['grossMargins']
        operating_margin = info['operatingMargins']
        net_margin = info['netMargins']
        pe_ratio = info['trailingPE']
        pb_ratio = info['priceToBook']
        debt_to_equity = info['debtToEquity']
        current_ratio = info['currentRatio']
        return {
            'ROE': roe,
            'ROA': roa,
            'Gross Margin': gross_margin,
            'Operating Margin': operating_margin,
            'Net Margin': net_margin,
            'P/E Ratio': pe_ratio,
            'P/B Ratio': pb_ratio,
            'Debt/Equity': debt_to_equity,
            'Current Ratio': current_ratio
        }
    except:
        return {}

def plot_price_trend(hist):
    fig, ax = plt.subplots()
    ax.plot(hist.index, hist['Close'])
    ax.set_title("Stock Price Trend (5Y)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price ($)")
    st.pyplot(fig)

def display_ratios(ratios):
    if not ratios:
        st.warning("Not enough data to display ratios.")
        return
    df = pd.DataFrame(list(ratios.items()), columns=["Ratio", "Value"])
    st.dataframe(df.set_index("Ratio"))

def valuation_score(ratios):
    score = 0
    if ratios.get('ROE', 0) > 0.15:
        score += 1
    if ratios.get('P/E Ratio', 100) < 20:
        score += 1
    if ratios.get('Debt/Equity', 100) < 1:
        score += 1
    if ratios.get('Current Ratio', 0) > 1.5:
        score += 1
    return score

def suggest_action(score):
    if score >= 3:
        return ("Buy", "🟢")
    elif score == 2:
        return ("Hold", "🟡")
    else:
        return ("Sell", "🔴")

# --- Streamlit UI ---
st.set_page_config(page_title="In-Depth Stock Analysis", layout="wide")
st.title("📈 In-Depth Stock Analysis Tool")

# Input Section
ticker = st.text_input("Enter Stock Ticker Symbol (e.g., AAPL, MSFT, TSLA)", "AAPL")
if ticker:
    with st.spinner("Fetching data..."):
        stock, info, hist = fetch_stock_data(ticker)

    st.subheader(f"Overview: {info.get('shortName', 'N/A')}")
    st.markdown(f"**Sector:** {info.get('sector', 'N/A')}  ")
    st.markdown(f"**Industry:** {info.get('industry', 'N/A')}  ")
    st.markdown(f"**Market Cap:** {info.get('marketCap', 'N/A'):,}  ")
    st.markdown(f"**Current Price:** ${info.get('currentPrice', 'N/A')}  ")
    st.markdown(f"**52-Week High/Low:** ${info.get('fiftyTwoWeekHigh', 'N/A')} / ${info.get('fiftyTwoWeekLow', 'N/A')}  ")

    st.subheader("📊 Price Trend")
    plot_price_trend(hist)

    st.subheader("📈 Key Financial Ratios")
    ratios = calculate_ratios(info)
    display_ratios(ratios)

    st.subheader("📌 Investment Suggestion")
    score = valuation_score(ratios)
    suggestion, emoji = suggest_action(score)
    st.markdown(f"### {emoji} Suggestion: **{suggestion}** (Score: {score}/4)")
