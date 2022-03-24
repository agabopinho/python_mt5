import logging
from datetime import datetime
from typing import Callable

import pandas as pd
from strategy import Side

from backtesting.transaction import Transaction


class TradingSimulate:
    def __init__(self, sides: list[Side] = [Side.BUY, Side.SELL], columns: tuple[str, str] = ('bid', 'ask')):
        self.sides = sides
        self.transactions = []
        self.book_transactions = []
        self.columns = columns

    def compute(self, data: pd.DataFrame, signal: Callable[[pd.Series], Side], risk: tuple[float, float, float] = (float, float)):
        logging.info('Computing signals...')

        data['signal'] = data.apply(signal, axis=1)

        logging.info('Computing transactions...')

        transaction = None

        for index, row in data.iterrows():
            transaction = self.__check_close(
                transaction, index, row, risk)

            if transaction is None:
                transaction = self.__check_open(index, row)
                if transaction:
                    self.transactions.append(transaction)

        if not transaction is None:
            row = data.iloc[-1]
            bid, ask = self.columns
            book_price = row[bid] if transaction.side == Side.BUY else row[ask]
            transaction.close(index, book_price)

    def __check_close(self, transaction: Transaction, index: datetime, row: pd.Series, risk: tuple[float, float, float] = (float, float)) -> Transaction:
        bid, ask = self.columns
        if transaction:
            book_price = row[bid] if transaction.side == Side.BUY else row[ask]
            transaction.compute(book_price)

            if risk:
                takepips, stoppips, trailingstoppips = risk

                if takepips and transaction.pips >= abs(takepips):
                    transaction.close(index, book_price)
                    return None

                if stoppips and transaction.pips <= -abs(stoppips):
                    transaction.close(index, book_price)
                    return None

                if trailingstoppips and transaction.max_pips > trailingstoppips and transaction.max_pips - transaction.pips >= abs(trailingstoppips):
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
        if row['signal'] == Side.BUY and Side.BUY in self.sides:
            return Transaction(Side.BUY, index, row[ask])
        if row['signal'] == Side.SELL and Side.SELL in self.sides:
            return Transaction(Side.SELL, index, row[bid])
        return None

    def to_dataframe(self):
        data = [item.todict() for item in self.transactions]

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(
            data=data,
            columns=data[0].keys())

        df.index = df['entry_time']
        df.drop(columns=['entry_time'], inplace=True)

        df['balance'] = df['pips'].cumsum()

        return df
