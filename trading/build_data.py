"""Descarga y arma los datos históricos de data/.

    python3 build_data.py

Fuentes (repos públicos de GitHub, sin API key):
  - BTC/USD de Bitstamp a 1 minuto, 2012 en adelante, actualizado a diario:
    https://github.com/ff137/bitstamp-btcusd-minute-data
  - Precio diario en USD de altcoins (Coin Metrics Community Data):
    https://github.com/coinmetrics/data
"""
import http.client
import io
import os
import time
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
BITSTAMP = "https://raw.githubusercontent.com/ff137/bitstamp-btcusd-minute-data/main/data/"
COINMETRICS = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/{}.csv"
# Solo monedas con precio diario largo en Coin Metrics (SOL, AVAX y SHIB no lo traen).
ALTS = ["eth", "ltc", "bch", "doge", "link", "uni", "aave", "dot", "xrp", "ada", "xlm", "trx"]
START = "2014-01-01"


def fetch(url, tries=4):
    print("descargando", url)
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=600) as r:
                return io.BytesIO(r.read())
        except (OSError, http.client.IncompleteRead) as e:
            if i == tries - 1:
                raise
            print(f"  reintentando ({e.__class__.__name__})")
            time.sleep(2 ** (i + 1))


def build_btc():
    hist = pd.read_csv(fetch(BITSTAMP + "historical/btcusd_bitstamp_1min_2012-2025.csv.gz"),
                       compression="gzip")
    new = pd.read_csv(fetch(BITSTAMP + "updates/btcusd_bitstamp_1min_latest.csv"))
    m = pd.concat([hist, new]).drop_duplicates("timestamp").sort_values("timestamp")
    m.index = pd.to_datetime(m.pop("timestamp"), unit="s")
    m = m[m.index >= START]
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    for tf in ("1d", "4h", "1h"):
        r = m.resample(tf.replace("d", "D")).agg(agg).dropna()
        r = r[r.index < m.index[-1].floor(tf.replace("d", "D"))]  # sin la vela en curso
        r.index.name = "date"
        r.round(2).to_csv(os.path.join(OUT, f"BTCUSD_{tf}.csv"))
        print(f"BTCUSD_{tf}: {len(r)} velas, {r.index[0]} -> {r.index[-1]}")


def build_alts():
    closes = {}
    for c in ALTS:
        d = pd.read_csv(fetch(COINMETRICS.format(c)), low_memory=False)
        d = d.set_index(pd.to_datetime(d["time"]))
        s = None
        for col in ("ReferenceRateUSD", "ReferenceRate", "PriceUSD"):
            if col in d:
                s = d[col] if s is None else s.fillna(d[col])
        closes[c.upper()] = s.dropna()
    cl = pd.DataFrame(closes).sort_index()
    cl = cl[cl.index >= START].dropna(how="all")
    cl.index.name = "date"
    cl.to_csv(os.path.join(OUT, "crypto_daily_close_usd.csv"), float_format="%.8g")
    print(f"altcoins: {cl.shape[1]} monedas, hasta {cl.index[-1].date()}")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    build_btc()
    build_alts()
