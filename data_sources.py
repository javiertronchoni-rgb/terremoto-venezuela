import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
HISTORIAL_CSV = os.path.join(DATA_DIR, 'historial.csv')

COLUMNS = ['timestamp', 'muertos', 'heridos', 'desaparecidos', 'replicas',
           'edificios_afectados', 'desplazados', 'fuente']

HEADERS = {
    'User-Agent': 'VenezuelaDashboard/1.0 (macOS; research)',
    'Accept': 'application/json, text/html, */*',
}

def load_historial():
    if os.path.exists(HISTORIAL_CSV):
        df = pd.read_csv(HISTORIAL_CSV, parse_dates=['timestamp'])
        return df
    return pd.DataFrame(columns=COLUMNS)

def save_historial(df):
    df.to_csv(HISTORIAL_CSV, index=False)

def extract_number(text):
    nums = re.findall(r'([\d,]+)\+?', text)
    if nums:
        return int(nums[0].replace(',', ''))
    return None

def fetch_usgs_aftershocks():
    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?"
        "format=geojson&starttime=2026-06-24&endtime=2026-07-15"
        "&minlatitude=8&maxlatitude=13&minlongitude=-72&maxlongitude=-65"
        "&minmagnitude=2.5&orderby=time"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()
        events = []
        for f in data.get('features', []):
            props = f['properties']
            ts = datetime.utcfromtimestamp(props['time'] / 1000)
            events.append({
                'time': ts,
                'mag': props['mag'],
                'place': props['place'],
                'url': props['url'],
            })
        return events
    except Exception as e:
        print(f"[USGS error] {e}")
        return []

def fetch_wikipedia_casualties():
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'parse',
        'page': '2026_Venezuela_earthquakes',
        'prop': 'text',
        'format': 'json',
        'redirects': 1,
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = resp.json()
        html = data.get('parse', {}).get('text', {}).get('*', '')

        m = re.search(
            r'Casualties\s*</th>\s*<td[^>]*>\s*(.*?)\s*</td>',
            html, re.IGNORECASE | re.DOTALL
        )
        muertos = heridos = desaparecidos = None
        if m:
            content = m.group(1)
            parts = re.findall(r'([\d,]+)\+?\s*([a-z]+)', content, re.IGNORECASE)
            for num_str, label in parts:
                num = int(num_str.replace(',', ''))
                low = label.lower()
                if any(w in low for w in ['dead', 'killed', 'death', 'muertos', 'fallecidos']):
                    muertos = num
                elif any(w in low for w in ['injured', 'injuries', 'heridos']):
                    heridos = num
                elif any(w in low for w in ['missing', 'desaparecidos']):
                    desaparecidos = num

        if muertos is None:
            death_match = re.search(r'Deaths?\s*</th>\s*<td[^>]*>\s*([^<]+)', html, re.IGNORECASE)
            if death_match:
                muertos = extract_number(death_match.group(1))

        if heridos is None:
            inj_match = re.search(r'Injured\s*</th>\s*<td[^>]*>\s*([^<]+)', html, re.IGNORECASE)
            if inj_match:
                heridos = extract_number(inj_match.group(1))

        if desaparecidos is None:
            miss_match = re.search(r'(\d[\d,]*)\s*(?:people|persons)?\s*(?:missing|unaccounted)', html, re.IGNORECASE)
            if miss_match:
                desaparecidos = extract_number(miss_match.group(1))

        print(f"[Wikipedia] casualties: {muertos} dead, {heridos} injured, {desaparecidos} missing")
        return {'muertos': muertos, 'heridos': heridos, 'desaparecidos': desaparecidos}
    except Exception as e:
        print(f"[Wikipedia error] {e}")
        return {}

def fetch_ocha_data():
    url = "https://www.unocha.org/publications/report/venezuela-bolivarian-republic/earthquakes-venezuela-situation-report-no-3-26-june-2026-time-300-pm"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        text = resp.text

        replicas = extract_number(re.search(r'(\d[\d,]*)\s*(?:aftershock|réplicas)', text, re.IGNORECASE).group(1)) if re.search(r'(\d[\d,]*)\s*(?:aftershock|réplicas)', text, re.IGNORECASE) else None
        infra = extract_number(re.search(r'(\d[\d,]*)\s*(?:infrastructure[^s]|infraestructura[^s])', text, re.IGNORECASE).group(1)) if re.search(r'(\d[\d,]*)\s*(?:infrastructure[^s]|infraestructura[^s])', text, re.IGNORECASE) else None
        displaced = extract_number(re.search(r'(\d[\d,]*)\s*(?:displaced|desplazado)', text, re.IGNORECASE).group(1)) if re.search(r'(\d[\d,]*)\s*(?:displaced|desplazado)', text, re.IGNORECASE) else None

        print(f"[OCHA] replicas={replicas}, edificios={infra}, desplazados={displaced}")
        return {'replicas': replicas, 'edificios_afectados': infra, 'desplazados': displaced}
    except Exception as e:
        print(f"[OCHA error] {e}")
        return {}

def get_current_snapshot():
    wiki = fetch_wikipedia_casualties()
    ocha = fetch_ocha_data()
    usgs = fetch_usgs_aftershocks()

    snapshot = {
        'timestamp': datetime.now(),
        'muertos': wiki.get('muertos'),
        'heridos': wiki.get('heridos'),
        'desaparecidos': wiki.get('desaparecidos'),
        'replicas': ocha.get('replicas', len(usgs)),
        'edificios_afectados': ocha.get('edificios_afectados'),
        'desplazados': ocha.get('desplazados'),
        'fuente': 'Wikipedia+OCHA+USGS',
    }
    return snapshot, usgs
