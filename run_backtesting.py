import logging
import time
from datetime import datetime, timedelta
from pprint import pformat
from typing import Tuple

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import mplfinance as mpf
import pandas as pd
import pytz
from pandas.plotting import register_matplotlib_converters
from pyparsing import any_open_tag, col

from advisor.timeframesignal import TimeFrameSignal
from backtesting.tradingsimulate import Side, TradingSimulate
from mtpy.mt5_client import MT5Client

register_matplotlib_converters()


def plt_ticks(ticks: pd.DataFrame, tradings: pd.DataFrame = None, plot_price: bool = False):
    logging.info('Plotting ticks')

    fig = plt.figure()

    if plot_price:
        plt.plot(ticks.index, ticks['ask'], 'r--', label='Ask')
        plt.plot(ticks.index, ticks['bid'], 'b--', label='bid')

    if not tradings is None:
        for index, row in tradings.loc[tradings['is_open'] == False].iterrows():
            point1 = [index, row['entry_price']]
            point2 = [row['exit_time'], row['exit_price']]
            x_values = [point1[0], point2[0]]
            y_values = [point1[1], point2[1]]

            if row['pips'] > 0:
                plt.plot(x_values, y_values, 'go', linestyle="--")
            else:
                plt.plot(x_values, y_values, 'ro', linestyle="--")

    plt.legend(loc='upper left')
    plt.title(f'Info')

    plt.show()
    plt.close(fig)


def plt_balance(trades: pd.DataFrame):
    logging.info('Plotting balance')
    print(trades)

    fig = plt.figure()
    plt.plot(trades.index, trades['balance'], 'y-', label='Balance')

    plt.legend(loc='upper left')
    plt.title(f'Info')

    plt.show()
    plt.close(fig)


def plt_candle(symbol: str, timeframe: pd.DataFrame):
    mpf.plot(timeframe, type='candle', title=symbol, style='yahoo')


def plt_timeframe(timeframe: pd.DataFrame, tradings: pd.DataFrame = None):
    fig = plt.figure()

    plt.plot(timeframe.index, timeframe['open'], 'k--', label='Open')
    plt.plot(timeframe.index,
             timeframe['sma_fast'], 'b--', label='SMA Fast (Open)')
    plt.plot(timeframe.index,
             timeframe['sma_slow'], 'c--', label='SMA Slow (Open)')

    if not tradings is None:
        for index, row in tradings.loc[tradings['is_open'] == False].iterrows():
            point1 = [index, row['entry_price']]
            point2 = [row['exit_time'], row['exit_price']]
            x_values = [point1[0], point2[0]]
            y_values = [point1[1], point2[1]]

            if row['side'] == Side.BUY:
                plt.plot(x_values, y_values, 'go', linestyle="--")
            else:
                plt.plot(x_values, y_values, 'ro', linestyle="--")

    plt.legend(loc='upper left')
    plt.show()


def set_price(timeframe: pd.DataFrame, ticks: pd.DataFrame, period_seconds: int):
    open_time = []
    open_bid = []
    open_ask = []

    last_frametick = None

    for index, _ in timeframe.iterrows():
        from_date = index
        to_date = index + timedelta(seconds=period_seconds)

        frame_ticks = ticks.loc[(ticks.index >= from_date)
                                & (ticks.index < to_date)]

        first_tick = None
        if len(frame_ticks) > 0:
            first_tick = frame_ticks.iloc[0]

        timeframe_tick = None
        if not first_tick is None and first_tick.name - from_date <= timedelta(seconds=1):
            timeframe_tick = first_tick
        elif not last_frametick is None:
            timeframe_tick = last_frametick

        if not timeframe_tick is None:
            open_time.append(timeframe_tick.name)
            open_bid.append(timeframe_tick['bid'])
            open_ask.append(timeframe_tick['ask'])
        else:
            open_time.append(from_date)
            open_bid.append(0)
            open_ask.append(0)

        if len(frame_ticks) > 0:
            last_frametick = frame_ticks.iloc[-1]

    timeframe['time_price'] = open_time
    timeframe['open_bid'] = open_bid
    timeframe['open_ask'] = open_ask


def simulate(client: MT5Client,
             symbol: str,
             start_date: datetime,
             end_date: datetime,
             take_stop: tuple[float, float],
             period_seconds: int,
             fast: any,
             slow: any,
             inverse: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    client.connect()
    status, ticks = client.get_ticks(symbol, start_date, end_date)

    if status != mt5.RES_S_OK:
        client.disconnect()
        quit()

    client.disconnect()

    logging.info('Computing...')

    if len(ticks) == 0:
        return None, None, None

    timeframe = ticks.resample(f'{period_seconds}s')['last'].ohlc()
    timeframe['sma_fast'] = timeframe.rolling(
        fast, min_periods=1)['open'].mean()
    timeframe['sma_slow'] = timeframe.rolling(
        slow, min_periods=1)['open'].mean()

    set_price(timeframe, ticks, period_seconds)

    signal = TimeFrameSignal(inverse)

    logging.info('Trading simulate...')
    simulate = TradingSimulate(columns=('open_bid', 'open_ask'))
    simulate.compute(timeframe, signal.apply, take_stop)

    logging.info('Creating trading data frame...')
    tradings = simulate.to_dataframe()

    return ticks, timeframe, tradings


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    client = MT5Client()
    for symbol in ['ITSA4']:
        all_tradings = None
        all_timeframe = None

        for day in reversed(range(60)):
            date = datetime.now() - timedelta(days=day)
            end_date = datetime(date.year, date.month,
                                date.day, 16, 20, tzinfo=pytz.utc)
            start_date = datetime(date.year, date.month,
                                  date.day, 10, 10, tzinfo=pytz.utc)

            _, timeframe, tradings = simulate(
                client, symbol, start_date, end_date,
                (None, None), period_seconds=600, fast=1, slow=10, inverse=False)

            if tradings is None:
                continue

            if all_tradings is None:
                all_tradings = tradings
            else:
                all_tradings = pd.concat([all_tradings, tradings])

            if all_timeframe is None:
                all_timeframe = timeframe

            else:
                all_timeframe = pd.concat([all_timeframe, timeframe])

        all_tradings['balance'] = all_tradings['pips'].cumsum()

        plt_balance(all_tradings)
        plt_timeframe(all_timeframe, all_tradings)


if __name__ == "__main__":
    main()
