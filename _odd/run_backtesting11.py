import logging
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import pytz
import ta
from _odd.run_backtesting8 import sumprofit

from backtesting import pltbalance, pltchart
from backtesting.transaction import Transaction
from run_backtesting8 import simplifyorders
from strategy import Side
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

    client = MT5Client()

    for f in [120]:
        all_chart = pd.DataFrame()
        all_trades = pd.DataFrame()
        frame = f'{f}s'

        start_date = datetime(2022, 3, 29, 9, 0, tzinfo=pytz.utc)
        end_date = datetime(2022, 3, 30, 17, 20, tzinfo=pytz.utc)
        date = datetime(2022, 3, 30, 9, 0, tzinfo=pytz.utc)

        client.connect()

        status, ticks = client.get_ticks(
            symbol, start_date, end_date, mt5.COPY_TICKS_ALL)

        if status != mt5.RES_S_OK:
            client.disconnect()
            quit()

        client.disconnect()

        logging.info('Computing...')

        if len(ticks) == 0:
            continue

        chart = ticks.resample(frame)['last'].ohlc()
        chart.dropna(inplace=True)

        rsifast = ta.momentum.rsi(chart['close'], window=25)
        rsislow = ta.momentum.rsi(chart['close'], window=100)
        ema = ta.trend.ema_indicator(chart['close'], window=25)

        chart['rsifast'] = rsifast
        chart['rsislow'] = rsislow
        chart['ema'] = ema

        chart['buy'] = np.where(
            (chart['open'] > chart['ema'].shift(1)) &
            (chart['rsifast'].shift(1) > chart['rsislow'].shift(1)), True, False)
        
        chart['sell'] = np.where(
            (chart['open'] < chart['ema'].shift(1)) &
            (chart['rsifast'].shift(1) < chart['rsislow'].shift(1)), True, False)

        simplifyorders(chart)
        sumprofit(chart)
        
        all_chart = pd.concat([all_chart, chart])
        
        # trades = tradesexec(chart, slippage=0.01)
        # all_trades = pd.concat([all_trades, trades])
        # all_trades['balance'] = all_trades['pips'].cumsum()
        # pltbalance(all_trades)
        pltchart(all_chart, all_trades, price='open')


if __name__ == "__main__":
    main()
