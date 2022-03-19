import logging
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

from timeframesignal import TimeFrameSignal
from tradingsimulate import TradingSimulate, Side

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
        logging.info("Get ticks failed, error code =",
                     (status, status_message))
        status, None

    logging.info('Get ticks success...')
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


def simulate_day(symbol: str, day: int):
    # end_date = datetime.now().replace(tzinfo=pytz.utc)
    end_date = datetime(2022, 3, day, 17, 00, tzinfo=pytz.utc)
    start_date = datetime(2022, 3, day, 9, 10, tzinfo=pytz.utc)

    connect()

    status, ticks = get_ticks(symbol, start_date, end_date)

    if status != mt5.RES_S_OK:
        disconnect()
        quit()

    disconnect()

    logging.info('Computing...')

    timeframe = ticks.resample('10s')['last'].ohlc()
    timeframe['sma_fast'] = timeframe.rolling(5)['open'].mean()
    timeframe['sma_slow'] = timeframe.rolling(30)['open'].mean()

    print(timeframe)

    signal = TimeFrameSignal(timeframe, ticks)

    logging.info('Trading simulate...')
    simulate = TradingSimulate(columns=('open', 'open'))
    simulate.compute(timeframe, signal.signal, (None, 50))

    logging.info('Creating trading data frame...')
    tradings = simulate.to_dataframe()

    plt_balance(tradings)
    # plt_timeframe(timeframe, tradings)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WIN$'

    for day in [7, 8, 9, 10, 11, 14, 15, 16, 17, 18]:
        # for day in [14, 15, 16, 17, 18]:
        # for day in [7, 8, 9, 10, 11]:
        simulate_day(symbol, day)


if __name__ == "__main__":
    main()
