from datetime import datetime, timedelta
from enum import Enum
import logging
import pandas as pd


class Side(Enum):
    BUY = 1,
    SELL = 2


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

        if self.side == Side.BUY:
            self.pips = exit_price - self.entry_price
        else:
            self.pips = self.entry_price - exit_price

        self.is_open = False

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


class TradingSim:
    def __init__(self):
        self.transactions = []

    def sim(self, ticks: pd.DataFrame):
        logging.info('Computing signals...')

        ticks['signal'] = ticks.apply(self.signal, axis=1)

        logging.info('Computing transactions...')

        transaction = None

        for index, row in ticks.iterrows():
            transaction = self.check_close(transaction, index, row)

            if transaction is None:
                transaction = self.check_open(index, row)
                if not transaction is None:
                    self.transactions.append(transaction)

    def signal(self, row: pd.Series) -> Side:
        if row['soft_sma'] > row['fast_sma'] > row['slow_sma']:
            return Side.BUY
        elif row['soft_sma'] < row['fast_sma'] < row['slow_sma']:
            return Side.SELL
        return None

    def check_close(self, transaction: Transaction, index: datetime, row: pd.Series) -> Transaction:
        if not transaction is None:
            if transaction.side == Side.BUY and row['signal'] == Side.SELL:
                transaction.close(index, row['bid'])
                transaction = None
            elif transaction.side == Side.SELL and row['signal'] == Side.BUY:
                transaction.close(index, row['ask'])
                transaction = None

        return transaction

    def check_open(self, index: datetime, row: pd.Series) -> Transaction:
        if row['signal'] == Side.BUY:
            return Transaction(Side.BUY, index, row['ask'])
        elif row['signal'] == Side.SELL:
            return Transaction(Side.SELL, index, row['bid'])
        return None

    def to_dataframe(self):
        df = pd.DataFrame(
            data=[item.to_item_list() for item in self.transactions],
            columns=[
                'side', 'entry_time', 'entry_price',
                'exit_price', 'exit_time', 'operating_time',
                'pips', 'is_open'])

        df.index = df['entry_time']
        df.drop(columns=['entry_time'])

        df['balance'] = df['pips'].cumsum()

        return df


if __name__ == "__main__":
    quit()
