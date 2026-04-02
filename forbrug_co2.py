import requests
import csv
import json
from datetime import datetime

def run():
    try:
        # 1. Hent aktuelle data (PowerSystemRightNow)
        url_now = "https://api.energidataservice.dk/dataset/PowerSystemRightNow?limit=1"
        res_now = requests.get(url_now).json()
        
        if not res_now.get('records'):
            print("Ingen records fundet i PowerSystemRightNow")
            return
            
        r = res_now['records'][0]
        tid_nu_str = r.get('Minutes1DK') or r.get('Minutes5DK')

        # Beregninger (Vind, Sol, Forbrug, Grøn %)
        vind = (r.get('OffshoreWindPower', 0) or 0) + (r.get('OnshoreWindPower', 0) or 0)
        sol = (r.get('SolarPower', 0) or 0)
        exchange = r.get('ExchangeSum')
        if exchange is None:
            exchange_fields = [k for k in r.keys() if 'Exchange' in k]
            exchange = sum(r.get(f, 0) or 0 for f in exchange_fields)
        produktion_total = (r.get('ProductionGe100MW', 0) or 0) + (r.get('ProductionLt100MW', 0) or 0) + vind + sol
        forbrug = produktion_total - exchange
        groen_procent = min(100, round(((vind + sol) / forbrug) * 100)) if forbrug > 0 else 0

        # 2. Hent CO2 prognose (CO2EmisProg)
        # Vi henter op til 500 records for at være sikre på at dække hele døgnet
        url_prog = "https://api.energidataservice.dk/dataset/CO2EmisProg?limit=500&filter=%7B%22PriceArea%22%3A%5B%22DK1%22%5D%7D"
        res_prog = requests.get(url_prog).json()
        prog_records = res_prog.get('records', [])

        # 3. Skriv til forbrugco2.csv
        with open('forbrugco2.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Sektion 1: Aktuelle tal
            writer.writerow(["type", "value"])
            writer.writerow(["CO2", f"{r.get('CO2Emission', 0)} g CO2/kWh"])
            writer.writerow(["Sol", f"{int(sol)} MW"])
            writer.writerow(["Vind", f"{int(vind)} MW"])
            writer.writerow(["Forbrug", f"{int(forbrug)} MW"])
            writer.writerow(["Grøn", f"{groen_procent} %"])
            writer.writerow(["Tid", tid_nu_str])
            
            # Sektion 2: Prognose per time (fra næste hele time til kl. 23)
            writer.writerow(["time", "forecast CO2"])
            
            # Sorter kronologisk
            sorted_all = sorted(prog_records, key=lambda x: (x.get('Minutes5DK') or x.get('Minutes1DK', '')))
            
            for p in sorted_all:
                tid_raw = p.get('Minutes5DK') or p.get('Minutes1DK')
                
                # Tjek om tidspunktet er efter 'nu'
                if tid_raw and tid_raw > tid_nu_str:
                    timer_str = tid_raw[11:13] # HH
                    minutter_str = tid_raw[14:16] # MM
                    
                    # Tag kun hele timer (:00)
                    if minutter_str == "00":
                        tid_kort = tid_raw[11:16]
                        writer.writerow([tid_kort, p.get('CO2Emission')])
                        
                        # Stop hvis vi har skrevet kl. 23:00
                        if timer_str == "23":
                            break

    except Exception as e:
        print(f"En fejl opstod: {e}")

if __name__ == "__main__":
    run()
