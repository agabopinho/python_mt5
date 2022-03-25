import logging

import mplfinance as mpf
import pandas as pd
from matplotlib import pyplot as plt
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

plt.rcParams["figure.autolayout"] = True


def __pltbalance(trades: pd.DataFrame):
    logging.info('Plotting balance')
    print(trades)

    fig = plt.figure()
    plt.plot(trades.index, trades['balance'], 'y-', label='Balance')
    plt.gcf().autofmt_xdate()

    plt.legend(loc='upper left')
    plt.title(f'Info')

    plt.show()
    plt.close(fig)
    

def pltbalance(trades: pd.DataFrame): 
    logging.info('Plotting balance')
    print(trades)
    
    df = pd.DataFrame()
    
    df['open'] = trades['balance'] 
    df['high'] = trades['balance'] 
    df['low'] = trades['balance'] 
    df['close'] = trades['balance'] 
    
    mpf.plot(df, type='line', title='Data', style='classic')


def pltchart(data: pd.DataFrame, trades: pd.DataFrame = None):
    alines = []
    for index, trade in trades.iterrows():
        open = (index, trade['entry_price'])
        close = (trade['exit_time'], trade['exit_price'])

        alines.append([open, close])

    c = []
    if 'sma_1' in data.columns: 
        c.append('sma_1')
    if 'sma_2' in data.columns: 
        c.append('sma_2')
    
    addplot = mpf.make_addplot(data[c]) if c else []

    mpf.plot(data, type='candle', title='Data', style='classic',
             alines=dict(alines=alines, colors=['b', 'r', 'c', 'k', 'g']), addplot=addplot)
