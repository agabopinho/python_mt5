import logging
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import pandas as pd
import pytz
from pandas.plotting import register_matplotlib_converters
from ta.volatility import AverageTrueRange, KeltnerChannel

from advisor.timeframesignal import Side
from backtesting.tradingsimulate import TradingSimulate
from strategy.mt5_client import MT5Client
from run_backtesting1 import plt_balance

register_matplotlib_converters()


class SmaSignal:
    def __init__(self):
        pass

    def apply(self, item: pd.Series) -> Side:
        sma_count = int(item['sma_count'])

        if not sma_count > 0:
            return None

        buy_signal = True
        for i in range(sma_count - 1):
            if not item[f'sma_{i}'] > item[f'sma_{i + 1}']:
                buy_signal = False
                break

        if buy_signal:
            return Side.BUY

        sell_signal = True
        for i in range(sma_count - 1):
            if not item[f'sma_{i}'] < item[f'sma_{i + 1}']:
                sell_signal = False
                break

        if sell_signal:
            return Side.SELL

        return None


class KcSignal:
    def __init__(self):
        pass

    def apply(self, item: pd.Series) -> Side:
        sma_count = int(item['sma_count'])

        if not sma_count > 0:
            return None

        buy_signal = True
        for i in range(sma_count - 1):
            if not item[f'sma_{i}'] > item[f'sma_{i + 1}']:
                buy_signal = False
                break

        if buy_signal:
            return Side.BUY

        sell_signal = True
        for i in range(sma_count - 1):
            if not item[f'sma_{i}'] < item[f'sma_{i + 1}']:
                sell_signal = False
                break

        if sell_signal:
            return Side.SELL

        return None


def plt_chart(ticks: pd.DataFrame, tradings: pd.DataFrame = None):
    fig = plt.figure()

    plt.plot(ticks.index, ticks['last'], 'k--', label='Last')

    # sma_count = ticks.iloc[0]['sma_count']
    # for i in range(sma_count):
    #     plt.plot(ticks.index, ticks[f'sma_{i}'], 'c--', label=f'SMA {i}')

    plt.plot(ticks.index, ticks[f'kch'], 'c--', label=f'KCH')
    plt.plot(ticks.index, ticks[f'kcl'], 'c--', label=f'KCL')

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
    plt.title('Chart')


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WDOJ22'
    take_stop = (50, 60)
    start_hour = 9
    smas = [5, 10, 20, 40, 80, 160, 320]
    smas = []

    client = MT5Client()
    all_trades = pd.DataFrame()

    for day in reversed(range(1)):
        date = datetime.now() - timedelta(days=day)
        start_date = datetime(date.year, date.month,
                              date.day, start_hour, 5, tzinfo=pytz.utc)
        end_date = datetime(date.year, date.month,
                            date.day, 16, 20, tzinfo=pytz.utc)

        client.connect()
        status, ticks = client.get_ticks(symbol, start_date, end_date, mt5.COPY_TICKS_ALL)

        if status != mt5.RES_S_OK:
            client.disconnect()
            quit()

        client.disconnect()

        logging.info('Computing...')

        if len(ticks) == 0:
            continue

        rolling = ticks.rolling('60s', min_periods=1)
        ikc = KeltnerChannel(rolling['last'].max(), rolling['last'].min(), rolling['last'].agg(lambda r: r[-1]),
                             window=30, original_version=True, fillna=True)
        iatr = AverageTrueRange(
            ticks['ask'], ticks["bid"], ticks["last"], window=600, fillna=True)

        ticks['kch'] = ikc.keltner_channel_hband()
        ticks['kcl'] = ikc.keltner_channel_lband()
        ticks['atr'] = iatr.average_true_range()
        
        index = 0
        for sma in smas:
            ticks[f'sma_{index}'] = ticks.rolling(
                f'{sma}s', min_periods=1)['last'].mean()
            index += 1

        ticks['sma_count'] = len(smas)

        signal = SmaSignal()

        logging.info('Trading simulate...')
        simulate = TradingSimulate()
        simulate.compute(ticks, signal.apply, take_stop)

        logging.info('Creating trading data frame...')
        trades = simulate.to_dataframe()

        print(trades)
        all_trades = pd.concat([all_trades, trades])

        plt_chart(ticks, trades)

    all_trades['balance'] = all_trades['pips'].cumsum()

    plt_balance(all_trades)
    plt.show()


if __name__ == "__main__":
    main()
