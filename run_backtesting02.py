import logging
from datetime import datetime, timedelta
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

    symbol = 'WIN$'

    start_date = datetime(2022, 4, 4, 9, 0, tzinfo=pytz.utc)
    end_date = datetime(2022, 4, 4, 18, 20, tzinfo=pytz.utc)

    ticks = Data.ticks(symbol, start_date, end_date)

    if len(ticks) == 0:
        logging.info('No data...')
        quit()

    logging.info('Computing...')

    chart = ticks.resample('15s')['last'].ohlc()
    chart.dropna(inplace=True)

    range = float(100)
    valuerange = []

    for _, row in chart.iterrows():
        if not valuerange:
            valuerange.append(row['open'] - row['open'] % range)
            continue
        if row['open'] > valuerange[-1] + range:
            valuerange.append(row['open'] - row['open'] % range)
        elif row['open'] < valuerange[-1] - range:
            valuerange.append(row['open'] - row['open'] % range + range)
        else:
            valuerange.append(valuerange[-1])

    chart['linemiddle'] = valuerange
    chart['lineup'] = chart['linemiddle'] + range
    chart['linedown'] = chart['linemiddle'] - range

    chart['sell'] = np.where(
        chart['open'] > chart['linemiddle'], True, False)
    chart['buy'] = np.where(
        chart['open'] < chart['linemiddle'], True, False)

    # chart = chart[start_date:start_date+timedelta(minutes=30)]

    simplifyorders(chart)
    sumprofit(chart, 0)

    print(chart)

    pltchart(chart, None, price='open')


if __name__ == "__main__":
    main()
