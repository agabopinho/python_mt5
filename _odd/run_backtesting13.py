import logging
from datetime import datetime

import numpy as np
import pandas as pd
import pytz

from backtesting import pltbalance, pltchart
from backtesting.data import Data
from backtesting.transaction import Transaction

from strategy import Side


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


def tradesexec(ticks: pd.DataFrame, chart: pd.DataFrame, slippage=0):
    trades = []
    histbar = []
    histamount = 100
    
    buyprice = 0
    sellprice = 0

    for i, bar in chart.iterrows():
        histbar.append(bar.copy())
        histbar = histbar[-histamount:]

        lasttrade = trades[-1] if trades else None
        
        if lasttrade and lasttrade.is_open: 
            pass
        
        buyprice = bar['high'] + 5
        sellprice = bar['low'] + 5
        
        if len(histbar) == 1: 
            continue

    closelasttrade(chart, trades)

    return tradestodataframe(trades)


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

    start_date = datetime(2022, 4, 1, 9, 0, tzinfo=pytz.utc)
    end_date = datetime(2022, 4, 1, 18, 20, tzinfo=pytz.utc)

    ticks = Data.ticks(symbol, start_date, end_date)

    if len(ticks) == 0:
        logging.info('No data...')
        quit()

    logging.info('Computing...')

    chart = ticks.resample('30s')['last'].ohlc()
    chart.dropna(inplace=True)

    trades = tradesexec(ticks, chart, 5)

    # pltbalance(trades)
    pltchart(chart, trades, price='open')


if __name__ == "__main__":
    main()
