import urllib.request
import csv
import json
import concurrent.futures
import codecs

# This dictionary maps Tickers to recognisable consumer products
# It enriches the names so users can search by the product they actually bought.
PRODUCT_MAP = {
    "AAPL": "iPhone, iPad, Mac, AirPods",
    "MSFT": "Xbox, Surface, Windows",
    "SONY": "PlayStation, Bravia TVs, Headphones",
    "AMZN": "Prime, Kindle, Echo/Alexa",
    "GOOGL": "Android, Pixel, YouTube",
    "NFLX": "Streaming Subscription",
    "TSLA": "Model 3, Model Y, Solar",
    "NKE": "Trainers, Jordans, Activewear",
    "SBUX": "Coffee, Frappuccino",
    "MCD": "Big Mac, Fast Food",
    "TSCO.L": "Groceries, Clubcard",
    "SBRY.L": "Groceries, Argos",
    "DGE.L": "Guinness, Smirnoff, Tanqueray",
    "ULVR.L": "Dove, Ben & Jerry's, Magnum",
    "RR.L": "Jet Engines, Luxury Cars",
    "VOD.L": "Mobile Contract, Broadband",
    "META": "Instagram, WhatsApp, Quest VR",
    "SPOT": "Music Subscription",
    "DIS": "Disney+, Marvel, Star Wars",
    "NVDA": "Graphics Cards, RTX, AI Tech",
    "NXT.L": "Clothing, Home Decor",
    "MKS.L": "Foodhall, Quality Clothing",
    "EZJ.L": "Flights, Holidays",
    "RYA.I": "Cheap Flights",
    "BMW.DE": "1 Series, 3 Series, Mini",
    "VOW3.DE": "VW, Audi, Porsche",
    "LULU": "Yoga Pants, Activewear",
    "EA": "FC 24, FIFA, Sims",
    "TTWO": "GTA V, Red Dead Redemption"
}

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
        
        # Enrich the name if we have products in our map
        if ticker in PRODUCT_MAP:
            name = f"{name} ({PRODUCT_MAP[ticker]})"
        
        final_db.append({"name": name, "ticker": ticker})

    # Sort alphabetically for the UI
    final_db = sorted(final_db, key=lambda x: x['name'])

    with open('companies.json', 'w', encoding='utf-8') as f:
        json.dump(final_db, f, indent=4)
    
    print(f"Done! Created companies.json with {len(final_db)} entries.")

if __name__ == "__main__":
    generate()