import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
import requests
from bs4 import BeautifulSoup

# ---------------------- CONFIG ----------------------
REQUIRED_METRICS = {
    "Current Price": "CMP Rs.",
    "Price to Earning": "P/E",
    "Market Capitalization": "Mar Cap Rs.Cr.",
    "Dividend Yield": "Div Yld %",
    "Return on Capital Employed": "ROCE %",
    "Operating Profit Margin": "OPM %",
    "Profit After Tax": "PAT 12M Rs.Cr.",
    "Debt to Equity": "Debt / Eq",
    "Return on Equity": "ROE %",
    "Sales Growth": "Sales growth %",
    "Industry PE": "Ind PE",
    "Profit Growth": "Profit growth %"
}

NEWS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/topic/{}",
    "Mint": "https://www.livemint.com/Search/Link/Keyword/{}",
    "Business Standard": "https://www.business-standard.com/search?q={}"
}

# ---------------------- EVALUATION ----------------------
def evaluate_rule(val, rule):
    try:
        op = rule.strip()[0:2] if rule[1] in '=<' else rule[0]
        num = float(rule.replace(op, ''))
        return eval(f"{val} {op} {num}")
    except:
        return False

def evaluate_all(metrics, rules):
    results = []
    for metric, rule in rules.items():
        value = metrics.get(metric)
        if value is None:
            results.append((metric, "Missing", rule, False))
            continue
        try:
            val = float(value)
            passed = evaluate_rule(val, rule)
            results.append((metric, val, rule, passed))
        except:
            results.append((metric, value, rule, False))
    return results

# ---------------------- NEWS ----------------------
def fetch_news(company):
    st.subheader(f"📰 News & Sentiment: {company}")
    for name, url in NEWS_SOURCES.items():
        st.markdown(f"**{name}**")
        try:
            r = requests.get(url.format(company.replace(" ", "+")), headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(r.content, 'html.parser')
            links = [a for a in soup.find_all('a', href=True) if len(a.text.strip()) > 30 and company.split()[0].lower() in a.text.lower()]
            for link in links[:5]:
                st.markdown(f"- [{link.text.strip()}]({link['href']})")
        except:
            st.warning(f"Could not fetch news from {name}")

# ---------------------- STREAMLIT APP ----------------------
st.set_page_config("Stock Evaluation Tool", layout="wide")
st.title("📊 In-Depth Indian Stock Analysis")

# Enter Financial Metrics section
st.subheader("📥 Enter Financial Metrics")
st.markdown("**Use [Screener.in](https://www.screener.in) for finding the below financial metrics**")
metric_inputs = {}
cols = st.columns(3)
for idx, (label, _) in enumerate(REQUIRED_METRICS.items()):
    with cols[idx % 3]:
        st.markdown(f"<label style='font-size:16px; font-weight:600'>{label}</label>", unsafe_allow_html=True)
        val = st.text_input(" ", key=f"manual_{label}")
        if val:
            metric_inputs[label] = val

# Evaluate button
st.markdown("<div style='text-align:center; margin-top:2rem;'>", unsafe_allow_html=True)
run_eval = st.button("✅ EVALUATE", type="primary")
st.markdown("</div>", unsafe_allow_html=True)

if run_eval:
    if len(metric_inputs) < len(REQUIRED_METRICS):
        missing = [k for k in REQUIRED_METRICS if k not in metric_inputs or not metric_inputs[k]]
        st.error(f"❌ Missing data for: {', '.join(missing)}")
    else:
        st.success("All required metrics available. Proceeding with evaluation.")

        # Evaluation criteria in sidebar after button click
        with st.sidebar:
            st.header("📋 Set Evaluation Rules")
            rule_inputs = {}
            for label in REQUIRED_METRICS:
                rule_val = st.text_input(f"{label} Rule", key=f"rule_{label}", value="")
                if rule_val:
                    rule_inputs[label] = rule_val

        st.subheader("📈 Evaluation Results")
        results = evaluate_all(metric_inputs, rule_inputs)
        score = int(100 * sum(r[3] for r in results) / len(results)) if results else 0
        st.markdown(f"### ✅ Match Score: **{score}%**")
        for metric, value, rule, passed in results:
            icon = "✅" if passed else "❌"
            st.write(f"{icon} {metric}: {value} (Rule: {rule})")

        company_name = metric_inputs.get("Current Price", "")
        if company_name:
            st.markdown("---")
            fetch_news(company_name)
        else:
            st.info("📌 Enter a company name above to fetch related news.")
