"""Reproduce todos los resultados del README.

    python3 run_backtest.py

Escribe tablas en resultados/.
"""
import os

import numpy as np
import pandas as pd

from backtest import (FEE_PER_SIDE, buy_and_hold, evaluate, sma_filter, tms,
                      tms_regime, trades, trend_score)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultados")
PERIODS = {
    "2014-2020 (diseño)": (None, "2020-12-31"),
    "2021-2026 (fuera de muestra)": ("2021-01-01", None),
    "Total": (None, None),
}


def load():
    btc = pd.read_csv(os.path.join(HERE, "data/BTCUSD_1d.csv"),
                      index_col=0, parse_dates=True)["close"]
    cl = pd.read_csv(os.path.join(HERE, "data/crypto_daily_close_usd.csv"),
                     index_col=0, parse_dates=True)
    coins = {c: cl[c].dropna() for c in cl if c != "BTC"}
    return btc, coins


def main():
    os.makedirs(OUT, exist_ok=True)
    btc, alts = load()
    strategies = {
        "Comprar y mantener": lambda c: buy_and_hold(c),
        "SMA200": lambda c: sma_filter(c),
        "TMS": lambda c: tms(c),
        "TMS + régimen BTC": lambda c: tms_regime(c, btc),
    }

    rows = []
    for period, (start, end) in PERIODS.items():
        for coin, px in {"BTC": btc, **alts}.items():
            if end and px.index[0] > pd.Timestamp(end) - pd.Timedelta(days=500):
                continue  # muy poca historia en ese tramo
            for name, fn in strategies.items():
                if coin == "BTC" and name == "TMS + régimen BTC":
                    continue  # para BTC es idéntico a TMS
                _, _, st = evaluate(px, fn, start=start, end=end)
                rows.append({"periodo": period, "moneda": coin,
                             "estrategia": name, **st})
    res = pd.DataFrame(rows)
    res.round(4).to_csv(os.path.join(OUT, "resumen.csv"), index=False)

    pct = ["retorno_total", "cagr", "max_dd", "exposicion"]
    fmt = lambda d: d.assign(**{k: (d[k] * 100).round(1) for k in pct if k in d}).round(2)
    cols = ["cagr", "max_dd", "sharpe", "exposicion", "operaciones", "op_por_año"]

    print("=== BTC (Bitstamp, comisión %.1f%% por lado) ===" % (FEE_PER_SIDE * 100))
    b = res[res.moneda == "BTC"].set_index(["periodo", "estrategia"])[cols]
    print(fmt(b).to_string())

    print("\n=== Altcoins: mediana de %d monedas ===" % len(alts))
    a = res[res.moneda != "BTC"]
    med = a.groupby(["periodo", "estrategia"])[cols].median()
    med["monedas_con_ganancia"] = a.groupby(["periodo", "estrategia"]).cagr.apply(
        lambda x: f"{(x > 0).sum()}/{len(x)}")
    print(fmt(med).to_string())

    # --- Sensibilidad BTC: comisión y retraso al ejecutar
    sens = []
    for fee in (0.0, 0.004, 0.005, 0.0075, 0.01):
        for lag in (0, 1, 2):
            _, _, st = evaluate(btc, tms, fee=fee, lag=lag)
            sens.append({"comision_por_lado_%": fee * 100,
                         "dias_de_retraso": lag, **st})
    sens = pd.DataFrame(sens)
    sens.round(4).to_csv(os.path.join(OUT, "btc_sensibilidad.csv"), index=False)
    print("\n=== BTC TMS: sensibilidad a comisión y retraso (Total) ===")
    print(fmt(sens[["comision_por_lado_%", "dias_de_retraso", "cagr",
                    "max_dd", "sharpe"]]).to_string(index=False))

    # --- Retorno por año BTC
    eq_t, pos_t, _ = evaluate(btc, tms)
    eq_b, _, _ = evaluate(btc, buy_and_hold)
    yearly = pd.DataFrame({
        "TMS_%": eq_t.resample("YE").last().pct_change(),
        "comprar_y_mantener_%": eq_b.resample("YE").last().pct_change(),
    })
    first = pd.DataFrame({"TMS_%": [eq_t.resample("YE").last().iloc[0] - 1],
                          "comprar_y_mantener_%": [eq_b.resample("YE").last().iloc[0] - 1]},
                         index=[eq_t.resample("YE").last().index[0]])
    yearly = pd.concat([first, yearly.iloc[1:]])
    yearly.index = yearly.index.year
    yearly.index.name = "año"
    (yearly * 100).round(1).to_csv(os.path.join(OUT, "btc_por_anio.csv"))
    print("\n=== BTC retorno por año (%) ===")
    print((yearly * 100).round(1).to_string())

    # --- Lista de operaciones BTC
    t = trades(btc.reindex(pos_t.index), pos_t)
    t["precio_entrada"] = btc.reindex(t.entrada).values
    t["precio_salida"] = btc.reindex(t.salida).values
    t["retorno"] = (t.retorno * 100).round(1)
    t.to_csv(os.path.join(OUT, "btc_operaciones.csv"), index=False)
    print(f"\nOperaciones BTC: {len(t)}, ganadoras {int((t.retorno > 0).sum())}, "
          f"ganancia media {t[t.retorno > 0].retorno.mean():.1f}%, "
          f"pérdida media {t[t.retorno <= 0].retorno.mean():.1f}%")

    # --- Curvas de capital (para el gráfico)
    pd.DataFrame({"TMS": eq_t, "comprar_y_mantener": eq_b, "posicion": pos_t}).round(5) \
        .to_csv(os.path.join(OUT, "btc_curva_capital.csv"))

    # --- Señal actual
    now = []
    btc_pos = tms(btc)
    for coin, px in {"BTC": btc, **alts}.items():
        s = trend_score(px)
        p = tms(px) if coin == "BTC" else tms_regime(px, btc)
        now.append({"moneda": coin, "fecha_dato": px.index[-1].date(),
                    "precio": px.iloc[-1], "votos_positivos": int(s.iloc[-1]),
                    "señal": "COMPRADO" if p.iloc[-1] == 1 else "FUERA (USD)",
                    "btc_en_compra": bool(btc_pos.reindex([px.index[-1]]).iloc[0])})
    now = pd.DataFrame(now)
    now.to_csv(os.path.join(OUT, "senales_actuales.csv"), index=False)
    print("\n=== Señal en el último dato disponible ===")
    print(now.to_string(index=False))


if __name__ == "__main__":
    main()
