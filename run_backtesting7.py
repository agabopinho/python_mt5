import logging
from datetime import datetime, timedelta

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
    slippage = 5

    client = MT5Client()

    # 10s, 30 pips
    for frame in [10]:
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
                        lasttrade.close(i, previous['low'], slippage)
                    # fechamento de venda
                    elif lasttrade.side == Side.SELL and bar['high'] > previous['high']:
                        lasttrade.close(i, previous['high'], slippage)

                    continue

                # rompeu max e min e fechou a cima da max
                if previous['close'] - previous['open'] > 30:
                    trades.append(Transaction(
                        Side.BUY, i, bar['open']))
                    continue

                elif previous['close'] - previous['open'] < -30:
                    trades.append(Transaction(
                        Side.SELL, i, bar['open']))
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
