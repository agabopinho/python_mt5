from datetime import datetime, timedelta

from strategy import Side


class Transaction:
    def __init__(self, side: Side, entry_time: datetime, entry_price: float, slippage: float = 0):
        self.side = side
        self.entry_time = entry_time
        self.entry_price = entry_price + \
            slippage if side == Side.BUY else entry_price - slippage
        self.exit_price = float(0)
        self.exit_time = datetime.min
        self.operating_time = timedelta(seconds=0)
        self.pips = float(0)
        self.min_pips = float(0)
        self.max_pips = float(0)
        self.is_open = True

    def close(self, exit_time: datetime, exit_price: float, slippage: float = 0):
        if not self.is_open:
            raise Exception('Transaction is closed.')

        self.exit_time = exit_time
        self.exit_price = exit_price + \
            slippage if self.side == Side.SELL else exit_price - slippage
        self.operating_time = exit_time - self.entry_time

        self.compute(self.exit_price)

        self.is_open = False

    def compute(self, exit_price: float):
        if self.side == Side.BUY:
            self.pips = exit_price - self.entry_price
        elif self.side == Side.SELL:
            self.pips = self.entry_price - exit_price
        else:
            raise Exception('Invalid side', self.side)

        if self.pips < self.min_pips:
            self.min_pips = self.pips

        if self.pips > self.max_pips:
            self.max_pips = self.pips

    def todict(self):
        return dict(
            side=self.side,
            entry_time=self.entry_time,
            entry_price=self.entry_price,
            exit_price=self.exit_price,
            exit_time=self.exit_time,
            operating_time=self.operating_time,
            pips=self.pips,
            min_pips=self.min_pips,
            max_pips=self.max_pips,
            is_open=self.is_open)

    def __str__(self):
        return f'Transaction(side={self.side}' + \
            f', entry_time={self.entry_time}' + \
            f', entry_price={self.entry_price}' + \
            f', exit_time={self.exit_time}' + \
            f', exit_price={self.exit_price}' + \
            f', operating_time={self.operating_time}' + \
            f', pips={self.pips}' + \
            f', min_pips={self.min_pips}' + \
            f', max_pips={self.max_pips}' + \
            f', is_open={self.is_open})'
