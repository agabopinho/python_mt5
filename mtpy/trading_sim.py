
import pandas as pd


def trading_sim(ticks: pd.DataFrame): 
    ticks['trade_buy'] =  [True if x['soft_sma'] > x['fast_sma'] > x['slow_sma'] else False for _, x in ticks.iterrows()]
    ticks['trade_sell'] =  [True if x['soft_sma'] < x['fast_sma'] < x['slow_sma'] else False for _, x in ticks.iterrows()]