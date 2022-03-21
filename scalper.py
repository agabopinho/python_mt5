import logging
from datetime import datetime, timedelta
from time import sleep
from typing import Tuple

import MetaTrader5 as mt5
import pandas as pd
import pytz

from mtpy.mt5_client import MT5Client
from advisor.timeframesignal import TimeFrameSignal


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
