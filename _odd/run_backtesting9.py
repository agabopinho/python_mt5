import logging
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import pytz
import ta

from backtesting import pltbalance, pltchart
from backtesting.transaction import Transaction
from run_backtesting8 import simplifyorders
from strategy import Side
from strategy.mt5_client import MT5Client


def trades_todataframe(trades: list[Transaction]):
    data = [item.todict() for item in trades]

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(
        data=data,
        columns=data[0].keys())

    df.index = df['entry_time']
    df.drop(columns=['entry_time'], inplace=True)

    df['balance'] = df['pips'].cumsum()

    return df


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    symbol = 'WINJ22'
    slippage = 0

    client = MT5Client()

    for f in [30]:
        all_trades = pd.DataFrame()
        all_chart = pd.DataFrame()
        frame = f'{f}s'

        for day in reversed(range(10)):
            date = datetime.now() - timedelta(days=day)
            start_date = datetime(date.year, date.month,
                                  date.day, 9, 0, tzinfo=pytz.utc)
            end_date = datetime(date.year, date.month,
                                date.day, 17, 20, tzinfo=pytz.utc)

            client.connect()

            status, ticks = client.get_ticks(
                symbol, start_date, end_date, mt5.COPY_TICKS_ALL)

            if status != mt5.RES_S_OK:
                client.disconnect()
                quit()

            client.disconnect()

            logging.info('Computing...')

            if len(ticks) == 0:
                continue

            chart = ticks.resample(frame)['last'].ohlc()
            chart.dropna(inplace=True)

            rsi = ta.momentum.rsi(
                (chart['high'] + chart['low'] + chart['close']) / 3, window=5)
            stock = ta.momentum.stoch(
                chart['high'], chart['low'], chart['close'], window=5)

            chart['rsi'] = rsi
            chart['rsi_up'] = 60
            chart['rsi_down'] = 40

            chart['stock'] = stock
            chart['stock_up'] = 50
            chart['stock_down'] = 50

            chart['buy'] = np.where(
                (chart['rsi'].shift(1) > chart['rsi_down'].shift(1)), True, False)
            chart['sell'] = np.where(
                (chart['rsi'].shift(1) < chart['rsi_up'].shift(1)), True, False)

            simplifyorders(chart)

            logging.info('Trading simulate...')

            trades = []
            histbar = []

            for i, bar in chart.iterrows():
                histbar.append(bar.copy())

                if len(histbar) < 3:
                    continue
                else:
                    histbar = histbar[-3:]

                lasttrade = trades[-1] if trades else None

                issell = bar['sell']
                isbuy = bar['buy']
                price = 'open'

                if lasttrade and lasttrade.is_open:
                    if lasttrade.side == Side.BUY and issell:
                        lasttrade.close(i, bar[price], slippage)
                    elif lasttrade.side == Side.SELL and isbuy:
                        lasttrade.close(i, bar[price], slippage)
                    else:
                        continue

                if isbuy:
                    trades.append(Transaction(
                        Side.BUY, i, bar[price], slippage))
                    continue

                elif issell:
                    trades.append(Transaction(
                        Side.SELL, i, bar[price], slippage))
                    continue

            lasttrade = trades[-1] if trades else None
            if lasttrade and lasttrade.is_open:
                lasttrade.close(chart.iloc[-1].name, chart.iloc[-1]['close'])

            all_trades = pd.concat([all_trades, trades_todataframe(trades)])
            all_chart = pd.concat([all_chart, chart])

        all_trades['balance'] = all_trades['pips'].cumsum()
        all_trades.to_csv(f'backtesting-trades.csv', sep='\t')

        pltbalance(all_trades)
        pltchart(all_chart, all_trades)


if __name__ == "__main__":
    main()
