import logging
from datetime import datetime

import MetaTrader5 as mt5
import numpy as np
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


def simplifyorders(chart: pd.DataFrame):
    buy = []
    sell = []

    is_buy = False
    is_sell = False

    for _, r in chart.iterrows():
        if r['buy'] and not is_buy:
            is_buy = True
            is_sell = False
            buy.append(True)
            sell.append(False)

            continue
        elif r['sell'] and not is_sell:
            is_sell = True
            is_buy = False
            sell.append(True)
            buy.append(False)

            continue

        buy.append(False)
        sell.append(False)

    chart['buy'] = buy
    chart['sell'] = sell


def sumprofit(chart: pd.DataFrame):
    price = 0
    sum = 0

    for _, r in chart.iterrows():
        if not price:
            if r['buy'] or r['sell']:
                price = r['open']

            continue

        if r['buy']:
            sum += price - r['open']
            price = r['open']

        if r['sell']:
            sum += r['open'] - price
            price = r['open']

    logging.info('Profit {}pips'.format(sum))


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WIN$'
    frame = '20s'

    client = MT5Client()

    start_date = datetime(2022, 3, 21, 9, 0, tzinfo=pytz.utc)
    end_date = datetime(2022, 3, 28, 17, 20, 0, tzinfo=pytz.utc)

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

    ind = ta.momentum.RSIIndicator((chart['open'] + chart['close']) / 2, window=5)

    chart['rsi'] = ind.rsi()
    chart['rsi_up'] = 70
    chart['rsi_down'] = 30

    chart['buy'] = np.where((chart['rsi'].shift(1) > chart['rsi_up'].shift(1)), True, False)
    chart['sell'] = np.where((chart['rsi'].shift(1) < chart['rsi_down'].shift(1)), True, False)

    simplifyorders(chart)
    sumprofit(chart)

    pltchart(chart)


if __name__ == "__main__":
    main()
