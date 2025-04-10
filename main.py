import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
import requests
from bs4 import BeautifulSoup
import re

# ---------------------- CONFIG ----------------------
RULES_FILE = "saved_rules.json"

METRIC_ALIASES = {
    "Price to Earning": ["price to earning", "p/e", "p/e ratio"],
    "Return on equity": ["return on equity", "roe"],
    "Market Capitalization": ["market capitalization", "market cap"],
    "Sales growth": ["sales growth"],
    "Dividend yield": ["dividend yield"],
    "Net Profit latest quarter": ["net profit latest quarter"],
    "Return on capital employed": ["roce", "return on capital employed"],
    "OPM": ["opm", "operating profit margin"],
    "Profit after tax": ["profit after tax", "pat"],
    "Debt to equity": ["debt to equity", "d/e"],
    "Industry PE": ["industry pe", "industry p/e"],
    "Profit growth": ["profit growth"]
}

NEWS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/topic/{}",
    "Mint": "https://www.livemint.com/Search/Link/Keyword/{}",
    "Business Standard": "https://www.business-standard.com/search?q={}"
}

# ---------------------- RULES ----------------------
def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    return {
        "buy_rules": {
            "Return on equity": "> 15",
            "Debt to equity": "< 1"
        },
        "valuation_rules": {
            "Price to Earning": "< 20",
            "Industry PE": "< 30"
        }
    }

def save_rules(rules):
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f)

# ---------------------- PARSER ----------------------
def extract_metrics(xls):
    sheets = xls.sheet_names
    found = {}
    missing = []
    company_name = "Unknown Company"

    if "Data Sheet" in sheets:
        meta = xls.parse("Data Sheet")
        try:
            first_col = meta.columns[1]
            if str(first_col).strip() != "Unnamed: 1":
                company_name = str(first_col).strip()
        except:
            pass

    for sheet in sheets:
        df = xls.parse(sheet).dropna(how='all').dropna(axis=1, how='all')
        for label, variants in METRIC_ALIASES.items():
            if label in found:
                continue
            for i in range(len(df)):
                row_label = str(df.iloc[i, 0]).lower()
                if any(re.search(v, row_label) for v in variants):
                    try:
                        row_vals = df.iloc[i, 1:].dropna().values[-5:].tolist()
                        col_years = df.columns[1:1+len(row_vals)].astype(str).tolist()
                        found[label] = {"years": col_years, "values": row_vals}
                        break
                    except:
                        continue

    for k in METRIC_ALIASES:
        if k not in found:
            missing.append(k)

    return company_name, found, missing

# ---------------------- EVALUATION ----------------------
def evaluate_rule(val, rule):
    try:
        op = rule.strip()[0:2] if rule[1] in '=<' else rule[0]
        num = float(rule.replace(op, ''))
        return eval(f"{val} {op} {num}")
    except:
        return False

def evaluate_all(metrics, rules):
    results = {"buy": [], "valuation": []}
    for rtype in results:
        for key, rule in rules[f"{rtype}_rules"].items():
            if key in metrics:
                try:
                    val = float(metrics[key]["values"][-1])
                    passed = evaluate_rule(val, rule)
                    results[rtype].append((key, val, rule, passed))
                except:
                    results[rtype].append((key, "N/A", rule, False))
            else:
                results[rtype].append((key, "Missing", rule, False))
    return results

# ---------------------- VISUALIZATION ----------------------
def plot_metric(name, data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['years'], y=data['values'], mode='lines+markers'))
    fig.update_layout(title=name, xaxis_title="Year", yaxis_title=name)
    st.plotly_chart(fig, use_container_width=True)

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
        except Exception as e:
            st.warning(f"Could not fetch news from {name}")

# ---------------------- STREAMLIT APP ----------------------
st.set_page_config("Indian Stock Analysis Tool", layout="wide")
st.title("📊 In-Depth Stock Analysis (India)")

rules = load_rules()
file = st.file_uploader("Upload Screener Excel File", type="xlsx")

# Sidebar Rules
with st.sidebar:
    st.header("📋 Buy/Sell Rules")
    for k in rules["buy_rules"]:
        rules["buy_rules"][k] = st.text_input(f"Buy Rule - {k}", rules["buy_rules"][k])
    st.header("📉 Valuation Rules")
    for k in rules["valuation_rules"]:
        rules["valuation_rules"][k] = st.text_input(f"Valuation Rule - {k}", rules["valuation_rules"][k])
    if st.button("💾 Save Rules"):
        save_rules(rules)
        st.success("Rules saved!")

# Main App
if file:
    with st.spinner("Processing Excel file..."):
        xls = pd.ExcelFile(file)
        company, metrics, missing = extract_metrics(xls)

    if missing:
        st.error("⚠️ Missing key metrics in the file: " + ", ".join(set(missing)))
    else:
        st.success(f"Parsed data for: **{company}**")
        st.subheader("📈 Financial Trend Visualizations")
        for k in metrics:
            plot_metric(k, metrics[k])

        st.subheader("📌 Buy/Sell Evaluation")
        results = evaluate_all(metrics, rules)
        score = int(100 * sum(x[3] for x in results['buy']) / len(results['buy'])) if results['buy'] else 0
        st.markdown(f"### ✅ Buy Score: **{score}%**")
        for k, v, r, ok in results['buy']:
            st.write(f"{'✅' if ok else '❌'} {k}: {v} (Rule: {r})")

        st.markdown("---")
        st.markdown("### 💰 Valuation Tags")
        for k, v, r, ok in results['valuation']:
            st.write(f"{k}: {v} (Rule: {r}) → {'📉 Undervalued' if ok else '💰 Overvalued'}")

        fetch_news(company)
