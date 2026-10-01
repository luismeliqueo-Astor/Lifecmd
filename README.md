# Lifecmd
## Indicador TradingView: Señales Compra/Venta 5m

Archivo: [`tradingview/senales_5m.pine`](tradingview/senales_5m.pine) (Pine Script v6, para gráficos de 5 minutos).

### Instalación
1. Abre TradingView con el gráfico en **5 min**.
2. Abre el **Editor Pine** (pestaña inferior), borra lo que haya y pega el contenido completo del archivo.
3. Pulsa **Añadir al gráfico**. Verás las EMAs 9/21/200, el fondo sombreado según la tendencia, las etiquetas COMPRA/VENTA con sus niveles SL/TP y un panel de estado arriba a la derecha.

### Cómo decide una señal
Una **COMPRA** aparece solo si **todas** las condiciones activadas se cumplen al cierre de la vela (la **VENTA** es la imagen espejo):

| # | Condición | Por defecto |
|---|-----------|-------------|
| 1 | Tendencia 5m: cierre sobre la EMA 200 | Activo |
| 2 | Tendencia mayor: cierre de 15m sobre su EMA 50 (usa la vela de 15m ya cerrada, no repinta) | Activo |
| 3 | Disparador: cruce EMA 9/21 **o** retroceso a la EMA 21 con reanudación | Ambos |
| 4 | ADX ≥ 20 y +DI > -DI (descarta mercado lateral) | Activo |
| 5 | RSI entre 50 y 70, histograma MACD positivo | Activo |
| 6 | Volumen ≥ promedio de 20 velas | Activo |
| 7 | Vela alcista con cuerpo ≥ 0,3 ATR | Activo |
| 8 | Precio a menos de 1,5 ATR de la EMA 21 (no persigue el precio) | Activo |
| 9 | VWAP y horario de sesión | Opcionales |

Además se marca **una sola señal por tramo de tendencia** (cada cruce de la EMA 9 con la EMA 21 abre un tramo nuevo) y se exige un mínimo de velas entre señales. Las señales se confirman al cierre de la vela, por lo que **no repintan**.

### Alertas
Crea una alerta sobre el indicador y elige la condición **Señal COMPRA**, **Señal VENTA** o **Cualquier señal**, con frecuencia **"Una vez por cierre de vela"**. El mensaje incluye precio, SL y TP.

### Ajustes
- **Más precisión, menos señales:** sube el ADX mínimo a 25, activa *Exigir pendiente de la EMA tendencia* y sube el cuerpo mínimo de la vela.
- **Más señales:** cambia *Máx. señales por tramo* a 2 o 3, baja el ADX mínimo a 15 o desactiva el filtro de volumen (necesario en símbolos sin volumen real).
- **Medir la precisión real:** el final del archivo explica cómo convertirlo en estrategia para usar el *Probador de estrategias* y ver el porcentaje de aciertos con los SL/TP del propio indicador.

Ningún indicador acierta siempre: pruébalo en el símbolo que operes antes de usarlo con dinero real.
