from flask import Flask, render_template, request, jsonify
import yfinance as yf
import concurrent.futures
import traceback

app = Flask(__name__)

# --- CHECKPOINTED MOCK DATA ---
# Fallback data if the real API fails during the hackathon demonstration
MOCK_TICKERS = {
    "AAPL": {"return": 0.25, "dividend": 0.005},
    "TSLA": {"return": 0.40, "dividend": 0.0},
    "NFLX": {"return": 0.15, "dividend": 0.0},
    "SBUX": {"return": 0.08, "dividend": 0.02}
}

DEPRECIATION_RATES = {
    "tech": 0.20,
    "car": 0.15,
    "subscription": 1.0, # Subscriptions have zero resale value
    "other": 0.10
}

def fetch_financial_data(ticker_symbol):
    """
    Attempts to fetch real data via yfinance. 
    Checkpoints to mock data on runtime error.
    """
    try:
        # REAL API CALL (Checkpointed)
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5y")
        if hist.empty:
            raise ValueError("No historical data found.")
            
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        
        # Calculate 5-year CAGR (Compound Annual Growth Rate)
        cagr = (end_price / start_price) ** (1/5) - 1
        
        # Approximate dividend yield
        div_yield = ticker.info.get('dividendYield', 0.0)
        if div_yield is None: div_yield = 0.0
            
        return {"return": float(cagr), "dividend": float(div_yield)}
        
    except Exception as e:
        print(f"Runtime error fetching {ticker_symbol}, using checkpointed mock data: {e}")
        # Fallback to mock data to prevent app crash
        return MOCK_TICKERS.get(ticker_symbol.upper(), {"return": 0.08, "dividend": 0.01})

def calculate_projection(price, is_subscription, years, fin_data, category):
    """Calculates the trajectory of the asset vs the equity."""
    annual_return = fin_data['return']
    div_yield = fin_data['dividend']
    depreciation = DEPRECIATION_RATES.get(category, 0.20)
    
    labels = []
    asset_values = []
    equity_values = []
    
    current_asset_val = price if not is_subscription else 0
    current_equity_val = price if not is_subscription else 0
    annual_cost = price * 12 if is_subscription else 0

    for year in range(0, years + 1):
        labels.append(f"Year {year}")
        
        if year == 0:
            asset_values.append(current_asset_val)
            equity_values.append(current_equity_val)
            continue
            
        # Asset Decay
        if not is_subscription:
            current_asset_val = current_asset_val * (1 - depreciation)
        asset_values.append(round(current_asset_val, 2))
        
        # Equity Growth
        if is_subscription:
            # Future value of a series for monthly subscriptions
            current_equity_val += annual_cost
            current_equity_val = current_equity_val * (1 + annual_return + div_yield)
        else:
            # Standard compound growth
            current_equity_val = current_equity_val * (1 + annual_return + div_yield)
            
        equity_values.append(round(current_equity_val, 2))
        
    # Calculate the "Free Item" milestone (when returns > original price)
    milestone = "Never"
    if current_equity_val > price:
        for i, val in enumerate(equity_values):
            if (val - price) >= price: # Profit equals the original cost
                milestone = f"Year {i}"
                break

    return {
        "labels": labels,
        "asset_values": asset_values,
        "equity_values": equity_values,
        "milestone": milestone,
        "final_equity": round(equity_values[-1], 2)
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    item_name = data.get('item_name', 'Item')
    price = float(data.get('price', 0))
    ticker = data.get('ticker', 'AAPL')
    years = int(data.get('years', 5))
    is_subscription = data.get('is_subscription', False)
    category = data.get('category', 'tech')

    # Parallelise the API fetch and any background processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_fin_data = executor.submit(fetch_financial_data, ticker)
        fin_data = future_fin_data.result()

    results = calculate_projection(price, is_subscription, years, fin_data, category)
    
    # Generate the witty verdict
    verdict = ""
    if is_subscription:
        verdict = f"That £{price}/month habit costs you £{results['final_equity']} in lost capitalisation over {years} years. Time to cancel?"
    else:
        verdict = f"Buying this {item_name} sacrifices £{results['final_equity']} in potential wealth. Is the dopamine hit really worth it?"

    results['verdict'] = verdict
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, threaded=True)