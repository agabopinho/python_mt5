from datetime import datetime, timedelta

from strategy import Side


class Transaction:
    def __init__(self, side: Side, entry_time: datetime, entry_price: float):
        self.side = side
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.exit_price = float(0)
        self.exit_time = datetime.min
        self.operating_time = timedelta(seconds=0)
        self.pips = float(0)
        self.is_open = True

    def close(self, exit_time: datetime, exit_price: float):
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.operating_time = exit_time - self.entry_time

        self.compute(exit_price)

        self.is_open = False

    def compute(self, exit_price: float):
        if self.side == Side.BUY:
            self.pips = exit_price - self.entry_price
        elif self.side == Side.SELL:
            self.pips = self.entry_price - exit_price
        else:
            raise Exception('Invalid side', self.side)

    def to_item_list(self):
        return [
            self.side, self.entry_time, self.entry_price,
            self.exit_price, self.exit_time, self.operating_time,
            self.pips, self.is_open]

    def __str__(self):
        return f'Transaction(side={self.side}' + \
            f', entry_time={self.entry_time}' + \
            f', entry_price={self.entry_price}' + \
            f', exit_time={self.exit_time}' + \
            f', exit_price={self.exit_price}' + \
            f', operating_time={self.operating_time}' + \
            f', pips={self.pips}' + \
            f', is_open={self.is_open})'
