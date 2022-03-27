import logging
from datetime import datetime, timedelta

import MetaTrader5 as mt5
from matplotlib import pyplot as plt
from numpy import char
import pandas as pd
import pytz
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
    
    client = MT5Client()

    frame = '1min'
    
    start_date = datetime(2022, 3, 25, 9, 0, tzinfo=pytz.utc)
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
    chart['sma_1'] = chart.rolling(10, min_periods=1)['close'].mean()
    chart['std'] = chart.rolling(10, min_periods=1)['close'].std()
    chart['bolu'] = chart['sma_1'] + 2 * chart['std']
    chart['bold'] = chart['sma_1'] - 2 * chart['std']

    logging.info('Trading simulate...')

    pltchart(chart)


if __name__ == "__main__":
    main()
