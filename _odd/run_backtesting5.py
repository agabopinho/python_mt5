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
    frame = '30s'
    slippage = 5

    client = MT5Client()
    all_trades = pd.DataFrame()
    all_chart = pd.DataFrame()

    for day in reversed(range(1)):
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
        chart['sma_1'] = chart.rolling(3, min_periods=1)['low'].mean()
        
        logging.info('Trading simulate...')

        trades = []
        histbar = []

        for i, bar in chart.iterrows():
            histbar.append(bar.copy())

            if len(histbar) < 3:
                continue

            previous = histbar[-2]
            lasttrade = trades[-1] if trades else None

            if lasttrade and lasttrade.is_open:
                lasttrade.compute(previous['high'])
                lasttrade.compute(previous['low'])
                lasttrade.compute(bar['open'])
                
                if lasttrade.max_pips - lasttrade.pips >= 100: 
                    lasttrade.close(i, bar['open'], slippage=slippage)
                    
                elif lasttrade.min_pips <= -100: 
                    lasttrade.close(i, bar['open'], slippage=slippage)
                
                # fechamento de compra
                elif lasttrade.side == Side.BUY and previous['close'] < previous['sma_1']:
                    lasttrade.close(i, bar['open'], slippage=slippage)
                else:
                    continue

            if histbar[-2]['close'] >= histbar[-2]['sma_1'] and histbar[-3]['close'] < histbar[-3]['sma_1']:
                trades.append(Transaction(
                    Side.BUY, i, bar['open'], slippage=slippage))
                
                continue

        lasttrade = trades[-1] if trades else None
        if lasttrade and lasttrade.is_open:
            lasttrade.close(chart.iloc[-1].name, chart.iloc[-1]['close'])

        all_trades = pd.concat([all_trades, trades_todataframe(trades)])
        all_chart = pd.concat([all_chart, chart])

    # all_trades = all_trades[all_trades['side'] == Side.BUY]
    all_trades['balance'] = all_trades['pips'].cumsum()
    all_trades.to_csv(f'backtesting-trades{slippage}.csv', sep='\t')

    print(all_trades)
    pltbalance(all_trades)
    pltchart(all_chart, all_trades)


if __name__ == "__main__":
    main()
