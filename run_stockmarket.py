import logging
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import pandas as pd
from pandas.plotting import register_matplotlib_converters

from strategy.mt5_client import MT5Client

register_matplotlib_converters()


def plt_chart(ticks: pd.DataFrame):
    fig = plt.figure()

    colors = ['tan', 'green', 'navy', 'purple', 'yellow']
    cindex = 0
    for key, items in ticks.groupby('name'):
        plt.plot(items.index, items['variation'],
                 'k--', label=key, color=colors[cindex])
        cindex += 1

    plt.legend(loc='upper left')
    plt.title('Chart')


def get_daterange(date: datetime) -> tuple[datetime, datetime]:
    return (date.replace(hour=9, minute=0, second=0, microsecond=0),
            date.replace(hour=23, minute=20, second=0, microsecond=0))


def get_ticks(client: MT5Client, symbol: str, start_date: datetime, end_date: datetime,) -> pd.DataFrame:
    status, ticks = client.get_ticks(
        symbol, start_date, end_date, mt5.COPY_TICKS_INFO)

    if status != mt5.RES_S_OK:
        client.disconnect()
        quit()

    return ticks


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    client = MT5Client()

    symbols = ['WINJ22', 'WDOJ22']

    client.connect()

    variations = pd.DataFrame()

    for offset in reversed(range(10)):
        date = datetime.utcnow().replace(hour=0) - timedelta(days=offset)
        for symbol in symbols:
            mt5.symbol_select(symbol, True)
            start_date, end_date = get_daterange(date)
            current_ticks = get_ticks(client, symbol, start_date, end_date)

            last_day_ticks = pd.DataFrame()
            attempts = 0

            while len(last_day_ticks) <= 0:
                start_date, end_date = get_daterange(
                    start_date - timedelta(days=1))
                start_date = start_date.replace(hour=16)
                last_day_ticks = get_ticks(
                    client, symbol, start_date, end_date)

                attempts += 1
                if attempts > 3:
                    raise Exception('Maximum attempts.')

            logging.info('Computing...')

            if len(current_ticks) == 0:
                continue

            last_day_close = last_day_ticks.iloc[-1]['last']
            current_var = pd.DataFrame()

            chart = current_ticks.resample('300s')['last'].ohlc()

            current_var['variation'] = (
                (chart['close'] - last_day_close) / last_day_close) * 100
            current_var['name'] = symbol

            variations = pd.concat([variations, current_var])

    plt_chart(variations)
    plt.show()


if __name__ == "__main__":
    main()
