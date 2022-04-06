import logging

import mplfinance as mpf
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from pandas.plotting import register_matplotlib_converters
from pyparsing import col

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
    df.index = trades.index

    mpf.plot(df, type='line', title='Data', style='classic')


def pltchart(data: pd.DataFrame, trades: pd.DataFrame = None, price='open', mav=()):
    alines = []

    if type(trades) == pd.DataFrame and not trades.empty:
        for index, trade in trades.iterrows():
            open = (index, trade['entry_price'])
            close = (trade['exit_time'], trade['exit_price'])

            alines.append([open, close])

    addplot = []

    columns = []
    if 'sma_1' in data.columns:
        columns.append('sma_1')
    if 'sma_2' in data.columns:
        columns.append('sma_2')
    if 'bolu' in data.columns:
        columns.append('bolu')
    if 'bold' in data.columns:
        columns.append('bold')
    if 'ema' in data.columns:
        columns.append('ema')
    if 'psarup' in data.columns:
        columns.append('psarup')
        columns.append('psardown')
        
    if 'lineup' in data.columns:
        columns.append('lineup')
    if 'linedown' in data.columns:
        columns.append('linedown')
    if 'linemiddle' in data.columns:
        columns.append('linemiddle')
        
    if 'delta' in data.columns:
        addplot.append(mpf.make_addplot(
            data[['delta', 'detal_ema']], panel=1))
       
    if columns:
        addplot.append(mpf.make_addplot(data[columns]))

    if 'rsi' in data.columns:
        addplot.append(mpf.make_addplot(
            data[['rsi', 'rsi_up', 'rsi_down']], panel=1))
        
    if 'rsifast' in data.columns:
        addplot.append(mpf.make_addplot(
            data[['rsifast', 'rsislow']], panel=1))

    if 'adx' in data.columns:
        addplot.append(mpf.make_addplot(
            data[['adx_pos', 'adx_neg']], panel=1))
    
    if 'cci' in data.columns:
        addplot.append(mpf.make_addplot(
            data[['cci']], panel=2))
        
    if 'buy' in data.columns and not data[data['buy']].empty:
        addplot.append(mpf.make_addplot(np.where(
            data['buy'], data[price], np.nan), type='scatter', marker='^'))

    if 'sell' in data.columns and not data[data['sell']].empty:
        addplot.append(mpf.make_addplot(np.where(
            data['sell'], data[price], np.nan), type='scatter', markersize=25, marker='v'))

    mpf.plot(data, mav=mav, type='candle', title='Data', style='classic',
             alines=dict(alines=alines, colors=['b', 'r', 'c', 'k', 'g']), addplot=addplot, show_nontrading=False)
