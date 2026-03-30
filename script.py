import requests
import re
import csv
import json
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo

def get_latest_euro_rate():
    rss_url = "https://www.nationalbanken.dk/api/currencyrates?format=rss&lang=da&isoCodes=EUR"
    try:
        res = requests.get(rss_url, timeout=10)
        match = re.search(r"koster\s+([\d,]+)\s+DKK", res.text)
        if match:
            return float(match.group(1).replace(",", ".")) / 100
    except:
        print("⚠ Kunne ikke hente live-kurs, bruger fallback 7.4604")
    return 7.4604

def get_local_iso_now():
    # Hent nuværende tidspunkt i dansk tidszone (håndterer automatisk sommer/vintertid)
    tz = ZoneInfo("Europe/Copenhagen")
    now = datetime.now(tz)
    # Rund ned til nærmeste hele time
    now = now.replace(minute=0, second=0, microsecond=0)
    return now

def run():
    eur_rate = get_latest_euro_rate()
    # Nu returnerer denne den korrekte danske tid uanset årstid
    start_dt = get_local_iso_now()
    end_dt = start_dt + timedelta(hours=36)
    
    # Vi bruger isoformat() eller strftime, men fjerner tidszone-offsettet fra strengen til API'et
    start_str = start_dt.strftime("%Y-%m-%dT%H:%M")
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M")
    
    print(f"ℹ Henter data fra (Dansk tid): {start_str} til {end_str}")

    url = (f"https://api.energidataservice.dk/dataset/DayAheadPrices"
           f"?start={start_str}&end={end_str}"
           f"&filter=%7B%22PriceArea%22%3A%5B%22DK1%22%2C%22DK2%22%5D%7D&limit=500")

    res = requests.get(url)
    data = res.json()
    records = data.get('records', [])

    if not records:
        print("Ingen data modtaget")
        return

    jf_raw = []
    oe_raw = []

    for r in records:
        # API'et returnerer TimeDK, som vi kan sammenligne direkte med vores start_str
        if r['TimeDK'] < start_str:
            continue

        price_mwh = r.get('DayAheadPriceDKK')
        if price_mwh is None:
            price_mwh = (r.get('DayAheadPriceEUR') or 0) * eur_rate
        
        # Pris pr kWh inkl moms
        price_kwh = (price_mwh / 1000) * 1.25
        obj = {"time": r['TimeDK'], "price": price_kwh}

        if r['PriceArea'] == "DK1":
            jf_raw.append(obj)
        else:
            oe_raw.append(obj)

    # Extrema
    def get_extrema(arr):
        if not arr: return {"min": {"time": "-", "price": 0}, "max": {"time": "-", "price": 0}}
        return {
            "min": min(arr, key=lambda x: x['price']),
            "max": max(arr, key=lambda x: x['price'])
        }

    jf_ex = get_extrema(jf_raw)
    oe_ex = get_extrema(oe_raw)

    # Group by hour
    times = {}
    for r in jf_raw:
        h = r['time'][:13] + ":00"
        if h not in times: times[h] = {"jf": [], "oe": []}
        times[h]["jf"].append(r['price'])
    for r in oe_raw:
        h = r['time'][:13] + ":00"
        if h not in times: times[h] = {"jf": [], "oe": []}
        times[h]["oe"].append(r['price'])

    # Skriv data.csv
    with open('data.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "Jylland + Fyn", "Sjælland + Øer"])
        for h in sorted(times.keys()):
            avg_jf = sum(times[h]["jf"])/len(times[h]["jf"]) if times[h]["jf"] else ""
            avg_oe = sum(times[h]["oe"])/len(times[h]["oe"]) if times[h]["oe"] else ""
            writer.writerow([h.replace("T", " "), f"{avg_jf:.2f}", f"{avg_oe:.2f}"])

    # Skriv extrema.csv
    with open('extrema.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([" ", "Jylland + Fyn", " ", "Sjælland + Øer", " "])
        writer.writerow([
            "Laveste pris", 
            jf_ex["min"]["time"].replace("T", " "), f"{jf_ex['min']['price']:.2f}",
            oe_ex["min"]["time"].replace("T", " "), f"{oe_ex['min']['price']:.2f}"
        ])
        writer.writerow([
            "Højeste pris", 
            jf_ex["max"]["time"].replace("T", " "), f"{jf_ex['max']['price']:.2f}",
            oe_ex["max"]["time"].replace("T", " "), f"{oe_ex['max']['price']:.2f}"
        ])

if __name__ == "__main__":
    run()
