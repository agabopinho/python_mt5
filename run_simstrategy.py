import logging
import math
import os
import random
from datetime import datetime, timedelta
from time import sleep
from typing import Callable, Tuple

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import pytz
from ta.momentum import rsi
from ta.trend import cci

from strategy import Side
from strategy.mt5_client import MT5Client


class Loop:
    def __init__(self, client: MT5Client, symbol: str, lot: float, offset: timedelta, simulate: dict, computebars: Callable[[any], None]):
        self.client = client
        self.symbol = symbol
        self.lot = lot
        self.offset = offset
        self.simulate = simulate
        self.computebars = computebars

        self.symbol_info = None
        self.desviation = 30
        self.magic = 5544
        self.ticks = pd.DataFrame()
        self.tickscache = pd.DataFrame()
        self.bars = pd.DataFrame()
        self.requests = pd.DataFrame()

        self._startdate = None
        self.__current = pd.Series()
        self.__targethigh = float(0)
        self.__targetlow = float(0)

        if type(self.simulate) != dict:
            raise Exception('Invalid arg: simulate.')

        if not 'startdate' in self.simulate or type(self.simulate['startdate']) != datetime or self.simulate['startdate'].tzinfo != pytz.utc:
            raise Exception('Invalid arg: simulate.startdate.')

        self._startdate = self.simulate['startdate']

        if not 'step' in self.simulate:
            self.simulate['step'] = timedelta(seconds=1)

        self.client.connect()
        logging.info('Loading symbol...')
        if not self._loadsymbol():
            raise Exception('Symbol not loaded.')
        self._loadallday()
        self.client.disconnect()

    def _requeststocsv(self):
        requests = self.requests.copy()
        profits = []
        p = pd.Series(dtype=object)

        for _, r in requests.iterrows():
            if p.empty:
                p = r
                profits.append(0)
                continue

            if p['type'] == Side.BUY:
                profits.append(r['price'] - p['price'])
            elif p['type'] == Side.SELL:
                profits.append(p['price'] - r['price'])

            p = r

        if len(profits) < len(requests):
            if p['type'] == Side.BUY:
                profits.append(self.bars.iloc[-1]['close'] - p['price'])
            elif p['type'] == Side.SELL:
                profits.append(p['price'] - self.bars.iloc[-1]['close'])

        requests['profit'] = profits
        requests['cumsum_profit'] = requests['profit'].cumsum()

        if not requests.empty:
            requests.to_csv('simulation-trades.csv', sep='\t')

    def _loadsymbol(self) -> bool:
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

    def _dates(self) -> Tuple[datetime, datetime]:
        end_date = self._startdate
        start_date = end_date - self.offset

        return start_date, end_date

    def _slidestartdate(self):
        self._startdate += self.simulate['step']
        now = datetime.now().replace(tzinfo=pytz.utc)
        if self._startdate > now:
            self._startdate = now
        logging.info(f'Now is {self._startdate}')

    def _loadticks(self) -> bool:
        startdate, enddate = self._dates()
        self.ticks = self.tickscache[startdate:enddate]
        return not self.ticks.empty

    def _loadallday(self) -> bool:
        startdate = self._startdate.replace(
            hour=0, minute=0, second=0, microsecond=0)
        enddate = startdate + timedelta(days=1)

        status, ticks = self.client.get_ticks(
            self.symbol, startdate, enddate, mt5.COPY_TICKS_ALL)

        if status != mt5.RES_S_OK:
            logging.warning('No data...')
            return False

        self.tickscache = ticks

    def _orderdic(self, result):
        result_dict = result._asdict()

        for field in result_dict.keys():
            if field == "request":
                result_dict[field] = result_dict[field]._asdict()

        return result_dict

    def _appendrequest(self, request: dict[any], request_date: datetime):
        self.requests = pd.concat(
            [self.requests, pd.DataFrame([request], columns=request.keys(), index=[request_date])])

    def _getprice(self) -> tuple[float, float]:
        bid = float(0)
        ask = float(0)

        for _, p in self.ticks.iloc[::-1].iterrows():
            if p['bid']:
                bid = p['bid']
                break

        for _, p in self.ticks.iloc[::-1].iterrows():
            if p['ask']:
                ask = p['ask']
                break

        return (bid, ask)

    def _sendorder(self, lot: float, side: Side, position: int = None) -> dict[any, any]:
        bid, ask = self._getprice()

        if not bid or not ask:
            logging.error('Price was not recovered.')
            return {
                'retcode': mt5.TRADE_RETCODE_ERROR
            }

        request = {
            "symbol": self.symbol,
            "volume": lot,
            "type": side,
            "price": ask if side == Side.BUY else bid,
        }

        if position:
            request['position'] = position

        logging.info(f'Sim order send, {request}')

        self._appendrequest(request, self.bars.iloc[-1].name)

        return {
            'retcode': mt5.TRADE_RETCODE_DONE
        }

    def _simposition(self):
        if self.requests.empty:
            return pd.DataFrame()

        last_request = self.requests.iloc[-1].copy()
        if 'position' in last_request.keys() and not math.isnan(last_request['position']):
            return pd.DataFrame()

        if last_request['volume'] != self.lot:
            logging.info('Simulation adjusting position...')
            last_request['volume'] = self.lot

        simpositions = pd.DataFrame(
            [last_request], columns=self.requests.columns, index=[last_request.name])
        simpositions['ticket'] = [random.randint(1, 100000000)]

        return simpositions

    def _dotrade(self):
        if self.bars.empty:
            return

        signal = None
        newbar = False

        if self.__current.name != self.bars.iloc[-1].name:
            newbar = True

        self.__current = self.bars.iloc[-1]

        logging.info(
            f'Current bar: {dict(last=self.__current.name, count=len(self.bars))}')

        if newbar and len(self.bars) > 1:
            previous = self.bars.iloc[-2]
            self.__targethigh = previous['high'] + 5
            self.__targetlow = previous['low'] - 5

        if self.__targethigh and self.__targetlow:
            if self.__current['close'] >= self.__targethigh:
                signal = Side.BUY
            if self.__current['close'] <= self.__targetlow:
                signal = Side.SELL

        positions = self._simposition()
        if len(positions) > 0:
            position = positions.iloc[-1]
            if position['type'] == Side.SELL and signal == Side.BUY:
                logging.info('Invert sell to buy...')
                self._sendorder(position['volume'] * 2, Side.BUY)
            elif position['type'] == Side.BUY and signal == Side.SELL:
                logging.info('Invert buy to sell...')
                self._sendorder(position['volume'] * 2, Side.SELL)
            else:
                logging.info('Staying in position...')
            return

        if signal == Side.BUY:
            logging.info('Sending buy order...')
            self._sendorder(self.lot, Side.BUY)
        elif signal == Side.SELL:
            logging.info('Sending sell order...')
            self._sendorder(self.lot, Side.SELL)

    def exec(self):
        logging.info('Slide start date...')
        self._slidestartdate()

        logging.info('Loading ticks...')
        if not self._loadticks():
            return

        logging.info('Computing chart...')
        self.computebars(self)

        logging.info('Operating the market...')
        self._dotrade()

        logging.info('Generating trades file...')
        self._requeststocsv()


def startlogs():
    if os.path.exists('debug.log'):
        os.remove('debug.log')

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("debug.log"),
        ]
    )


def main():
    startlogs()

    def _computebars(self):
        bars = self.ticks.resample('1min')['last'].ohlc()
        bars.dropna(inplace=True)
        self.bars = bars

    simulate = dict(
        startdate=datetime(2022, 3, 29, 9, 0, tzinfo=pytz.utc),
        step=timedelta(seconds=1))

    loop = Loop(MT5Client(),
                symbol='WIN$',
                lot=1,
                offset=timedelta(hours=10),
                simulate=simulate,
                computebars=_computebars)

    while True:
        try:
            logging.info('Running loop...')
            loop.exec()
            logging.info('Loop executed...')
        except KeyboardInterrupt:
            logging.error('Requested stop', exc_info=True)
            quit()
        except Exception:
            logging.error('Unknown error', exc_info=True)
            sleep(1)


if __name__ == "__main__":
    main()
