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

REQUIRED_METRICS = [
    "Price to Earning",
    "Net Profit",
    "OPM"
]

OPTIONAL_METRICS = [
    "Return on equity",
    "Debt to equity",
    "Return on capital employed",
    "Profit growth",
    "Industry PE",
    "Dividend yield",
    "Sales growth"
]

METRIC_ALIASES = {
    "Price to Earning": ["price to earning", "p/e"],
    "Return on equity": ["return on equity", "roe"],
    "Market Capitalization": ["market capitalization", "market cap"],
    "Sales growth": ["sales growth"],
    "Dividend yield": ["dividend yield", "div yld"],
    "Return on capital employed": ["roce", "return on capital employed"],
    "OPM": ["opm", "operating profit margin"],
    "Net Profit": ["net profit", "pat"],
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
    found = {}
    company_name = "Unknown Company"

    if "Data Sheet" in xls.sheet_names:
        meta = xls.parse("Data Sheet")
        try:
            name = meta.columns[1]
            if str(name).strip().lower() != "unnamed: 1":
                company_name = str(name).strip()
        except:
            pass

    for sheet in xls.sheet_names:
        df = xls.parse(sheet).fillna("").astype(str)
        for row in df.values:
            for i, cell in enumerate(row):
                cell_str = cell.lower().strip()
                for metric, aliases in METRIC_ALIASES.items():
                    if metric in found:
                        continue
                    if any(alias in cell_str for alias in aliases):
                        values = list(row[i+1:i+6]) if i+1 < len(row) else []
                        values = [v for v in values if str(v).strip() != ""]
                        if values:
                            found[metric] = {
                                "years": [f"Year {j+1}" for j in range(len(values))],
                                "values": values
                            }

    return company_name, found

# ---------------------- PEER COMPARISON PARSER ----------------------
def parse_peer_comparison(pasted_text):
    lines = pasted_text.strip().split("\n")
    if len(lines) < 2:
        return {}

    header = lines[0].split("\t")
    values = lines[1].split("\t")
    peer_data = dict(zip(header, values))
    mapped = {}
    for key, aliases in METRIC_ALIASES.items():
        for col in header:
            col_clean = col.lower().strip()
            if any(alias in col_clean for alias in aliases):
                val = peer_data.get(col)
                if val:
                    mapped[key] = {"years": ["Peer"], "values": [val]}
    return mapped

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
        except:
            st.warning(f"Could not fetch news from {name}")

# ---------------------- STREAMLIT APP ----------------------
st.set_page_config("Indian Stock Analysis Tool", layout="wide")
st.title("📊 In-Depth Stock Analysis (India)")

rules = load_rules()
file = st.file_uploader("Upload Screener Excel File", type="xlsx")
pasted_text = st.text_area("📋 Paste the first 2 lines from the Peer Comparison table (copy from Screener.in)",
                           placeholder="S.No.\tName\tCMP Rs.\tP/E\tMar Cap Rs.Cr.\tDiv Yld %\tROCE %\tOPM %\tPAT 12M Rs.Cr.\tDebt / Eq\tROE %\tSales growth %\tInd PE\tProfit growth %\n1.\tReliance Industr\t1185.35\t23.18\t1604059.38\t0.42\t9.61\t17.46\t69192.00\t0.44\t9.25\t7.12\t21.17\t-0.98")

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
combined_metrics = {}
if file:
    with st.spinner("Processing Excel file..."):
        xls = pd.ExcelFile(file)
        company, extracted_metrics = extract_metrics(xls)
        combined_metrics.update(extracted_metrics)
else:
    company = "Uploaded"

if pasted_text.strip():
    pasted_metrics = parse_peer_comparison(pasted_text)
    combined_metrics.update(pasted_metrics)

if combined_metrics:
    st.success(f"Parsed data for: **{company}**")
    st.subheader("📈 Financial Trend Visualizations")
    for k in combined_metrics:
        plot_metric(k, combined_metrics[k])

    st.subheader("📌 Buy/Sell Evaluation")
    results = evaluate_all(combined_metrics, rules)
    score = int(100 * sum(x[3] for x in results['buy']) / len(results['buy'])) if results['buy'] else 0
    st.markdown(f"### ✅ Buy Score: **{score}%**")
    for k, v, r, ok in results['buy']:
        st.write(f"{'✅' if ok else '❌'} {k}: {v} (Rule: {r})")

    st.markdown("---")
    st.markdown("### 💰 Valuation Tags")
    for k, v, r, ok in results['valuation']:
        st.write(f"{k}: {v} (Rule: {r}) → {'📉 Undervalued' if ok else '💰 Overvalued'}")

    fetch_news(company)
else:
    st.warning("Please upload an Excel file or paste Peer Comparison data to continue.")
