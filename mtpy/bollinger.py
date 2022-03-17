import logging
from datetime import datetime, timedelta, tzinfo
from pprint import pformat
import time
from typing import Tuple
from xmlrpc.client import boolean

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import pandas as pd
import pytz
from pandas.plotting import register_matplotlib_converters

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

    # set index
    ticks.index = pd.to_datetime(
        ticks['time_msc'], unit='ms', utc=True)
    ticks = ticks.drop(columns=['time', 'time_msc'])

    return status, ticks


def connect():
    logging.info('Connect to MetaTrader 5')
    if not mt5.initialize():
        logging.info("initialize() failed")
        mt5.shutdown()


def disconnect():
    logging.info('Disconnect from MetaTrader 5')
    mt5.shutdown()


def add_sma(ticks: pd.DataFrame, name: str, from_column: str, window: str):
    ticks[name] = ticks[from_column].rolling(window).mean()


def add_bollinger(ticks: pd.DataFrame, column_name: str, window: str, desviations: list[float] = [2, 2.5]):
    sma = 'bollinger_sma'
    std = 'bollinger_std'
    up1 = 'bollinger1_up'
    down1 = 'bollinger1_down'
    up2 = 'bollinger2_up'
    down2 = 'bollinger2_down'

    ticks[sma] = ticks[column_name].rolling(window).mean()
    ticks[std] = ticks[column_name].rolling(window).std()
    ticks[up1] = ticks[sma] + ticks[std] * desviations[0]
    ticks[down1] = ticks[sma] - ticks[std] * desviations[0]
    ticks[up2] = ticks[sma] + ticks[std] * desviations[1]
    ticks[down2] = ticks[sma] - ticks[std] * desviations[1]


def plotting_ticks(ticks: pd.DataFrame):
    logging.info('Plotting ticks')
    print(ticks)

    # display ticks on the chart
    fig = plt.figure()
    # plt.plot(ticks.index, ticks['last'], 'y-', label='Last')
    plt.plot(ticks.index, ticks['soft_sma'], 'y-', label='Soft SMA')
    plt.plot(ticks.index, ticks['fast_sma'], 'g--', label='Fast SMA')
    plt.plot(ticks.index, ticks['slow_sma'], 'r--', label='Slow SMA')

    if 'bollinger_sma' in ticks.columns:
        plt.plot(ticks.index, ticks['bollinger_sma'], label='SMA', c='g')
        plt.plot(ticks['bollinger1_up'], 'k--', label='Bollinger 1 Up')
        plt.plot(ticks['bollinger1_down'], 'k--', label='Bollinger 1 Down')
        plt.plot(ticks['bollinger2_up'], 'k--', label='Bollinger 2 Up')
        plt.plot(ticks['bollinger2_down'], 'k--', label='Bollinger 2 Down')

    plt.legend(loc='upper left')
    plt.title(f'Info')

    plt.show()
    plt.close(fig)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            # logging.FileHandler("debug.log"),
            logging.StreamHandler()
        ]
    )

    connect()

    symbol = 'WIN$'
    end_date = datetime(2022, 3, 17, 10, tzinfo=pytz.utc)
    # end_date = datetime.now().replace(tzinfo=pytz.utc)
    start_date = end_date - timedelta(minutes=30)

    status, ticks = get_ticks(symbol, start_date, end_date)

    if status != mt5.RES_S_OK:
        disconnect()
        quit()

    disconnect()

    add_sma(ticks, 'soft_sma', 'last', '5s')
    add_sma(ticks, 'fast_sma', 'last', '15s')
    add_sma(ticks, 'slow_sma', 'last', '30s')
    
    add_bollinger(ticks, 'last', '600s')

    plotting_ticks(ticks)


if __name__ == "__main__":
    main()
