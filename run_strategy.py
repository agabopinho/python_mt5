import logging
import math
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

        self._sim_startdate = None

        if type(self.simulate) != dict:
            raise Exception('Invalid arg: simulate.')

        if not 'simulation' in self.simulate:
            raise Exception('Not found arg: simulate.simulation.')

        if self.simulate['simulation']:
            if not 'startdate' in self.simulate or type(self.simulate['startdate']) != datetime or self.simulate['startdate'].tzinfo != pytz.utc:
                raise Exception('Invalid arg: simulate.startdate.')

            self._sim_startdate = self.simulate['startdate']

            if not 'step' in self.simulate:
                self.simulate['step'] = timedelta(seconds=1)

    def _requeststocsv(self):
        requests = self.requests.copy()
        profits = []
        p = pd.Series(dtype=object)

        for _, r in requests.iterrows():
            if p.empty:
                p = r
                profits.append(0)
                continue

            if p['type'] == mt5.POSITION_TYPE_BUY:
                profits.append(r['price'] - p['price'])
            elif p['type'] == mt5.POSITION_TYPE_SELL:
                profits.append(p['price'] - r['price'])

            p = r

        if len(profits) < len(requests):
            if p['type'] == mt5.POSITION_TYPE_BUY:
                profits.append(self.bars.iloc[-1]['close'] - p['price'])
            elif p['type'] == mt5.POSITION_TYPE_SELL:
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
        now = datetime.now().replace(tzinfo=pytz.utc)
        end_date = now

        if self.simulate['simulation']:
            end_date = self._sim_startdate
            self._sim_startdate += self.simulate['step']

            if self._sim_startdate > now:
                self._sim_startdate = now

        start_date = end_date - self.offset

        if not self.simulate['simulation']:
            end_date += timedelta(seconds=5)

        return start_date, end_date

    def _loadticks(self) -> bool:
        startdate, enddate = self._dates()
        startdateodd = startdate
        enddateodd = enddate

        if self.simulate['simulation']:
            if self.tickscache.empty:
                startdate = startdate.replace(
                    hour=0, minute=0, second=0, microsecond=0)
                enddate = startdate + timedelta(days=1)
            else:
                self.ticks = self.tickscache[startdate:enddate]
                return not self.ticks.empty

        status, ticks = self.client.get_ticks(
            self.symbol, startdate, enddate, mt5.COPY_TICKS_ALL)

        if status != mt5.RES_S_OK:
            logging.warning('No data...')
            return False

        self.ticks = ticks[startdateodd:enddateodd]
        self.tickscache = ticks

        return not self.ticks.empty

    def _orderdic(self, result):
        result_dict = result._asdict()

        for field in result_dict.keys():
            if field == "request":
                result_dict[field] = result_dict[field]._asdict()

        return result_dict

    def _appendrequest(self, request: dict[any], request_date: datetime):
        self.requests = pd.concat(
            [self.requests, pd.DataFrame([request], columns=request.keys(), index=[request_date])])

    def _getprice(self, side: Side) -> float | None:
        if not self.simulate['simulation']:
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

    def _sendorder(self, lot: float, side: Side, position: int = None) -> dict[any, any]:
        price = self._getprice(side)

        if not price:
            logging.error('Price was not recovered.')
            return {
                'retcode': mt5.TRADE_RETCODE_ERROR
            }

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

        if self.simulate['simulation']:
            logging.info(f'Sim order send, {request}')

            self._appendrequest(request, self.bars.iloc[-1].name)

            return {
                'retcode': mt5.TRADE_RETCODE_DONE
            }

        result = mt5.order_send(request)
        self._appendrequest(request, datetime.now().replace(tzinfo=pytz.utc))

        if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
            if not result:
                logging.error(
                    f'Order send failed, there was no result.')
            else:
                logging.error(
                    f'Order send failed, {self._orderdic(result)}')

        return self._orderdic(result)

    def _postorderwait(self):
        if not self.simulate['simulation']:
            sleep(5)

    def _simposition(self):
        if self.requests.empty:
            return pd.DataFrame()

        last_request = self.requests.iloc[-1].copy()
        if 'position' in last_request.keys() and not math.isnan(last_request['position']):
            return pd.DataFrame()

        if last_request['volume'] != self.lot:
            logging.info('Simulation: Adjusting position...')
            last_request['volume'] = self.lot

        simpositions = pd.DataFrame(
            [last_request], columns=self.requests.columns, index=[last_request.name])
        simpositions['ticket'] = [random.randint(1, 100000000)]

        return simpositions

    def _dotrade(self):
        if self.bars.empty:
            return

        lastbar = self.bars.iloc[-1]
        signal = None

        if lastbar['buy']:
            signal = Side.BUY
        elif lastbar['sell']:
            signal = Side.SELL

        logging.info(f'Current bar: {lastbar.name}')

        positions = pd.DataFrame()

        if self.simulate['simulation']:
            logging.info('Simulating positions...')
            positions = self._simposition()
        else:
            status, positions = self.client.get_position(self.symbol)

            if status != mt5.RES_S_OK:
                logging.error(
                    'Cannot trade, error when searching for position.')
                return

        if positions.empty:
            if signal == Side.BUY:
                logging.info('Sending buy order...')
                self._sendorder(self.lot, Side.BUY)
                self._postorderwait()
            elif signal == Side.SELL:
                logging.info('Sending sell order...')
                self._sendorder(self.lot, Side.SELL)
                self._postorderwait()

            return

        position = positions.iloc[-1]

        if position['type'] == mt5.POSITION_TYPE_SELL and signal == Side.BUY:
            logging.info('Invert sell to buy...')
            self._sendorder(position['volume'] * 2, Side.BUY)
            self._postorderwait()
        elif position['type'] == mt5.POSITION_TYPE_BUY and signal == Side.SELL:
            logging.info('Invert buy to sell...')
            self._sendorder(position['volume'] * 2, Side.SELL)
            self._postorderwait()
        else:
            logging.info('Staying in position...')

    def exec(self):
        self.client.connect()

        logging.info('Loading symbol...')
        if not self._loadsymbol():
            return

        logging.info('Loading ticks...')
        if not self._loadticks():
            return

        logging.info('Computing chart...')
        self.computebars(self)

        logging.info('Operating the market...')
        self._dotrade()

        if self.simulate['simulation']:
            logging.info('Generating trades file...')
            self._requeststocsv()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    def __computebars(self):
        chart = self.ticks.resample('2min')['last'].ohlc()
        chart.dropna(inplace=True)

        chart['rsifast'] = rsi(chart['close'], window=34).ewm(
            alpha=1 / 8, min_periods=1, adjust=False).mean()
        chart['rsislow'] = rsi(chart['close'], window=144).ewm(
            alpha=1 / 8, min_periods=1, adjust=False).mean()
        chart['cci'] = cci(chart['high'], chart['low'],
                           chart['close'], window=21)

        chart['buy'] = np.where(
            (chart['cci'] > 100) &
            (chart['cci'].shift(1) < 100) &
            (chart['rsifast'] > chart['rsislow']), True, False)
        chart['sell'] = np.where(
            (chart['cci'] < -100) &
            (chart['cci'].shift(1) > -100) &
            (chart['rsifast'] < chart['rsislow']), True, False)

        self.bars = chart

    simulate = dict(
        simulation=True,
        startdate=datetime(2022, 3, 28, 9, 0, tzinfo=pytz.utc),
        step=timedelta(seconds=1))

    loop = Loop(MT5Client(),
                symbol='WIN$',
                lot=1,
                offset=timedelta(hours=5),
                simulate=simulate,
                computebars=__computebars)

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
