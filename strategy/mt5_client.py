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
        logging.info(
            f'Get ticks {dict(symbol=symbol, start=start_date, end=end_date)}')

        mt5ticks = mt5.copy_ticks_range(
            symbol, start_date, end_date, ticks_info)
        status, status_message = mt5.last_error()

        if not status == mt5.RES_S_OK:
            logging.error(
                f'Get ticks failed, error code = {dict(status=status, message=status_message)}')
            return status, pd.DataFrame()

        logging.info(
            f'Get ticks success... {dict(status=status, message=status_message, tickslen=len(mt5ticks))}')
        ticks = pd.DataFrame(mt5ticks)
        ticks = ticks.loc[ticks['last'] > 0]

        # set index
        ticks.index = pd.to_datetime(
            ticks['time_msc'], unit='ms', utc=True)

        ticks.drop(columns=['time', 'time_msc'], inplace=True)

        return status, ticks

    def get_position(self, symbol: str) -> tuple[int, pd.DataFrame]:
        logging.info(f'Get positions {dict(symbol=symbol)}')

        mt5positions = mt5.positions_get(symbol=symbol)
        status, status_message = mt5.last_error()

        if status != mt5.RES_S_OK:
            logging.error(
                f'Get positions failed, error code = {dict(status=status, message=status_message)}')
            return status, pd.DataFrame()

        logging.info(
            f'Get positions success... {dict(positionlen=len(mt5positions))}')

        if mt5positions:
            columns = mt5positions[0]._asdict().keys()

            positions = pd.DataFrame(list(mt5positions), columns=columns)

            positions.index = pd.to_datetime(
                positions['time_msc'], unit='ms', utc=True)
            positions['time_update_msc'] = pd.to_datetime(
                positions['time_update_msc'], unit='ms', utc=True)

            positions.drop(columns=['time', 'time_msc', 'time_update'], inplace=True)

            return status, positions

        return status, pd.DataFrame()

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
