import logging
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import mplfinance as mpf
import pandas as pd
import pytz
from pandas.plotting import register_matplotlib_converters

from backtesting.tradingsimulate import TradingSimulate
from run_backtesting1 import plt_balance
from strategy import Side
from strategy.mt5_client import MT5Client

register_matplotlib_converters()


class SmaSignal:
    def __init__(self):
        self.__state = []

    def apply(self, item: pd.Series) -> Side:
        self.__state.append(item.copy())

        if len(self.__state) < 2:
            return None

        previous = self.__state[-2]

        if previous['sma_1'] > previous['sma_2']:
            return Side.BUY
        
        if previous['sma_1'] < previous['sma_2']:
            return Side.SELL
        
        if len(self.__state) > 2:
            self.__state = self.__state[-2:]

        return None


def plt_chart(data: pd.DataFrame, trades: pd.DataFrame = None):
    alines = []
    for index, trade in trades.iterrows():
        open = (index, trade['entry_price'])
        close = (trade['exit_time'], trade['exit_price'])

        alines.append([open, close])

    addplot = mpf.make_addplot(data[['sma_1', 'sma_2']])

    mpf.plot(data, mav=(), type='candle', title='Data', style='classic',
             renko_params={'brick_size': 1.}, alines=dict(alines=alines, colors=['b', 'r', 'c', 'k', 'g']), addplot=addplot)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WINJ22'

    client = MT5Client()
    all_trades = pd.DataFrame()
    all_chart = pd.DataFrame()

    for day in reversed(range(1)):
        date = datetime.now() - timedelta(days=day)
        start_date = datetime(date.year, date.month,
                              date.day, 9, 0, tzinfo=pytz.utc)
        end_date = datetime(date.year, date.month,
                            date.day, 17, 55, tzinfo=pytz.utc)

        client.connect()

        status, ticks = client.get_ticks(
            symbol, start_date, end_date, mt5.COPY_TICKS_TRADE)

        if status != mt5.RES_S_OK:
            client.disconnect()
            quit()

        client.disconnect()

        logging.info('Computing...')

        if len(ticks) == 0:
            continue

        chart = ticks.resample('30s')['last'].ohlc()

        chart['sma_1'] = chart.rolling(5, min_periods=1)['close'].mean()
        chart['sma_2'] = chart.rolling(5, min_periods=1)['open'].mean()

        logging.info('Trading simulate...')
        simulate = TradingSimulate(sides=[Side.BUY], columns=('open', 'open'))
        simulate.compute(chart, SmaSignal().apply, (None, None, None))

        logging.info('Creating trading data frame...')
        trades = simulate.to_dataframe()

        all_trades = pd.concat([all_trades, trades])
        all_chart = pd.concat([all_chart, chart])

    all_trades['balance'] = all_trades['pips'].cumsum()
    all_trades.to_csv('backtesting-trades.csv', sep='\t')

    print(all_trades)
    plt_balance(all_trades)
    plt_chart(all_chart, all_trades)


if __name__ == "__main__":
    main()
