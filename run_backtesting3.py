import logging
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import mplfinance as mpf
import pandas as pd
import pytz
from pandas.plotting import register_matplotlib_converters
from ta.volatility import AverageTrueRange, KeltnerChannel

from advisor.timeframesignal import Side
from backtesting.tradingsimulate import TradingSimulate
from mtpy.mt5_client import MT5Client
from run_backtesting import plt_balance

register_matplotlib_converters()


def plt_chart(data: pd.DataFrame, tradings: pd.DataFrame = None):
    # apdict = mpf.make_addplot(data[['kch', 'kcl']])
    mpf.plot(data, mav=(), type='renko', title='Data', style='classic', renko_params={'brick_size':1.})


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WDOJ22'
    start_hour = 9

    client = MT5Client()

    for day in reversed(range(1)):
        date = datetime.now() - timedelta(days=day)
        start_date = datetime(date.year, date.month,
                              date.day, start_hour, 5, tzinfo=pytz.utc)
        end_date = datetime(date.year, date.month,
                            date.day, 16, 20, tzinfo=pytz.utc)
        

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

        chart = ticks.resample('10s')['last'].ohlc()

        ikc = KeltnerChannel(
            chart['high'], chart['low'], chart['close'], window=10, fillna=True)

        chart['kch'] = ikc.keltner_channel_hband()
        chart['kcl'] = ikc.keltner_channel_lband()

        plt_chart(chart)

    plt.show()


if __name__ == "__main__":
    main()
