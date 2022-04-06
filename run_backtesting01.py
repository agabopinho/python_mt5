import logging
from datetime import datetime
from unicodedata import decimal

import numpy as np
import pandas as pd
import pytz
from _odd.run_backtesting8 import simplifyorders, sumprofit

from backtesting import pltchart
from backtesting.data import Data
from backtesting.transaction import Transaction

from ta.volatility import average_true_range


def tradestodataframe(trades: list[Transaction]):
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


def closelasttrade(chart, trades):
    lasttrade = trades[-1] if trades else None
    if lasttrade and lasttrade.is_open:
        lasttrade.close(chart.iloc[-1].name, chart.iloc[-1]['close'])


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WDOK22'

    start_date = datetime(2022, 4, 1, 9, 0, tzinfo=pytz.utc)
    end_date = datetime(2022, 4, 1, 18, 20, tzinfo=pytz.utc)

    ticks = Data.ticks(symbol, start_date, end_date)

    if len(ticks) == 0:
        logging.info('No data...')
        quit()

    logging.info('Computing...')

    chart = ticks.resample('2s')['last'].ohlc()
    chart.dropna(inplace=True)

    window = chart.shift(1).rolling(5, min_periods=0)

    chart['lineup'] = window['high'].max()
    chart['linedown'] = window['low'].min()
    chart['linemiddle'] = (chart['lineup'] + chart['linedown']) / 2
    chart['sma_1'] = chart.shift(1).rolling(5, min_periods=0)['close'].mean()

    chart['delta'] = (chart['sma_1'] - chart['linemiddle']).round(decimals=2)
    chart['detal_ema'] = chart.rolling(5, min_periods=0)['delta'].mean()

    chart['buy'] = np.where(chart['delta'] > chart['detal_ema'], True, False)
    chart['sell'] = np.where(chart['delta'] < chart['detal_ema'], True, False)

    chart = chart[datetime(2022, 4, 1, 9, 0, tzinfo=pytz.utc):datetime(
        2022, 4, 1, 9, 10, tzinfo=pytz.utc)]

    simplifyorders(chart)
    sumprofit(chart, 0)

    print(chart)

    pltchart(chart, None, price='open')


if __name__ == "__main__":
    main()
