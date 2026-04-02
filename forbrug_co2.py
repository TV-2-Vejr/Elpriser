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
            print("Ingen records fundet")
            return
            
        r = res_now['records'][0]
        tid_nu_str = r.get('Minutes1DK') or r.get('Minutes5DK')

        # --- BEREGNINGER ---
        ge100 = r.get('ProductionGe100MW', 0) or 0
        lt100 = r.get('ProductionLt100MW', 0) or 0
        sol = r.get('SolarPower', 0) or 0
        offshore = r.get('OffshoreWindPower', 0) or 0
        onshore = r.get('OnshoreWindPower', 0) or 0
        exchange = r.get('ExchangeSum', 0) or 0
        
        # Forbrug = Summen af alle kilder + udveksling (ExchangeSum er positiv ved import)
        forbrug = ge100 + lt100 + sol + offshore + onshore + exchange
        
        # Vind samlet
        vind_total = offshore + onshore
        
        # Grøn procent (Vind + Sol som % af forbrug)
        groen_procent = 0
        if forbrug > 0:
            groen_procent = int(round(((vind_total + sol) / forbrug) * 100))

        # 2. Hent CO2 prognose (CO2EmisProg)
        url_prog = "https://api.energidataservice.dk/dataset/CO2EmisProg?limit=500&filter=%7B%22PriceArea%22%3A%5B%22DK1%22%5D%7D"
        res_prog = requests.get(url_prog).json()
        prog_records = res_prog.get('records', [])

        # 3. Skriv til forbrugco2.csv
        with open('forbrugco2.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Sektion 1: Aktuelle tal
            writer.writerow(["type", "value"])
            writer.writerow(["CO2", f"{int(r.get('CO2Emission', 0))} g CO₂/kWh"])
            writer.writerow(["Sol", f"{int(sol)} MW"])
            writer.writerow(["Vind", f"{int(vind_total)} MW"])
            writer.writerow(["Forbrug", f"{int(forbrug)} MW"])
            writer.writerow(["Grøn", f"{int(groen_procent)} %"])
            writer.writerow(["Tid", tid_nu_str])
            
            # Sektion 2: Prognose
            writer.writerow(["time", "forecast CO₂"])
            
            # Sorter kronologisk
            sorted_all = sorted(prog_records, key=lambda x: (x.get('Minutes5DK') or x.get('Minutes1DK', '')))
            
            for p in sorted_all:
                t_raw = p.get('Minutes5DK') or p.get('Minutes1DK')
                if t_raw and t_raw > tid_nu_str:
                    if t_raw[14:16] == "00":
                        writer.writerow([t_raw[11:16], int(p.get('CO2Emission', 0))])
                        if t_raw[11:13] == "23":
                            break

    except Exception as e:
        print(f"En fejl opstod: {e}")

if __name__ == "__main__":
    run()
