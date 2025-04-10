import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import json
import os
import requests
from bs4 import BeautifulSoup

# --- Configuration ---
RULES_FILE = "saved_rules.json"
REQUIRED_METRICS = [
    "Price to Earning",
    "Return on equity",
    "Market Capitalization",
    "Free cash flow 3years",
    "Dividend yield",
    "Sales growth",
    "Net Profit latest quarter",
    "Return on capital employed",
    "OPM",
    "Profit after tax",
    "Debt to equity",
    "Industry PE",
    "Profit growth",
    "Free cash flow last year"
]
NEWS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/topic/{}",
    "Mint": "https://www.livemint.com/Search/Link/Keyword/{}",
    "Business Standard": "https://www.business-standard.com/search?q={}"
}

# --- Load or Initialize Rules ---
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

# --- Screener Excel Parsing ---
def parse_screener_excel(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    sheets = xls.sheet_names
    metrics = {}
    missing = []
    company_name = "Unknown Company"

    if "Data Sheet" in sheets:
        meta = xls.parse("Data Sheet")
        first_cell = str(meta.columns[1]) if len(meta.columns) > 1 else None
        if first_cell and first_cell.strip() != "Unnamed: 1":
            company_name = first_cell.strip()

    for sheet_name in sheets:
        df = xls.parse(sheet_name)
        df = df.dropna(how='all')
        if 'Narration' not in df.iloc[:, 0].astype(str).values:
            continue

        df.columns = df.iloc[1]  # Set second row as header
        df = df[2:]  # Skip first two rows

        for metric in REQUIRED_METRICS:
            match = df[df[df.columns[0]].astype(str).str.contains(metric, case=False, na=False)]
            if not match.empty:
                values = match.iloc[0, 1:].dropna()
                try:
                    years = values.index.astype(str).tolist()
                except:
                    years = [f"Year {i+1}" for i in range(len(values))]
                metrics[metric] = {"years": years, "values": values.tolist()}
            else:
                if metric not in metrics:
                    missing.append(metric)

    return company_name, metrics, missing

# --- Evaluate Rules ---
def evaluate_rule(value, rule_str):
    try:
        operator = rule_str.strip()[0:2] if rule_str.strip()[1] in '=<' else rule_str.strip()[0]
        number = float(rule_str.strip().replace(operator, ''))
        if operator == '>': return value > number
        if operator == '<': return value < number
        if operator == '>=': return value >= number
        if operator == '<=': return value <= number
        if operator == '==': return value == number
        return False
    except:
        return False

def evaluate_metrics(metrics, rules):
    results = {"buy": [], "valuation": []}
    for key, rule in rules["buy_rules"].items():
        if key in metrics:
            try:
                latest_value = float(metrics[key]["values"][-1])
                passed = evaluate_rule(latest_value, rule)
                results["buy"].append((key, latest_value, rule, passed))
            except:
                results["buy"].append((key, "N/A", rule, False))
        else:
            results["buy"].append((key, "Missing", rule, False))

    for key, rule in rules["valuation_rules"].items():
        if key in metrics:
            try:
                latest_value = float(metrics[key]["values"][-1])
                passed = evaluate_rule(latest_value, rule)
                results["valuation"].append((key, latest_value, rule, passed))
            except:
                results["valuation"].append((key, "N/A", rule, False))
        else:
            results["valuation"].append((key, "Missing", rule, False))

    return results

# --- Chart Plotting ---
def plot_metric_trend(metric_name, data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["years"],
        y=data["values"],
        mode='lines+markers',
        name=metric_name
    ))
    fig.update_layout(
        title=metric_name,
        xaxis_title="Year",
        yaxis_title=metric_name,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- News Fetching ---
def fetch_news(company):
    st.subheader(f"📰 News & Sentiment for: {company}")
    for source, url_template in NEWS_SOURCES.items():
        url = url_template.format(company.replace(" ", "+"))
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(response.content, 'html.parser')
            st.markdown(f"**{source}**")
            links = soup.find_all("a", href=True)
            shown = 0
            for link in links:
                text = link.get_text().strip()
                href = link['href']
                if len(text) > 30 and company.split()[0].lower() in text.lower():
                    st.markdown(f"- [{text}]({href})")
                    shown += 1
                if shown >= 5:
                    break
        except Exception as e:
            st.warning(f"Could not fetch news from {source}: {e}")

# --- Streamlit UI ---
st.set_page_config(page_title="Indian Stock Analysis Tool", layout="wide")
st.title("📊 In-Depth Stock Analysis - India Focus")

# Upload Screener Excel
uploaded_file = st.file_uploader("Upload Screener.in Excel File", type=["xlsx"])
rules = load_rules()

# Rule Editor Sidebar
with st.sidebar:
    st.header("⚙️ Buy/Sell Criteria")
    st.markdown("Define your investment rules")
    for key in rules["buy_rules"]:
        rules["buy_rules"][key] = st.text_input(f"Buy Rule - {key}", value=rules["buy_rules"][key])

    st.header("📉 Valuation Rules")
    for key in rules["valuation_rules"]:
        rules["valuation_rules"][key] = st.text_input(f"Valuation Rule - {key}", value=rules["valuation_rules"][key])

    if st.button("💾 Save Rules"):
        save_rules(rules)
        st.success("Rules saved successfully!")

# Main logic
if uploaded_file:
    with st.spinner("Parsing Excel file..."):
        company_name, metrics, missing = parse_screener_excel(uploaded_file)

    if missing:
        st.error(f"⚠️ Missing key metrics in the file: {', '.join(missing)}")
        st.info("Please re-download the Excel from Screener with all data points.")
    else:
        st.success(f"All required metrics found for **{company_name}**!")
        st.subheader("📈 Extracted Key Financial Trends")
        for key in metrics:
            plot_metric_trend(key, metrics[key])

        st.subheader("📌 Evaluation Result")
        results = evaluate_metrics(metrics, rules)

        buy_passed = [r for r in results["buy"] if r[3]]
        buy_total = len(results["buy"])
        buy_score = int((len(buy_passed) / buy_total) * 100) if buy_total else 0

        st.markdown(f"### Buy Signal Match: **{buy_score}%**")
        for r in results["buy"]:
            status = "✅" if r[3] else "❌"
            st.write(f"{status} {r[0]}: Latest = {r[1]}, Rule = {r[2]}")

        st.markdown("---")
        st.markdown("### Valuation Check")
        for r in results["valuation"]:
            status = "📉 Undervalued" if r[3] else "💰 Overvalued"
            st.write(f"{r[0]}: Latest = {r[1]}, Rule = {r[2]} → {status}")

        fetch_news(company_name)
