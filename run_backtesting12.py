import logging
from datetime import datetime

import numpy as np
import pandas as pd
import pytz

from backtesting import pltbalance, pltchart
from backtesting.data import Data
from backtesting.transaction import Transaction
from run_backtesting8 import simplifyorders
from ta.momentum import rsi
from ta.trend import cci

from strategy import Side


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


def tradesexec(chart: pd.DataFrame, slippage=0):
    trades = []
    histbar = []

    for i, bar in chart.iterrows():
        histbar.append(bar.copy())

        if len(histbar) < 3:
            continue
        else:
            histbar = histbar[-3:]

        lasttrade = trades[-1] if trades else None

        issell = bar['sell']
        isbuy = bar['buy']

        price = 'open'

        if lasttrade and lasttrade.is_open:
            if lasttrade.side == Side.BUY and issell:
                lasttrade.close(i, bar[price], slippage)
            elif lasttrade.side == Side.SELL and isbuy:
                lasttrade.close(i, bar[price], slippage)
            else:
                continue

        if isbuy:
            trades.append(Transaction(
                Side.BUY, i, bar[price], slippage))
            continue

        elif issell:
            trades.append(Transaction(
                Side.SELL, i, bar[price], slippage))
            continue

    lasttrade = trades[-1] if trades else None
    if lasttrade and lasttrade.is_open:
        lasttrade.close(chart.iloc[-1].name, chart.iloc[-1]['close'])

    return trades_todataframe(trades)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WIN$'

    start_date = datetime(2022, 3, 15, 9, 0, tzinfo=pytz.utc)
    end_date = datetime(2022, 4, 1, 18, 20, tzinfo=pytz.utc)

    ticks = Data.ticks(symbol, start_date, end_date)

    if len(ticks) == 0:
        logging.info('No data...')
        quit()

    logging.info('Computing...')

    chart = ticks.resample('5s')['last'].ohlc()
    chart.dropna(inplace=True)

    chart['rsifast'] = rsi(chart['close'], window=34).ewm(
        span=8, adjust=False, min_periods=0).mean()
    chart['rsislow'] = rsi(chart['close'], window=144).ewm(
        span=8, adjust=False, min_periods=0).mean()
    chart['cci'] = cci(
        chart['high'], chart['low'], chart['close'], window=89)

    chart['buy'] = np.where(
        (chart['cci'].shift(1) > 100), True, False)
    chart['sell'] = np.where(
        (chart['cci'].shift(1) < -100), True, False)

    simplifyorders(chart)

    trades = tradesexec(chart, 5)

    pltbalance(trades)
    pltchart(chart, trades, price='open')


if __name__ == "__main__":
    main()
