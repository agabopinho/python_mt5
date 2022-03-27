import logging
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd
import pytz
import ta

from backtesting import pltchart
from backtesting.transaction import Transaction
from strategy.mt5_client import MT5Client


def trades_todataframe(trades: list[Transaction]):
    data = [item.todict() for item in trades]

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(
        data=data,
        columns=data[0].keys())

    df.index = df['entry_time']
    df.drop(columns=['entry_time'], inplace=True)

    df['balance'] = df['pips'].cumsum()

    return df


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WINJ22'
    frame = '1min'
    
    client = MT5Client()

    start_date = datetime(2022, 3, 24, 9, 0, tzinfo=pytz.utc)
    end_date = datetime(2022, 3, 25, 17, 20, tzinfo=pytz.utc)

    client.connect()

    status, ticks = client.get_ticks(
        symbol, start_date, end_date, mt5.COPY_TICKS_ALL)

    if status != mt5.RES_S_OK:
        client.disconnect()
        quit()

    client.disconnect()

    logging.info('Computing...')
    
    chart = ticks.resample(frame)['last'].ohlc()
    chart.dropna(inplace=True)
    
    bb = ta.volatility.BollingerBands(close=chart['close'], window=10, window_dev=2)
    rsi = ta.momentum.RSIIndicator(close=chart['close'], window=14)

    chart['bolu'] = bb.bollinger_hband()
    chart['bold'] = bb.bollinger_lband()    
    chart['rsi'] = rsi.rsi()
    chart['rsi_up'] = 70
    chart['rsi_down'] = 30

    pltchart(chart)


if __name__ == "__main__":
    main()
