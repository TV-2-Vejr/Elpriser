import requests
import re
import csv
from datetime import datetime, timedelta

def get_latest_euro_rate():
    try:
        res = requests.get("https://www.nationalbanken.dk/api/currencyrates?format=rss&lang=da&isoCodes=EUR")
        match = re.search(r"koster\s+([\d,]+)\s+DKK", res.text)
        if match: return float(match.group(1).replace(",", ".")) / 100
    except: pass
    return 7.4604

def run():
    eur_rate = get_latest_euro_rate()
    now = datetime.now()
    end_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=730)
    split_dt = datetime(2025, 10, 1)

    records = []

    # Elspotprices
    if start_dt < split_dt:
        end_old = min(split_dt, now).strftime("%Y-%m-%d")
        url = (f"https://api.energidataservice.dk/dataset/Elspotprices"
               f"?start={start_dt.strftime('%Y-%m-%d')}&end={end_old}"
               f"&filter=%7B%22PriceArea%22%3A%5B%22DK1%22%2C%22DK2%22%5D%7D&limit=50000")
        res = requests.get(url).json()
        for r in res.get('records', []):
            records.append({'t': r['HourDK'], 'a': r['PriceArea'], 'dkk': r['SpotPriceDKK'], 'eur': r['SpotPriceEUR']})

    # DayAheadPrices
    if now > split_dt:
        start_new = max(start_dt, split_dt).strftime("%Y-%m-%d")
        url = (f"https://api.energidataservice.dk/dataset/DayAheadPrices"
               f"?start={start_new}&end={end_dt.strftime('%Y-%m-%d')}"
               f"&filter=%7B%22PriceArea%22%3A%5B%22DK1%22%2C%22DK2%22%5D%7D&limit=50000")
        res = requests.get(url).json()
        for r in res.get('records', []):
            records.append({'t': r['TimeDK'], 'a': r['PriceArea'], 'dkk': r['DayAheadPriceDKK'], 'eur': r['DayAheadPriceEUR']})

    months = {}
    for r in records:
        p_mwh = r['dkk'] if r['dkk'] is not None else (r['eur'] * eur_rate if r['eur'] is not None else None)
        if p_mwh is None: continue
        
        p_kwh = (p_mwh / 1000) * 1.25
        m_key = r['t'][:7]
        if m_key not in months: months[m_key] = {"DK1": [], "DK2": []}
        months[m_key][r['a']].append(p_kwh)

    with open("monthly_power_prices.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Month", "Jylland + Fyn", "Sjælland + Øer"])
        for m in sorted(months.keys()):
            jf = sum(months[m]["DK1"])/len(months[m]["DK1"]) if months[m]["DK1"] else ""
            oe = sum(months[m]["DK2"])/len(months[m]["DK2"]) if months[m]["DK2"] else ""
            writer.writerow([m, f"{jf:.3f}" if jf else "", f"{oe:.3f}" if oe else ""])

if __name__ == "__main__":
    run()
