"""Gráfico de la curva de capital de BTC (requiere correr run_backtest.py antes)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
TMS_C, BH_C = "#2a78d6", "#eb6834"

df = pd.read_csv(os.path.join(HERE, "resultados/btc_curva_capital.csv"),
                 index_col=0, parse_dates=True)
dd = df[["TMS", "comprar_y_mantener"]] / df[["TMS", "comprar_y_mantener"]].cummax() - 1

plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2})
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True,
                               gridspec_kw={"height_ratios": [2.2, 1]}, facecolor=SURFACE)
for ax in (ax1, ax2):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0)

# Tramos en efectivo (fuera de mercado)
cash = df["posicion"] == 0
starts = df.index[cash & ~cash.shift(1, fill_value=False)]
ends = df.index[cash & ~cash.shift(-1, fill_value=False)]
for s, e in zip(starts, ends):
    for ax in (ax1, ax2):
        ax.axvspan(s, e, color="#efeeea", lw=0, zorder=0)

ax1.plot(df.index, df["comprar_y_mantener"], color=BH_C, lw=2, label="Comprar y mantener")
ax1.plot(df.index, df["TMS"], color=TMS_C, lw=2, label="TMS")
ax1.set_yscale("log")
ax1.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:,.0f}x" if v >= 1 else f"{v:.1f}x"))
ax1.set_title("BTC: cuánto se multiplicó 1 USD (escala log, comisión 0.5% por lado)",
              loc="left", fontsize=12, color=INK, pad=12)
for col, c in (("TMS", TMS_C), ("comprar_y_mantener", BH_C)):
    v = df[col].iloc[-1]
    ax1.annotate(f"{v:,.0f}x", (df.index[-1], v), xytext=(6, 0), textcoords="offset points",
                 va="center", color=INK, fontsize=10)
ax1.legend(frameon=False, loc="upper left", labelcolor=INK)

ax2.plot(dd.index, dd["comprar_y_mantener"] * 100, color=BH_C, lw=1.5)
ax2.plot(dd.index, dd["TMS"] * 100, color=TMS_C, lw=1.5)
ax2.set_ylabel("Caída desde máximo (%)")
ax2.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax2.set_ylim(-90, 2)
fig.text(0.01, 0.01, "Fondo gris: TMS fuera del mercado (en USD). Datos: Bitstamp BTC/USD, ago-2014 a sep-2026.",
         color=INK2, fontsize=8.5)
fig.tight_layout(rect=(0, 0.03, 0.97, 1))
fig.savefig(os.path.join(HERE, "resultados/btc_tms.png"), dpi=130, facecolor=SURFACE)
print("ok")
