import datetime
import logging
from typing import Tuple

import MetaTrader5 as mt5
import pandas as pd


class MT5Client:
    def __init__(self):
        pass

    def get_ticks(
            self,
            symbol: str,
            start_date: datetime,
            end_date: datetime,
            ticks_info: int = mt5.COPY_TICKS_INFO
    ) -> Tuple[int, pd.DataFrame]:

        logging.info(f'Get ticks {symbol} - start {start_date} end {end_date}')
        mt5_ticks = mt5.copy_ticks_range(
            symbol, start_date, end_date, ticks_info)

        status, status_message = mt5.last_error()
        if not status == mt5.RES_S_OK:
            logging.error(
                f'Get ticks failed, error code = {(status, status_message)}')
            return status, None

        logging.info(f'Get ticks success... {(status, status_message, len(mt5_ticks))}')
        ticks = pd.DataFrame(mt5_ticks)
        ticks = ticks.loc[ticks['last'] > 0]

        # set index
        ticks.index = pd.to_datetime(
            ticks['time_msc'], unit='ms', utc=True)
        ticks = ticks.drop(columns=['time', 'time_msc'])

        return status, ticks

    def connect(self):
        logging.info('Connect to MetaTrader 5...')
        if not mt5.initialize():
            logging.info("initialize() failed")
            mt5.shutdown()

    def disconnect(self):
        logging.info('Disconnect from MetaTrader 5...')
        mt5.shutdown()


if __name__ == "__main__":
    quit()
