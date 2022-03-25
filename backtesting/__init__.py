import logging

import mplfinance as mpf
import pandas as pd
from matplotlib import pyplot as plt
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

plt.rcParams["figure.autolayout"] = True


def pltbalance(trades: pd.DataFrame):
    logging.info('Plotting balance')
    print(trades)

    fig = plt.figure()
    plt.plot(trades.index, trades['balance'], 'y-', label='Balance')
    plt.gcf().autofmt_xdate()

    plt.legend(loc='upper left')
    plt.title(f'Info')

    plt.show()
    plt.close(fig)


def pltchart(data: pd.DataFrame, trades: pd.DataFrame = None):
    alines = []
    for index, trade in trades.iterrows():
        open = (index, trade['entry_price'])
        close = (trade['exit_time'], trade['exit_price'])

        alines.append([open, close])

    addplot = mpf.make_addplot(data[['sma_1', 'sma_2']])

    mpf.plot(data, type='candle', title='Data', style='classic',
             alines=dict(alines=alines, colors=['b', 'r', 'c', 'k', 'g']), addplot=addplot)
