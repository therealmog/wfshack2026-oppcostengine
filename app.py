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
import numpy as np
import yfinance as yf

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

# def get_sector_map():
#     """
#     Builds a {sector: [tickers]} dictionary from COMPANY_DB
#     """
#     sector_map = {}
#     for co in COMPANY_DB:
#         try:
#             ticker = yf.Ticker(co["ticker"])
#             sector = ticker.info.get("sector", "Other")
#             if sector not in sector_map:
#                 sector_map[sector] = []
#             sector_map[sector].append(co["ticker"])
#         except Exception:
#             continue
#     return sector_map


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


    
def run_gbm_simulation(price, years, mu, sigma, is_subscription, total_steps, n_sims):
    """
    Core GBM Engine: Generates stochastic paths using Monte Carlo.
    Returns: (median_path, upper_path, lower_path)
    """
    # Create matrix: Rows = Simulations, Cols = Years
    paths = np.zeros((n_sims, total_steps + 1))
    
    # Starting value
    initial_val = price if not is_subscription else (price * 12)
    paths[:, 0] = initial_val

    for t in range(1, total_steps + 1):
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

@app.route('/learn')
def learn():
    return render_template('learn.html')

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

    # deal with 0.25 step size for years
    years = float(data.get('years', 5))
    step_size = 0.25
    total_steps = int(years/step_size)

    ticker = data['ticker']
    yt = yf.Ticker(ticker)
    full_summary = yt.info.get("shortBusinessSummary", yt.info.get("longBusinessSummary", "No summary available."))


    # --- MODEL SELECTION ---
    upper_equity, lower_equity = [], [] # Default empty for non-GBM
    curr_equity = price if not is_subscription else 0
    curr_asset = price if not is_subscription else 0
    labels, asset_values, equity_values = [], [], []

    if model_type == 'GBM':
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(GBM_model, ticker)
            stat_data = future.result()
            
        mu = stat_data.get('mu', 0.08)
        sigma = stat_data.get('sigma', 0.15)
        
        equity_values, upper_equity, lower_equity = run_gbm_simulation(
            price, years, mu, sigma, is_subscription, total_steps, 100 
        )
        
        # --- FIX: Generate the missing Labels and Asset Values for GBM ---
        curr_asset = price if not is_subscription else 0
        for i in range(total_steps + 1):
            current_time = i * step_size
            labels.append(f"Yr {current_time}")
            asset_values.append(round(curr_asset, 2))
            curr_asset *= (0.8 ** step_size) # Apply 20% annual depreciation

    elif model_type == "NB_AI":
        # Uses your Regression + Sentiment logic
        annual_growth = get_ai_growth_rate(ticker)
        periodic_growth = (1 + annual_growth) ** step_size


        curr_asset = price if not is_subscription else 0
        curr_equity = price if not is_subscription else 0
        annual_sub_cost = price * 12 if is_subscription else 0

        for i in range(total_steps + 1):
            current_time = i * step_size
            
            # Create labels like "Yr 1.25" or "Yr 1.5"
            labels.append(f"Yr {current_time}")

            if i == 0:
                equity_values.append(round(curr_equity, 2))
                asset_values.append(round(curr_asset, 2))
                continue

            # 1. Update Asset (Monthly equivalent of 20% annual drop)
            # 0.8^0.25 per step
            curr_asset *= (0.8 ** step_size)
            
            # 2. Update Equity
            if is_subscription:
                # Add 3 months worth of sub cost (price * 3) before compounding
                curr_equity = (curr_equity + (price * 3)) * periodic_growth
            else:
                curr_equity *= periodic_growth

            equity_values.append(round(curr_equity, 2))
            asset_values.append(round(curr_asset, 2))

    else:
        # ORIGINAL Historical Trend Logic
        annual_growth = fin_data.get('return', 0.08) + fin_data.get('dividend', 0.01)
        periodic_growth = (1 + annual_growth) ** step_size

        equity_values = []
        curr_equity = price if not is_subscription else 0
        annual_sub_cost = price * 12 if is_subscription else 0

        for i in range(total_steps + 1):
            current_time = i * step_size
            
            # Create labels like "Yr 1.25" or "Yr 1.5"
            labels.append(f"Yr {current_time}")

            if i == 0:
                equity_values.append(round(curr_equity, 2))
                asset_values.append(round(curr_asset, 2))
                continue

            # 1. Update Asset (Monthly equivalent of 20% annual drop)
            # 0.8^0.25 per step
            curr_asset *= (0.8 ** step_size)
            
            # 2. Update Equity
            if is_subscription:
                # Add 3 months worth of sub cost (price * 3) before compounding
                curr_equity = (curr_equity + (price * 3)) * periodic_growth
            else:
                curr_equity *= periodic_growth

            equity_values.append(round(curr_equity, 2))
            asset_values.append(round(curr_asset, 2))

    # --- SHARED LOGIC (Depreciation & Verdict) ---
    final_val = equity_values[-1]
    asset_values = []
    temp_asset = price if not is_subscription else 0
    for y in range(total_steps + 1):
        asset_values.append(round(temp_asset, 2))
        temp_asset *= (0.80 ** step_size)

    formatted_equity = f"£{final_val:,.2f}"

    # Calculate profit (Opportunity Cost)
    base_cost = (price * 12 * years) if is_subscription else price
    profit_val = final_val - base_cost
    profit_str = f"£{abs(profit_val):,.2f}"
    price_str = f"£{price:,.2f}"

    # --- UPDATED MILESTONE FORMATTER ---
    milestone = "Never"
    for i, val in enumerate(equity_values):
        threshold = (price * 2 if not is_subscription else price * 24)
        if val >= threshold:
            time_val = i * step_size  # e.g., 1.25
            yrs = int(time_val)
            mos = int(round((time_val - yrs) * 12))
            
            parts = []
            if yrs > 0: 
                parts.append(f"{yrs} yr{'s' if yrs > 1 else ''}")
            if mos > 0: 
                parts.append(f"{mos} mo{'s' if mos > 1 else ''}")
            
            # Joins with " and " if both exist, otherwise just shows one
            milestone = " ".join(parts) if parts else "Never"
            break

    verdict_properties = {"price":price_str,
                          "product":product_name,
                          "profit":profit_str,
                          "company_name":company_name,
                          "years":years}
    # Verdict Logic with correctly passed arguments for .format()
    """if is_subscription:
        verdict = f"Paying £{price:,.2f}/month for {product_name} sacrifices {profit_str} in potential wealth gain over {years} years. Time to cancel?"
    else:
        is_pos = profit_val > 0
        verdict_template = get_verdict(isPositive=is_pos, isProduct=True)
        # FIX: Added profit=profit_str and product=product_name to the format call
        verdict = verdict_template.format(product=product_name, profit=profit_str,years=years,company_name=company_name)"""
    
    verdict = get_verdict(profit_val>0,not is_subscription).format(**verdict_properties)

    return jsonify({
        "labels": labels,
        "asset_values": asset_values,
        "equity_values": equity_values,
        "upper_equity": upper_equity,
        "lower_equity": lower_equity,
        "final_equity": final_val,
        "verdict": verdict,
        "milestone": milestone,# <-- initial display
        "full_context": full_summary, 
    })

def get_name_from_ticker(ticker):
    for companyDetails in COMPANY_DB:
        if companyDetails["ticker"] == ticker:
            return companyDetails["name"]
    return ticker

def get_verdict(isPositive, isProduct):
    with open("verdicts.json", "r") as f:
        verdictsDict = json.load(f)
    
    # Match statement for the different possibilities
    match(isProduct,isPositive):
        case(True,True):
            return choice(verdictsDict["products_positive"])
        case(True,False):
            return choice(verdictsDict["products_negative"])
        case(False,True):
            return choice(verdictsDict["subscriptions_positive"])
        case(False,False):
            return choice(verdictsDict["subscriptions_negative"])

# @app.route('/similar_trades', methods=['POST'])
# def similar_trades():
#     data = request.json
#     sector = data.get("sector")
#     price = float(data.get("price", 0))
#     years = float(data.get("years", 5))

#     if not sector:
#         return jsonify([])

#     sector_map = get_sector_map()
#     tickers = sector_map.get(sector, [])[:10]  # limit to avoid API spam

#     results = []

#     for ticker in tickers:
#         fin = fetch_financial_data(ticker)
#         growth = fin.get("return", 0.08) + fin.get("dividend", 0.01)

#         final_val = price * ((1 + growth) ** years)
#         profit = final_val - price

#         milestone = "N/A"
#         if final_val >= price * 2:
#             milestone = f"{round(np.log(2)/np.log(1+growth),1)} yrs"

#         results.append({
#             "ticker": ticker,
#             "final_value": round(final_val,2),
#             "profit": round(profit,2),
#             "milestone": milestone
#         })

#     # Sort by highest final value
#     results = sorted(results, key=lambda x: x["final_value"], reverse=True)[:3]

#     return jsonify(results)

"""@app.route('/sectors')
def sectors():
    sector_map = get_sector_map()
    return jsonify(list(sector_map.keys()))"""



if __name__ == '__main__':
    app.run(debug=True)

#################################################
#################################################
#------PROPERTY OF RAASclart PRODUCTIONS--------#
#################################################
#################################################