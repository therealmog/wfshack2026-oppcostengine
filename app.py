#################################################
#################################################
#------PROPERTY OF RAASclart PRODUCTIONS--------#
#################################################
#################################################


from flask import Flask, render_template, request, jsonify
import yfinance as yf
import concurrent.futures
import json
import os

app = Flask(__name__)

# --- DATA LOADING & CHECKPOINTING ---
def load_company_database():
    if os.path.exists('companies.json'):
        try:
            with open('companies.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return [{"name": "Apple (iPhone, Mac, iPad)", "ticker": "AAPL"}]

COMPANY_DB = load_company_database()

def fetch_financial_data(ticker_symbol):
    """Fetches real-market data with a fallback to 8% return if the API fails."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Using 5-year history to calculate historical CAGR
        hist = ticker.history(period="5y")
        if hist.empty:
            return {"return": 0.08, "dividend": 0.01}
            
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        cagr = (end_price / start_price) ** (1/5) - 1
        div_yield = ticker.info.get('dividendYield', 0.01) or 0.01
        return {"return": float(cagr), "dividend": float(div_yield)}
    except Exception:
        return {"return": 0.08, "dividend": 0.01}

@app.route('/')
def index():
    return render_template('index.html', companies=COMPANY_DB)

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    product_name = data.get('item_name', 'this item')
    price = float(data.get('price', 0))
    ticker = data.get('ticker', 'AAPL')
    years = int(data.get('years', 5))
    is_subscription = data.get('is_subscription', False)

    # Parallelise the API fetch
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(fetch_financial_data, ticker)
        fin_data = future.result()

    annual_growth = fin_data['return'] + fin_data['dividend']
    labels, asset_values, equity_values = [], [], []
    
    # Calculation Logic (Scientific Methodology)
    curr_asset = price if not is_subscription else 0
    curr_equity = price if not is_subscription else 0
    annual_sub_cost = price * 12 if is_subscription else 0

    for year in range(years + 1):
        labels.append(f"Year {year}")
        if year == 0:
            asset_values.append(round(curr_asset, 2))
            equity_values.append(round(curr_equity, 2))
            continue

        # Depreciation: 20% for tech/general, 100% for subscriptions
        deprec_rate = 1.0 if is_subscription else 0.20
        curr_asset *= (1 - deprec_rate)
        
        if is_subscription:
            curr_equity = (curr_equity + annual_sub_cost) * (1 + annual_growth)
        else:
            curr_equity *= (1 + annual_growth)

        asset_values.append(round(curr_asset, 2))
        equity_values.append(round(curr_equity, 2))

    # Formatting Verdict (British Standards)
    final_val = equity_values[-1]
    formatted_equity = f"£{final_val:,.2f}"
    profit = f"£{(final_val - price):,.2f}"
    
    milestone = "Never"
    for i, val in enumerate(equity_values):
        if val >= (price * 2 if not is_subscription else price * 24):
            milestone = f"Year {i}"
            break

    if is_subscription:
        verdict = f"Paying £{price:,.2f}/month for {product_name} sacrifices {profit} in potential wealth gain over {years} years. Time to cancel?"
    else:
        verdict = f"Buying {product_name} sacrifices {profit} in potential wealth gain over {years} years. Is the dopamine hit really worth it?"

    return jsonify({
        "labels": labels, "asset_values": asset_values, "equity_values": equity_values,
        "milestone": milestone, "final_equity": final_val, "verdict": verdict
    })

def get_name_from_ticker(ticker):
    for companyDetails in COMPANY_DB:
        if companyDetails["ticker"] == ticker:
            return companyDetails["name"]
        
if __name__ == '__main__':
    app.run(debug=True)


#################################################
#################################################
#------PROPERTY OF RAASclart PRODUCTIONS--------#
#################################################
#################################################