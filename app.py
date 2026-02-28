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
from random import choice
import numpy as np
from sklearn.linear_model import LinearRegression
from textblob import TextBlob

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

def GBM_model(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5y")
        if hist.empty:
            return {"mu": 0.08, "sigma": 0.15} # Reasonable defaults
            
        # Log returns are more accurate for GBM math
        log_returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna()
        
        # Annualize (252 trading days)
        drift = log_returns.mean() * 252
        volatility = log_returns.std() * np.sqrt(252)
        
        return {"mu": float(drift), "sigma": float(volatility)}
    except Exception:
        return {"mu": 0.08, "sigma": 0.20}

def BS_method():
    pass

def run_gbm_simulation(price, years, mu, sigma, is_subscription, n_sims=100):
    """
    Core GBM Engine: Generates stochastic paths using Monte Carlo.
    Returns: (median_path, upper_path, lower_path)
    """
    # Create matrix: Rows = Simulations, Cols = Years
    paths = np.zeros((n_sims, years + 1))
    
    # Starting value
    initial_val = price if not is_subscription else (price * 12)
    paths[:, 0] = initial_val

    for t in range(1, years + 1):
        # Generate random shocks for all sims at once
        Z = np.random.standard_normal(n_sims)
        
        # GBM Equation: exp((drift - vol_drag) + volatility * shock)
        growth_factors = np.exp((mu - 0.5 * sigma**2) + sigma * Z)
        
        if is_subscription:
            # Compound existing wealth + add new annual subscription cost
            paths[:, t] = (paths[:, t-1] * growth_factors) + (price * 12)
        else:
            paths[:, t] = paths[:, t-1] * growth_factors

    # Calculate percentiles (10th, 50th, 90th) across the horizontal axis
    median = np.percentile(paths, 50, axis=0).tolist()
    upper = np.percentile(paths, 90, axis=0).tolist()
    lower = np.percentile(paths, 10, axis=0).tolist()
    
    return median, upper, lower

def get_ai_growth_rate(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="2y")
        if hist.empty:
            return 0.07 
        
        prices = hist['Close'].values.reshape(-1, 1)
        days = np.arange(len(prices)).reshape(-1, 1)
        
        model = LinearRegression()
        model.fit(days, prices)
        
        current_price = prices[-1][0]
        predicted_annual_change = (model.coef_[0][0] * 252) / current_price
        
        sentiment_adjustment = 0
        news = ticker.news
        if news:
            scores = [TextBlob(n['title']).sentiment.polarity for n in news[:5]]
            avg_sentiment = sum(scores) / len(scores)
            sentiment_adjustment = avg_sentiment * 0.05

        total_rate = predicted_annual_change + sentiment_adjustment
        return max(min(total_rate, 0.35), -0.15)
    except Exception as e:
        print(f"AI Prediction Error: {e}")
        return 0.07

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
    
    # Get model choice from frontend: 'historical' or 'gbm'
    model_type = data.get('model_type', 'historical') 
    company_name = get_name_from_ticker(ticker)

    # Fetch financial parameters
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(fetch_financial_data, ticker)
        fin_data = future.result()

    # --- MODEL SELECTION ---
    upper_equity, lower_equity = [], [] # Default empty for non-GBM

    if model_type == 'gbm':
        # ONLY runs if GBM is selected
        mu = fin_data.get('mu', 0.08)
        sigma = fin_data.get('sigma', 0.15)
        
        equity_values, upper_equity, lower_equity = run_gbm_simulation(
            price, years, mu, sigma, is_subscription
        )

    elif model_type == "NB_AI":
        # Uses your Regression + Sentiment logic
        annual_growth = get_ai_growth_rate(ticker)
        labels, asset_values, equity_values = [], [], []

        curr_asset = price if not is_subscription else 0
        curr_equity = price if not is_subscription else 0
        annual_sub_cost = price * 12 if is_subscription else 0

        for year in range(years + 1):
            labels.append(f"Year {year}")
            if year == 0:
                asset_values.append(round(curr_asset, 2))
                equity_values.append(round(curr_equity, 2))
                continue

            deprec_rate = 1.0 if is_subscription else 0.20
            curr_asset *= (1 - deprec_rate)
            
            if is_subscription:
                curr_equity = (curr_equity + annual_sub_cost) * (1 + annual_growth)
            else:
                curr_equity *= (1 + annual_growth)

            asset_values.append(round(curr_asset, 2))
            equity_values.append(round(curr_equity, 2))


    else:
        # ORIGINAL Historical Trend Logic
        annual_growth = fin_data.get('return', 0.08) + fin_data.get('dividend', 0.01)
        equity_values = []
        curr_equity = price if not is_subscription else 0
        annual_sub_cost = price * 12 if is_subscription else 0

        for year in range(years + 1):
            if year == 0:
                equity_values.append(round(curr_equity, 2))
                continue
            if is_subscription:
                curr_equity = (curr_equity + annual_sub_cost) * (1 + annual_growth)
            else:
                curr_equity *= (1 + annual_growth)
            equity_values.append(round(curr_equity, 2))

    # --- SHARED LOGIC (Depreciation & Verdict) ---
    final_val = equity_values[-1]
    asset_values = []
    temp_asset = price if not is_subscription else 0
    for y in range(years + 1):
        asset_values.append(round(temp_asset, 2))
        temp_asset *= 0.80

    formatted_equity = f"£{final_val:,.2f}"

    # Calculate profit (Opportunity Cost)
    base_cost = (price * 12 * years) if is_subscription else price
    profit_val = final_val - base_cost
    profit_str = f"£{abs(profit_val):,.2f}"

    milestone = "Never"
    for i, val in enumerate(equity_values):
        threshold = (price * 2 if not is_subscription else price * 24)
        if val >= threshold:
            milestone = f"Year {i}"
            break

    # Verdict Logic with correctly passed arguments for .format()
    if is_subscription:
        verdict = f"Paying £{price:,.2f}/month for {product_name} sacrifices {profit_str} in potential wealth gain over {years} years. Time to cancel?"
    else:
        is_pos = profit_val > 0
        verdict_template = get_verdict(isPositive=is_pos, isProduct=True)
        # FIX: Added profit=profit_str and product=product_name to the format call
        verdict = verdict_template.format(product=product_name, profit=profit_str,years=years,company_name=company_name)

    return jsonify({
        "labels": [f"Year {i}" for i in range(years + 1)],
        "asset_values": asset_values,
        "equity_values": equity_values,
        "upper_equity": upper_equity,
        "lower_equity": lower_equity,
        "final_equity": final_val,
        "verdict": verdict
    })

def get_name_from_ticker(ticker):
    for companyDetails in COMPANY_DB:
        if companyDetails["ticker"] == ticker:
            return companyDetails["name"]
    return ticker

def get_verdict(isPositive, isProduct):
    with open("verdicts.json", "r") as f:
        verdictsDict = json.load(f)
    
    if isPositive:
        return choice(verdictsDict["products_positive"]) if isProduct else "Positive Sub Verdict"
    else:
        return choice(verdictsDict["products_negative"]) if isProduct else "Negative Sub Verdict"

if __name__ == '__main__':
    app.run(debug=True)

#################################################
#################################################
#------PROPERTY OF RAASclart PRODUCTIONS--------#
#################################################
#################################################