import logging
import time
from datetime import datetime, timedelta
from typing import Tuple

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import pandas as pd
import pytz
from pandas.plotting import register_matplotlib_converters

from trading_sim import Side, TradingSim

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
    
    print(ticks)

    return status, ticks


def connect():
    logging.info('Connect to MetaTrader 5...')
    if not mt5.initialize():
        logging.info("initialize() failed")
        mt5.shutdown()


def disconnect():
    logging.info('Disconnect from MetaTrader 5...')
    mt5.shutdown()


def add_sma(ticks: pd.DataFrame, name: str, from_column: str, window: str):
    ticks[name] = ticks[from_column].rolling(window).mean()


def add_bollinger(ticks: pd.DataFrame, column_name: str, window: str, desviations: tuple[float, float] = (2, 2.5)):
    sma = 'bollinger_sma'
    std = 'bollinger_std'
    up1 = 'bollinger1_up'
    down1 = 'bollinger1_down'
    up2 = 'bollinger2_up'
    down2 = 'bollinger2_down'

    desviation1, desviations2 = desviations

    ticks[sma] = ticks[column_name].rolling(window).mean()
    ticks[std] = ticks[column_name].rolling(window).std()
    ticks[up1] = ticks[sma] + ticks[std] * desviation1
    ticks[down1] = ticks[sma] - ticks[std] * desviation1
    ticks[up2] = ticks[sma] + ticks[std] * desviations2
    ticks[down2] = ticks[sma] - ticks[std] * desviations2


def plotting_ticks(ticks: pd.DataFrame, tradings: pd.DataFrame = None, plot_price: bool = False):
    logging.info('Plotting ticks')

    fig = plt.figure()

    if plot_price:
        plt.plot(ticks.index, ticks['ask'], 'r--', label='Ask')
        plt.plot(ticks.index, ticks['bid'], 'b--', label='bid')

    if 'bid_mean' in ticks.columns:
        plt.plot(ticks.index, ticks['bid_mean'], 'r:', label='Bid Mean')

    if 'ask_mean' in ticks.columns:
        plt.plot(ticks.index, ticks['ask_mean'], 'b:', label='Ask Mean')
        
    if 'soft_sma' in ticks.columns:
        plt.plot(ticks.index, ticks['soft_sma'], 'k--', label='Soft SMA')

    if 'fast_sma' in ticks.columns:
        plt.plot(ticks.index, ticks['fast_sma'], 'm--', label='Fast SMA')

    if 'slow_sma' in ticks.columns:
        plt.plot(ticks.index, ticks['slow_sma'], 'c--', label='Slow SMA')

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

            # plt.text(point1[0]+timedelta(seconds=5), point1[1],
            #          'BUY' if row['side'] == Side.BUY else 'SELL')

    if 'bollinger_sma' in ticks.columns:
        plt.plot(ticks.index, ticks['bollinger_sma'], label='SMA', c='g')
        plt.plot(ticks['bollinger1_up'], 'k:', label='Bollinger 1 Up')
        plt.plot(ticks['bollinger1_down'], 'k:', label='Bollinger 1 Down')
        plt.plot(ticks['bollinger2_up'], 'k:', label='Bollinger 2 Up')
        plt.plot(ticks['bollinger2_down'], 'k:', label='Bollinger 2 Down')

    plt.legend(loc='upper left')
    plt.title(f'Info')

    plt.show()
    plt.close(fig)


def plotting_balance(tradings: pd.DataFrame):
    logging.info('Plotting balance')
    print(tradings)

    fig = plt.figure()
    plt.plot(tradings.index, tradings['balance'], 'y-', label='Balance')

    plt.legend(loc='upper left')
    plt.title(f'Info')

    plt.show()
    plt.close(fig)


def sma_signal(row: pd.Series, invert: bool = False) -> Side:
    if row['soft_sma'] >= row['fast_sma']:
        return Side.BUY
    elif row['soft_sma'] <= row['fast_sma']:
        return Side.SELL
    return None


def sim_day(symbol: str, day: int):
    end_date = datetime(2022, 3, day, 11, 50, tzinfo=pytz.utc)
    # end_date = datetime.now().replace(tzinfo=pytz.utc)
    # start_date = end_date - timedelta(hours=2, minutes=30)
    start_date = datetime(2022, 3, day, 10, 10, tzinfo=pytz.utc)

    connect()

    status, ticks = get_ticks(symbol, start_date, end_date)

    if status != mt5.RES_S_OK:
        disconnect()
        quit()

    disconnect()

    logging.info('Computing SMA...')
    add_sma(ticks, 'bid_mean', 'bid', '30s')
    add_sma(ticks, 'ask_mean', 'ask', '30s')

    # logging.info('Trading simulation...')
    # trading_sim = TradingSim()
    # trading_sim.sim(ticks, sma_signal, (None, 150))

    # logging.info('Creating trading data frame...')
    # tradings = trading_sim.to_dataframe()

    plotting_ticks(ticks, None, plot_price=True)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            # logging.FileHandler("debug.log"),
            logging.StreamHandler()
        ]
    )

    symbol = 'PETR4'

    for day in [18]:
        # for day in [14, 15, 16, 17, 18]:
        # for day in [7, 8, 9, 10, 11]:
        sim_day(symbol, day)


if __name__ == "__main__":
    main()
