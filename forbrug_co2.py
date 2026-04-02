import requests
import csv
from datetime import datetime

def run():
    # 1. Hent aktuelle data (PowerSystemRightNow)
    url_now = "https://api.energidataservice.dk/dataset/PowerSystemRightNow?limit=1"
    res_now = requests.get(url_now).json()
    r = res_now['records'][0]

    # Beregninger
    # Vind = Offshore + Onshore
    vind = (r['OffshoreWindPower'] or 0) + (r['OnshoreWindPower'] or 0)
    # Sol
    sol = (r['SolarPower'] or 0)
    # Produktion (Total) = Vind + Sol + Store værker + Små værker
    produktion = vind + sol + (r['ProductionGe100MW'] or 0) + (r['ProductionLt100MW'] or 0)
    # Forbrug = Produktion - Exchange_Sum (Exchange_Sum er positiv ved eksport, negativ ved import)
    forbrug = produktion - (r['Exchange_Sum'] or 0)
    
    # Grøn andel (Vind + Sol) / Forbrug
    # Vi sikrer os mod division med nul og sætter max til 100%
    groen_procent = 0
    if forbrug > 0:
        groen_procent = min(100, round(((vind + sol) / forbrug) * 100))

    # 2. Hent CO2 prognose (CO2EmisProg)
    # Vi henter for de næste 10 timer for DK1 (Jylland/Fyn) som repræsentant
    url_prog = "https://api.energidataservice.dk/dataset/CO2EmisProg?limit=10&filter=%7B%22PriceArea%22%3A%5B%22DK1%22%5D%7D"
    res_prog = requests.get(url_prog).json()
    prog_records = res_prog['records']

    # 3. Skriv til CSV
    with open('forbrugco2.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Første sektion: Aktuelle tal
        writer.writerow(["type", "value"])
        writer.writerow(["CO2", f"{r['CO2Emission']} g CO2/kWh"])
        writer.writerow(["Sol", f"{int(sol)} MW"])
        writer.writerow(["Vind", f"{int(vind)} MW"])
        writer.writerow(["Forbrug", f"{int(forbrug)} MW"])
        writer.writerow(["Grøn", f"{groen_procent} %"])
        writer.writerow(["Tid", r['Minutes1DK']])
        
        # Mellem-header
        writer.writerow(["time", "forecast CO2"])
        
        # Anden sektion: Prognose (Sorteret efter tid)
        for p in reversed(prog_records):
            # Formatér tid fra "2026-03-30T14:00:00" til "14:00"
            tid_kort = p['Minutes1DK'][11:16]
            writer.writerow([tid_kort, p['CO2Emission']])

    print("✔ forbrugco2.csv er gemt.")

if __name__ == "__main__":
    run()
