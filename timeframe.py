import logging
from pprint import pformat
import time
from datetime import datetime, timedelta
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

register_matplotlib_converters()


def get_ticks(
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        ticks_info: int = mt5.COPY_TICKS_INFO) -> Tuple[int, pd.DataFrame]:

    logging.info(f'Get ticks {symbol} - start {start_date} end {end_date}')
    mt5_ticks = mt5.copy_ticks_range(
        symbol, start_date, end_date, ticks_info)

    status, status_message = mt5.last_error()
    if not status == mt5.RES_S_OK:
        logging.error(
            f'Get ticks failed, error code = {(status, status_message)}')
        return status, None

    logging.info(f'Get ticks success... {(status, status_message)}')
    ticks = pd.DataFrame(mt5_ticks)
    ticks = ticks.loc[ticks['last'] > 0]

    ticks['mid'] = (ticks['bid'] + ticks['ask']) / 2

    # set index
    ticks.index = pd.to_datetime(
        ticks['time_msc'], unit='ms', utc=True)
    ticks = ticks.drop(columns=['time', 'time_msc'])

    return status, ticks


def connect():
    logging.info('Connect to MetaTrader 5...')
    if not mt5.initialize():
        logging.info("initialize() failed")
        mt5.shutdown()


def disconnect():
    logging.info('Disconnect from MetaTrader 5...')
    mt5.shutdown()


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


def plt_balance(tradings: pd.DataFrame):
    logging.info('Plotting balance')
    print(tradings)

    fig = plt.figure()
    plt.plot(tradings.index, tradings['balance'], 'y-', label='Balance')

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


def simulate(symbol: str,
             start_date: datetime,
             end_date: datetime,
             take_stop: tuple[float, float],
             period: any,
             fast: any,
             slow: any,
             inverse: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    connect()

    status, ticks = get_ticks(symbol, start_date, end_date)

    if status != mt5.RES_S_OK:
        disconnect()
        quit()

    disconnect()

    logging.info('Computing...')

    if len(ticks) == 0:
        return None, None, None

    timeframe = ticks.resample(period)['last'].ohlc()
    timeframe['sma_fast'] = timeframe.rolling(fast)['open'].mean()
    timeframe['sma_slow'] = timeframe.rolling(slow)['open'].mean()

    signal = TimeFrameSignal(inverse)

    logging.info('Trading simulate...')
    simulate = TradingSimulate(columns=('open', 'open'))
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

    # ['RENT3', 'USIM5', 'B3SA3', 'ECOR3', 'BBAS3', 'GOAU4', 'ITSA4', 'BBDC4', 'CYRE3', 'ECOR3']:
    # ['RENT3', 'ITSA4', 'BBDC4', 'CYRE3', 'ECOR3']:
    # ITSA4 -> melhor performance period='60s', fast='300s', slow='600s', inverse=True

    for symbol in ['RENT3', 'ITSA4']:
        all_tradings = None
        all_timeframe = None

        for day in reversed(range(30)):
            date = datetime.now() - timedelta(days=day)
            end_date = datetime(date.year, date.month,
                                date.day, 16, 0, tzinfo=pytz.utc)
            start_date = datetime(date.year, date.month,
                                  date.day, 10, 10, tzinfo=pytz.utc)

            _, timeframe, tradings = simulate(
                symbol, start_date, end_date, (None, .02), period='60s', fast='300s', slow='600s', inverse=True)

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

        all_tradings.to_csv('trades.csv', sep='\t')

        plt_balance(all_tradings)
        plt_timeframe(all_timeframe, all_tradings)


if __name__ == "__main__":
    main()
