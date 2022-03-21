import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable

import pandas as pd
from advisor.timeframesignal import Side


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


class TradingSimulate:
    def __init__(self, columns: tuple[str, str] = ('bid', 'ask')):
        self.transactions = []
        self.book_transactions = []
        self.columns = columns

    def compute(self, data: pd.DataFrame, signal: Callable[[pd.Series], Side], take_stop: tuple[float, float] = (float, float)):
        logging.info('Computing signals...')

        data['signal'] = data.apply(signal, axis=1)

        logging.info('Computing transactions...')

        transaction = None

        for index, row in data.iterrows():
            transaction = self.__check_close(
                transaction, index, row, take_stop)

            if transaction is None:
                transaction = self.__check_open(index, row)
                if transaction:
                    self.transactions.append(transaction)

    def __check_close(self, transaction: Transaction, index: datetime, row: pd.Series, take_stop: tuple[float, float] = (float, float)) -> Transaction:
        bid, ask = self.columns
        if transaction:
            book_price = row[bid] if transaction.side == Side.BUY else row[ask]
            transaction.compute(book_price)

            if take_stop:
                take, stop = take_stop

                if not stop is None and transaction.pips <= -stop:
                    transaction.close(index, book_price)
                    return None

                if not take is None and transaction.pips >= take:
                    transaction.close(index, book_price)
                    return None

            if transaction.side == Side.BUY and row['signal'] == Side.SELL:
                transaction.close(index, book_price)
                return None
            elif transaction.side == Side.SELL and row['signal'] == Side.BUY:
                transaction.close(index, book_price)
                return None

        return transaction

    def __check_open(self, index: datetime, row: pd.Series) -> Transaction:
        bid, ask = self.columns
        if row['signal'] == Side.BUY:
            return Transaction(Side.BUY, index, row[ask])
        elif row['signal'] == Side.SELL:
            return Transaction(Side.SELL, index, row[bid])
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
