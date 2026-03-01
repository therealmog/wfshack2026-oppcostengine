import urllib.request
import csv
import json
import concurrent.futures
import codecs
import os
import yfinance as yf

def fetch_sp500():
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    try:
        response = urllib.request.urlopen(url, timeout=10)
        reader = csv.DictReader(codecs.iterdecode(response, 'utf-8'))
        return [{"name": row['Security'], "ticker": row['Symbol']} for row in reader]
    except: 
        return []

def fetch_ftse100():
    return [
        {"name": "Tesco", "ticker": "TSCO.L"}, {"name": "Sainsbury's", "ticker": "SBRY.L"},
        {"name": "Diageo", "ticker": "DGE.L"}, {"name": "Unilever", "ticker": "ULVR.L"},
        {"name": "Rolls-Royce", "ticker": "RR.L"}, {"name": "Vodafone", "ticker": "VOD.L"},
        {"name": "Next", "ticker": "NXT.L"}, {"name": "Marks & Spencer", "ticker": "MKS.L"},
        {"name": "HSBC", "ticker": "HSBA.L"}, {"name": "Barclays", "ticker": "BARC.L"},
        {"name": "BP", "ticker": "BP.L"}, {"name": "Shell", "ticker": "SHEL.L"},
        {"name": "AstraZeneca", "ticker": "AZN.L"}, {"name": "easyJet", "ticker": "EZJ.L"},
        {"name": "Burberry", "ticker": "BRBY.L"}, {"name": "JD Sports", "ticker": "JD.L"},
        {"name": "Lloyds Banking Group", "ticker": "LLOY.L"}, {"name": "NatWest", "ticker": "NWG.L"},
        {"name": "BT Group", "ticker": "BT-A.L"}, {"name": "Greggs", "ticker": "GRG.L"}
    ]

def process_company(co):
    name = co['name']
    ticker = co['ticker']
    # Default state ensures ALL keys always exist
    result = {"name": name, "ticker": ticker, "sector": "unclassified", "has_news": False}
    
    try:
        yt = yf.Ticker(ticker)
        
        # 1. Fetch Sector and force lowercase with dashes
        try:
            raw_sector = yt.info.get("sector", "")
            if raw_sector:
                # "Consumer Cyclical" -> "consumer-cyclical"
                result["sector"] = str(raw_sector).lower().replace(" ", "-")
        except Exception:
            pass 
            
        # 2. Fetch News and boolean flag
        try:
            news = yt.news
            if news and len(news) > 0:
                result["has_news"] = True
        except Exception:
            pass 
            
    except Exception as e:
        print(f"Skipping {ticker} data pull: {e}")
        
    return result

def generate():
    print("Fetching base lists...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        f1 = executor.submit(fetch_sp500)
        f2 = executor.submit(fetch_ftse100)
        all_companies = f1.result() + f2.result()

    final_db = []
    total = len(all_companies)
    print(f"Enhancing {total} companies via Yahoo API in parallel. Please wait...")

    # Using 10 workers for stability to avoid rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_company, co): co for co in all_companies}
        
        for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                final_db.append(future.result())
                if count % 50 == 0:
                    print(f"Progress: {count}/{total} processed...")
            except Exception as e:
                print(f"Thread failed: {e}")

    # Sort alphabetically for the UI
    final_db = sorted(final_db, key=lambda x: x['name'])

    # Write the brand new file
    print("Writing cleanly formatted JSON to disk...")
    with open('companies.json', 'w', encoding='utf-8') as f:
        json.dump(final_db, f, indent=4)
        
    print("Complete! Check your folder for companies.json.")

if __name__ == "__main__":
    generate()