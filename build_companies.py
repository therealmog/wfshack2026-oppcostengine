import urllib.request
import csv
import json
import concurrent.futures
import codecs
from yfinance import Ticker

def fetch_sp500():
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    try:
        response = urllib.request.urlopen(url, timeout=10)
        reader = csv.DictReader(codecs.iterdecode(response, 'utf-8'))
        return [{"name": row['Security'], "ticker": row['Symbol']} for row in reader]
    except: return []

def fetch_ftse100():
    # Since scraping FTSE is flaky, we use a robust hardcoded list of the top 50 UK consumer brands
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

def generate():
    print("Generating your Gold Catalogue...")
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        f1 = executor.submit(fetch_sp500)
        f2 = executor.submit(fetch_ftse100)
        all_companies = f1.result() + f2.result()

    final_db = []
    for co in all_companies:
        name = co['name']
        ticker = co['ticker']
        try:
            sector = Ticker(ticker).info["sector"]
        except:
            sector = ""

        news = ticker.news
        has_news = True
        if not news:
            has_news = False
        
        final_db.append({"name": name, "ticker": ticker,"sector":sector, "has_news": has_news})

    # Sort alphabetically for the UI
    final_db = sorted(final_db, key=lambda x: x['name'])

    with open('companies.json', 'w', encoding='utf-8') as f:
        json.dump(final_db, f, indent=4)
    
    print(f"Done! Created companies.json with {len(final_db)} entries.")

if __name__ == "__main__":
    generate()