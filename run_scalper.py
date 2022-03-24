import logging
from datetime import datetime, timedelta
from time import sleep

import MetaTrader5 as mt5
from numpy import char
import pandas as pd
import pytz

from strategy import Side
from strategy.mt5_client import MT5Client


class SmaSignal:
    def __init__(self):
        self.__state = []

    def apply(self, item: pd.Series) -> Side:
        self.__state.append(item.copy())

        if len(self.__state) < 2:
            return None

        preivous = self.__state[-2]

        if preivous['sma_1'] > preivous['sma_2']:
            return Side.BUY

        if preivous['sma_1'] < preivous['sma_2']:
            return Side.SELL

        return None


class Loop:
    def __init__(self, client: MT5Client, offset: timedelta, sim_startdate: datetime = None):
        self.symbol = 'WINJ22'
        self.frame = '15s'

        self.client = client
        self.offset = offset
        self.sim_startdate = None
        self.signal = SmaSignal()
        self.odd_candle = None
        self.symbol_info = None
        self.lot = 1
        self.desviation = 20
        self.magic = 5544
        self.candle = None

        if not sim_startdate is None:
            if sim_startdate.tzinfo != pytz.utc:
                raise Exception(
                    'Invalid arg: sim_enddate, message: The time zone needs to be utc.')

            self.sim_startdate = sim_startdate

    def __check_symbol(self) -> bool:
        self.symbol_info = mt5.symbol_info(self.symbol)

        if self.symbol_info is None:
            logging.error(
                f'The {self.symbol} not found, can not call order_check()')
            return False

        if not self.symbol_info.visible:
            logging.info(
                f'The {self.symbol} is not visible, trying to switch on')

            if not mt5.symbol_select(self.symbol, True):
                logging.error(f'Symbol select failed')
                return False

        return True

    def __dates(self):
        end_date = datetime.now().replace(tzinfo=pytz.utc) + timedelta(seconds=10)

        if not self.sim_startdate is None:
            end_date = self.sim_startdate
            self.sim_startdate += timedelta(seconds=1)

        start_date = end_date - self.offset

        return start_date, end_date

    def __ticks(self):
        start_date, end_date = self.__dates()

        status, ticks = self.client.get_ticks(
            self.symbol, start_date, end_date, mt5.COPY_TICKS_ALL)

        if status != mt5.RES_S_OK:
            logging.warning('No data...')
            return None

        return ticks

    def __is_equal(self, a: pd.Series, b: pd.Series) -> bool:
        return a['open'] == b['open'] and a['high'] == b['high'] and a['low'] == b['low'] and a['close'] == b['close']

    def __orderinfo(self, result):
        result_dict = result._asdict()
        message = ''

        for field in result_dict.keys():
            message += '   {}={}\n'.format(field, result_dict[field])

            if field == "request":
                traderequest_dict = result_dict[field]._asdict()
                for tradereq_filed in traderequest_dict:
                    message += '       traderequest: {}={}\n'.format(
                        tradereq_filed, traderequest_dict[tradereq_filed])

        return message

    def __send_order(self, lot: float, side: Side, position: int = None):
        logging.info('Sending order...')

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY if Side.BUY else mt5.ORDER_TYPE_SELL,
            "price": self.symbol_info.ask if Side.BUY else self.symbol_info.bid,
            "deviation": self.desviation,
            "magic": self.magic,
            "comment": "strategy timeframe",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        if not position is None:
            request['position'] = position

        result = mt5.order_send(request)

        if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
            if not result:
                logging.error(
                    f'Order send failed, result is None')
            else:
                logging.error(
                    f'Order send failed, retcode={result.retcode}, detail\n{self.__orderinfo(result)}')

        return result

    def __compute_chart(self, ticks):
        chart = ticks.resample(self.frame)['last'].ohlc()
        chart['sma_1'] = chart.rolling(5, min_periods=1)['close'].mean()
        chart['sma_2'] = chart.rolling(5, min_periods=1)['open'].mean()
        chart['signal'] = chart.apply(self.signal.apply, axis=1)

        return chart

    def __is_newcandle(self, chart):
        if len(chart) < 1:
            logging.error('Chart size less than 2...')
            return False

        self.candle = chart.iloc[-1]

        if self.odd_candle is None:
            self.odd_candle = self.candle
            return False

        if self.__is_equal(self.candle, self.odd_candle):
            logging.info('Candle is equal...')
            return False

        return True

    def __trade(self):
        signal = self.candle['signal']

        _, positions = self.client.get_position(self.symbol)

        if positions.empty:
            if signal == Side.BUY:
                logging.info('Sending buy order...')
                self.__send_order(self.lot, Side.BUY)

            return

        logging.info('Has position...')

        position = positions[-1]

        if position['type'] == mt5.POSITION_TYPE_BUY and signal == Side.SELL:
            self.__send_order(position['volume'],
                              Side.SELL, position['ticket'])
        elif position['type'] == mt5.POSITION_TYPE_SELL and signal == Side.BUY:
            self.__send_order(position['volume'],
                              Side.BUY, position['ticket'])

    def exec(self):
        self.client.connect()

        logging.info('Checkin symbol...')
        if not self.__check_symbol():
            return

        logging.info('Get ticks...')
        ticks = self.__ticks()
        if ticks.empty:
            return

        logging.info('Computing chart...')
        chart = self.__compute_chart(ticks)

        logging.info('Checking new candle...')
        if not self.__is_newcandle(chart):
            return

        logging.info('Operating the market...')
        self.__trade()

        logging.info('Save last candle...')
        self.odd_candle = self.candle


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    offset = timedelta(minutes=15)
    sim_startdate = datetime(2022, 3, 23, 9, 40, tzinfo=pytz.utc)

    client = MT5Client()
    loop = Loop(client, offset=offset, sim_startdate=sim_startdate)

    while True:
        try:
            loop.exec()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logging.error(e)
            sleep(1)


if __name__ == "__main__":
    main()
