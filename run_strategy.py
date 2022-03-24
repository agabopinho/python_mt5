import logging
import math
import random
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


class Loop:
    def __init__(self, client: MT5Client, symbol: str, lot: float, frame: str, offset: timedelta, period: int, simulate: dict):
        self.symbol = symbol
        self.frame = frame

        self.client = client
        self.offset = offset
        self.period = period
        self.symbol_info = None
        self.lot = lot
        self.desviation = 20
        self.magic = 5544
        self.ticks = pd.DataFrame()
        self.bars = pd.DataFrame()
        self.previous_bar = pd.Series()
        self.simulate = simulate
        self.requests = pd.DataFrame()

        self.__sim_startdate = None

        if self.simulate['simulation']:
            if not self.simulate['startdate'] or type(self.simulate['startdate']) != datetime or self.simulate['startdate'].tzinfo != pytz.utc:
                raise Exception(
                    'Invalid arg: simulate startdate.')

            self.__sim_startdate = self.simulate['startdate']
            self.simulate['sendorders'] = False
        elif not 'sendorders' in self.simulate:
            self.simulate['sendorders'] = False

        if not 'online' in self.simulate:
            self.simulate['online'] = False

        if not 'step' in self.simulate:
            self.simulate['step'] = timedelta(seconds=1)

    def __loadsymbol(self) -> bool:
        self.symbol_info = mt5.symbol_info(self.symbol)

        if self.symbol_info is None:
            logging.error(
                f'Symbol not found: {self.symbol}')
            return False

        if not self.symbol_info.visible:
            logging.info(
                f'Symbol is not visible, trying to switch on: {self.symbol}')

            if not mt5.symbol_select(self.symbol, True):
                logging.error(f'Symbol select failed: {self.symbol}')
                return False

        return True

    def __dates(self):
        now = datetime.now().replace(tzinfo=pytz.utc)
        end_date = now

        if self.simulate['simulation']:
            end_date = self.__sim_startdate
            self.__sim_startdate += self.simulate['step']

            if self.__sim_startdate > now:
                self.__sim_startdate = now

        start_date = end_date - self.offset

        if not self.simulate['simulation']:
            end_date += timedelta(seconds=5)

        return start_date, end_date

    def __compute_bars(self):
        p = self.period
        bars = self.ticks.resample(self.frame)['last'].ohlc()
        bars['sma_1'] = bars.rolling(p, min_periods=1)['close'].mean()
        bars['sma_2'] = bars.rolling(p, min_periods=1)['open'].mean()
        bars['signal'] = bars.apply(SmaSignal().apply, axis=1)

        self.bars = bars

    def __loadticks(self) -> bool:
        start_date, end_date = self.__dates()

        status, ticks = self.client.get_ticks(
            self.symbol, start_date, end_date, mt5.COPY_TICKS_ALL)

        if status != mt5.RES_S_OK:
            logging.warning('No data...')
            return False

        self.ticks = ticks

        if not self.ticks.empty:
            logging.info('Computing chart...')
            self.__compute_bars()

        return not self.ticks.empty

    def __isnewbar(self):
        if len(self.bars) < 1:
            logging.error('Bars count less than 1...')
            return False

        current_bar = self.bars.iloc[-1]

        if self.previous_bar.empty:
            self.previous_bar = current_bar
            return False

        if current_bar.name == self.previous_bar.name:
            logging.info('Same bar...')
            return False

        self.previous_bar = current_bar

        return True

    def __orderdic(self, result):
        result_dict = result._asdict()

        for field in result_dict.keys():
            if field == "request":
                result_dict[field] = result_dict[field]._asdict()

        return result_dict

    def __appendrequest(self, request, request_date):
        self.requests = pd.concat(
            [self.requests, pd.DataFrame([request], columns=request.keys(), index=[request_date])])

    def __getprice(self, side: Side) -> float | None:
        if self.simulate['online']:
            if side == Side.BUY:
                return self.symbol_info.ask
            elif side == Side.SELL:
                return self.symbol_info.bid
            return None

        if side == Side.BUY:
            for _, p in self.ticks.iloc[::-1].iterrows():
                if p['ask']:
                    return p['ask']

        if side == Side.SELL:
            for _, p in self.ticks.iloc[::-1].iterrows():
                if p['bid']:
                    return p['bid']

        return None

    def __sendorder(self, lot: float, side: Side, position: int = None) -> dict[any, any]:
        price = self.__getprice(side)

        if not price:
            logging.error('Price was not recovered.')
            return {
                'retcode': mt5.TRADE_RETCODE_ERROR
            }

        request_date = datetime.now().replace(tzinfo=pytz.utc)

        if not self.simulate['online']:
            request_date = self.bars.iloc[-1].name

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY if side == Side.BUY else mt5.ORDER_TYPE_SELL,
            "price": price,
            "deviation": self.desviation,
            "magic": self.magic,
            "comment": "strategy timeframe",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        if position:
            request['position'] = position

        if not self.simulate['sendorders']:
            logging.info(f'Sim order send, {request}')

            self.__appendrequest(request, request_date)

            return {
                'retcode': mt5.TRADE_RETCODE_DONE
            }

        result = mt5.order_send(request)

        if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
            if not result:
                logging.error(
                    f'Order send failed, there was no result.')
            else:
                logging.error(
                    f'Order send failed, {self.__orderdic(result)}')

        self.__appendrequest(request, request_date)

        return self.__orderdic(result)

    def __simposition(self):
        if self.requests.empty:
            return pd.DataFrame()
        last_request = self.requests.iloc[-1]
        if 'position' in last_request.keys() and not math.isnan(last_request['position']):
            return pd.DataFrame()

        simpositions = pd.DataFrame(
            [last_request], columns=self.requests.columns, index=[last_request.name])
        simpositions['ticket'] = [random.randint(1, 100000000)]
        return simpositions

    def __dotrade(self):
        signal = self.bars.iloc[-1]['signal']

        status, positions = self.client.get_position(self.symbol)

        if status != mt5.RES_S_OK:
            logging.error('Cannot trade, error when searching for position.')
            return

        if not self.simulate['sendorders']:
            logging.info('Simulating positions...')
            positions = self.__simposition()

        if positions.empty:
            if signal == Side.BUY:
                logging.info('Sending buy order...')
                self.__sendorder(self.lot, Side.BUY)
            else:
                logging.info('Ignore sell signal...')

            return

        position = positions.iloc[-1]

        if position['type'] == mt5.POSITION_TYPE_BUY and signal == Side.SELL:
            logging.info('Sending close buy order...')
            self.__sendorder(position['volume'],
                             Side.SELL, position['ticket'])
        else:
            logging.info('Staying in position...')

    def exec(self):
        self.client.connect()

        logging.info('Loading symbol...')
        if not self.__loadsymbol():
            return

        logging.info('Loading ticks...')
        if not self.__loadticks():
            return

        logging.info('Checking bar...')
        if not self.__isnewbar():
            return

        logging.info('Operating the market...')
        self.__dotrade()

        if not self.simulate['sendorders']:
            logging.info('Generating trades file...')
            self.requests.to_csv('simulation-trades.csv', sep='\t')


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    # startdate = datetime(2022, 3, 24, 9, 0, tzinfo=pytz.utc)
    startdate = datetime.now().replace(tzinfo=pytz.utc)

    client = MT5Client()
    loop = Loop(client,
                symbol='WINJ22',
                lot=1,
                frame='30s',
                offset=timedelta(seconds=180),
                period=5,
                simulate=dict(simulation=True, startdate=startdate, step=timedelta(seconds=1), sendorders=False, online=True))

    while True:
        try:
            logging.info('Running loop...')
            loop.exec()
            sleep(1/4)
            logging.info('Loop executed...')
        except KeyboardInterrupt:
            logging.error('Requested stop', exc_info=True)
            quit()
        except Exception:
            logging.error('Unknown error', exc_info=True)
            sleep(1)


if __name__ == "__main__":
    main()
