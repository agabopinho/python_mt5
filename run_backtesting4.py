import logging
from datetime import datetime, timedelta
from pprint import pformat

import MetaTrader5 as mt5
import pandas as pd
import pytz

from backtesting import pltbalance, pltchart
from backtesting.transaction import Transaction
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
    
    for frame in [60]:
        all_trades = pd.DataFrame()
        all_chart = pd.DataFrame()
        frame = f'{frame}s'
        
        for day in reversed(range(5)):
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
            chart['sma_1'] = chart.rolling(5)['close'].mean()

            logging.info('Trading simulate...')

            trades = []
            histbar = []

            for i, bar in chart.iterrows():
                histbar.append(bar.copy())

                if len(histbar) < 2:
                    continue
                else:
                    histbar = histbar[-2:]

                previous = histbar[-2]
                lasttrade = trades[-1] if trades else None

                if lasttrade and lasttrade.is_open:
                    # fechamento de compra
                    if lasttrade.side == Side.BUY and bar['low'] < previous['low']:
                        lasttrade.close(i, previous['low'], slippage=slippage)
                    # fechamento de venda
                    elif lasttrade.side == Side.SELL and bar['high'] > previous['high']:
                        lasttrade.close(i, previous['high'], slippage=slippage)
                    
                    continue

                # rompeu max e min e fechou a cima da max
                if bar['high'] > previous['high'] and bar['low'] < previous['low'] and bar['close'] > previous['high']:
                    t1 = Transaction(
                        Side.SELL, i, previous['low'])
                    t1.close(i, previous['high'], slippage=slippage)
                    trades.append(t1)
                    trades.append(Transaction(
                        Side.BUY, i, previous['high']))
                    continue

                # rompeu max e min e fechou a baixo da min
                elif bar['high'] > previous['high'] and bar['low'] < previous['low'] and bar['close'] < previous['low']:
                    t1 = Transaction(
                        Side.BUY, i, previous['high'])
                    t1.close(i, previous['low'], slippage=slippage)
                    trades.append(t1)
                    trades.append(Transaction(
                        Side.SELL, i, previous['low']))
                    continue

                elif bar['high'] > previous['high']:
                    trades.append(Transaction(
                        Side.BUY, i, previous['high']))
                    continue

                elif bar['low'] < previous['low']:
                    trades.append(Transaction(
                        Side.SELL, i, previous['low']))
                    continue

            lasttrade = trades[-1] if trades else None
            if lasttrade and lasttrade.is_open:
                lasttrade.close(chart.iloc[-1].name, chart.iloc[-1]['close'])

            all_trades = pd.concat([all_trades, trades_todataframe(trades)])
            all_chart = pd.concat([all_chart, chart])

        # all_trades = all_trades[all_trades['side'] == Side.BUY]
        all_trades['balance'] = all_trades['pips'].cumsum()
        all_trades.to_csv(f'backtesting-trades.csv', sep='\t')

        pltbalance(all_trades)
        pltchart(all_chart, all_trades)


if __name__ == "__main__":
    main()
