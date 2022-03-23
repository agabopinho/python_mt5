import logging
from datetime import datetime, timedelta
from time import sleep

import MetaTrader5 as mt5
import pandas as pd
import pytz

from strategy import Side
from strategy.mt5_client import MT5Client


class SmaSignal:
    def __init__(self):
        self.__state = []

    def apply(self, item: pd.Series) -> Side:
        self.__state.append(item.copy())

        if len(self.__state) < 3:
            return None

        preivous = self.__state[-2]

        if preivous['sma_1'] > preivous['sma_2'] and self.__state[-3]['sma_1'] < self.__state[-3]['sma_2']:
            return Side.BUY

        if preivous['sma_1'] < preivous['sma_2'] and self.__state[-3]['sma_1'] > self.__state[-3]['sma_2']:
            return Side.SELL

        return None


class Loop:
    def __init__(self, client: MT5Client, is_debug: bool = False):
        self.client = client
        self.is_debug = is_debug
        self.__end_date = None

    def __get_end_date(self) -> datetime:
        if not self.is_debug:
            return datetime.now().replace(tzinfo=pytz.utc)

        if not self.__end_date:
            self.__end_date = datetime(
                2022, 3, 18, 10, 13, second=1, tzinfo=pytz.utc)
        else:
            self.__end_date = self.__end_date + timedelta(seconds=10)

        return self.__end_date

    def exec(self):
        self.client.connect()

        symbol = 'ITSA4'
        frame = '60s'
        sma_fast = '300s'
        sma_slow = '600s'

        end_date = self.__get_end_date()
        start_date = end_date - timedelta(minutes=15)

        status, ticks = self.client.get_ticks(symbol, start_date, end_date)
        if status != mt5.RES_S_OK:
            logging.warning('No data')
            return

        ohlc = ticks.resample(frame)['last'].ohlc()
        ohlc['sma_fast'] = ohlc.rolling(sma_fast)['open'].mean()
        ohlc['sma_slow'] = ohlc.rolling(sma_slow)['open'].mean()

        signal = TimeFrameSignal(inverse=True)

        ohlc['signal'] = ohlc.apply(signal.apply, axis=1)
        signal = ohlc.iloc[-1:]['signal']

        logging.info(signal)
        sleep(1/10)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    client = MT5Client()
    loop = Loop(client, is_debug=True)
    while True:
        loop.exec()


if __name__ == "__main__":
    main()
