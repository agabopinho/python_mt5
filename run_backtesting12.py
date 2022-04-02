import logging
from datetime import datetime

import numpy as np
import pandas as pd
import pytz

from backtesting import pltchart
from backtesting.data import Data
from run_backtesting8 import simplifyorders
from ta.momentum import rsi
from ta.trend import CCIIndicator


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WIN$'

    all_chart = pd.DataFrame()
    all_trades = pd.DataFrame()

    start_date = datetime(2022, 3, 30, 9, 0, tzinfo=pytz.utc)
    end_date = datetime(2022, 4, 1, 17, 20, tzinfo=pytz.utc)

    ticks = Data.ticks(symbol, start_date, end_date)

    if len(ticks) == 0:
        logging.info('No data...')
        quit()

    logging.info('Computing...')

    chart = ticks.resample('1min')['last'].ohlc()
    chart.dropna(inplace=True)

    chart['rsifast'] = rsi(chart['close'], window=34).ewm(
        alpha=1 / 8, min_periods=1, adjust=False).mean()
    chart['rsislow'] = rsi(chart['close'], window=144).ewm(
        alpha=1 / 8, min_periods=1, adjust=False).mean()
    chart['cci'] = CCIIndicator(
        chart['high'], chart['low'], chart['close'], window=21).cci()
    chart['ccih'] = float(100)
    chart['ccil'] = float(-100)

    chart['buy'] = np.where(
        (chart['cci'] > chart['ccih']) &
        (chart['cci'].shift(1) < chart['ccih']) &
        (chart['rsifast'] > chart['rsislow']), True, False)
    chart['sell'] = np.where(
        (chart['cci'] < chart['ccil']) &
        (chart['cci'].shift(1) > chart['ccil']) &
        (chart['rsifast'] < chart['rsislow']), True, False)

    simplifyorders(chart)

    all_chart = pd.concat([all_chart, chart])

    print(all_chart)
    pltchart(all_chart, all_trades, price='open')


if __name__ == "__main__":
    main()
