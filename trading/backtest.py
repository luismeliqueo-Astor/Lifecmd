"""Backtest de indicadores de tendencia para cripto (solo largo, spot).

Supuestos de ejecución (pensados para Zesty):
  - La señal se calcula con el cierre diario (00:00 UTC) y se ejecuta a ese
    precio, o `lag` días después si se opera con retraso.
  - Comisión Zesty: 0.4% por compra y 0.4% por venta. Se suma 0.1% de
    deslizamiento por lado -> 0.5% por lado por defecto.
  - Sin apalancamiento ni cortos: la posición es 0 (USD) o 1 (cripto).
"""
import numpy as np
import pandas as pd

FEE_PER_SIDE = 0.005
DAYS_PER_YEAR = 365


# ---------------------------------------------------------------- señales
def buy_and_hold(close):
    return pd.Series(1.0, index=close.index)


def sma_filter(close, n=200):
    """Clásico: comprado mientras el cierre esté sobre la SMA(n)."""
    return (close > close.rolling(n).mean()).astype(float)


def ema_cross(close, fast=20, slow=100):
    return (close.ewm(span=fast, adjust=False).mean()
            > close.ewm(span=slow, adjust=False).mean()).astype(float)


def donchian(close, entry=50, exit=20):
    """Ruptura de canal: compra al romper el máximo de `entry` días,
    vende al perder el mínimo de `exit` días (solo cierres)."""
    hi = close.rolling(entry).max().shift(1)
    lo = close.rolling(exit).min().shift(1)
    return _latch(close > hi, close < lo)


TMS_LOOKBACKS = (30, 60, 120, 240)


def trend_score(close, lookbacks=TMS_LOOKBACKS):
    """Cuántos horizontes de momentum son positivos (0..len(lookbacks))."""
    votes = [(close > close.shift(n)).astype(float) for n in lookbacks]
    score = sum(votes)
    score[close.shift(max(lookbacks)).isna()] = np.nan
    return score


def tms(close, lookbacks=TMS_LOOKBACKS, buy_at=3, sell_at=1):
    """Trend Momentum Score (TMS), el indicador propuesto.

    Vota el momentum en 4 horizontes (30, 60, 120 y 240 días): cada voto es
    "el cierre de hoy está sobre el cierre de hace N días".
    Compra cuando >= `buy_at` votos son positivos y vende cuando quedan
    <= `sell_at`. La zona intermedia mantiene la posición previa
    (histéresis), lo que reduce operaciones falsas y comisiones.
    """
    s = trend_score(close, lookbacks)
    return _latch(s >= buy_at, s <= sell_at)


def tms_regime(close, btc_close, **kw):
    """TMS para altcoins: solo comprado si la alt Y el BTC están en señal
    de compra. Las alts caen más fuerte que BTC en los mercados bajistas."""
    btc_pos = tms(btc_close.dropna(), **kw).reindex(close.index).fillna(0.0)
    return tms(close, **kw) * btc_pos


def _latch(enter, leave):
    """Convierte condiciones de entrada/salida en una posición 0/1."""
    pos = np.zeros(len(enter))
    e, l = enter.to_numpy(), leave.to_numpy()
    cur = 0.0
    for i in range(len(pos)):
        if cur == 0 and e[i]:
            cur = 1.0
        elif cur == 1 and l[i]:
            cur = 0.0
        pos[i] = cur
    return pd.Series(pos, index=enter.index)


# ---------------------------------------------------------------- motor
def run(close, pos, fee=FEE_PER_SIDE, lag=0):
    """Devuelve la curva de capital diaria (empieza en 1.0).

    `pos[t]` se decide con datos hasta el cierre t y gana el retorno t->t+1.
    Con `lag`=1 se ejecuta un día más tarde (operador que llega tarde).
    """
    close = close.dropna()
    pos = pos.reindex(close.index).fillna(0.0).shift(lag).fillna(0.0)
    ret = close.pct_change().fillna(0.0)
    held = pos.shift(1).fillna(0.0)
    cost = pos.diff().abs().fillna(pos.iloc[0]) * fee
    equity = ((1 + held * ret) * (1 - cost)).cumprod()
    return equity, pos


def trades(close, pos, fee=FEE_PER_SIDE):
    """Lista de operaciones cerradas (y la abierta, marcada a mercado)."""
    close = close.reindex(pos.index)
    d = pos.diff().fillna(pos.iloc[0])
    entries = list(pos.index[d > 0])
    exits = list(pos.index[d < 0])
    out = []
    for i, t_in in enumerate(entries):
        t_out = exits[i] if i < len(exits) else None
        p_out = close[t_out] if t_out is not None else close.iloc[-1]
        r = p_out / close[t_in] * (1 - fee) ** 2 - 1
        out.append({"entrada": t_in, "salida": t_out,
                    "dias": ((t_out or close.index[-1]) - t_in).days,
                    "retorno": r})
    return pd.DataFrame(out)


def stats(equity, pos, close=None, fee=FEE_PER_SIDE):
    eq = equity.dropna()
    years = (eq.index[-1] - eq.index[0]).days / DAYS_PER_YEAR
    r = eq.pct_change().dropna()
    dd = eq / eq.cummax() - 1
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    sharpe = r.mean() / r.std() * np.sqrt(DAYS_PER_YEAR) if r.std() > 0 else np.nan
    out = {
        "retorno_total": eq.iloc[-1] - 1,
        "cagr": cagr,
        "max_dd": dd.min(),
        "sharpe": sharpe,
        "calmar": cagr / -dd.min() if dd.min() < 0 else np.nan,
        "exposicion": pos.reindex(eq.index).mean(),
    }
    if close is not None:
        t = trades(close, pos.reindex(eq.index), fee)
        out["operaciones"] = len(t)
        out["aciertos"] = (t.retorno > 0).mean() if len(t) else np.nan
        out["op_por_año"] = len(t) / years if years > 0 else np.nan
    return out


def evaluate(close, signal_fn, start=None, end=None, warmup=max(TMS_LOOKBACKS), **kw):
    """Calcula la señal con todo el historial (sin mirar al futuro) y mide
    solo en [start, end]. `warmup` días iniciales se descartan."""
    close = close.dropna()
    pos = signal_fn(close)
    lag = kw.pop("lag", 0)
    fee = kw.pop("fee", FEE_PER_SIDE)
    pos = pos.iloc[warmup:] if start is None else pos
    c = close.loc[pos.index[0]:]
    if start is not None:
        c = c.loc[max(pd.Timestamp(start), close.index[min(warmup, len(close) - 1)]):]
    if end is not None:
        c = c.loc[:end]
    p = pos.reindex(c.index)
    # al inicio de la ventana la posición se "abre" pagando comisión
    eq, p = run(c, p, fee=fee, lag=lag)
    return eq, p, stats(eq, p, c, fee)
