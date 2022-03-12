import logging
import os
import shutil
from datetime import datetime, time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters
from varname import nameof

register_matplotlib_converters()


class TicksData:
    def load(self, path: str, intraday_start: time, intraday_end: time) -> pd.DataFrame:
        ticks = pd.read_csv(path, sep='\t')

        ticks.rename(columns={
            '<DATE>': 'date',
            '<TIME>': 'time',
            '<BID>': 'bid',
            '<ASK>': 'ask',
            '<LAST>': 'last',
            '<VOLUME>': 'volume',
            '<FLAGS>': 'flags',
        }, inplace=True)

        # parse date and time
        ticks['date'] = pd.to_datetime(
            ticks['date'], format='%Y.%m.%d')
        ticks['time'] = pd.to_datetime(
            ticks['time'], format='%H:%M:%S.%f') - datetime(1900, 1, 1)
        ticks['date'] = ticks['date'] + ticks['time']

        ticks.drop(columns=['time'], inplace=True)

        ticks = pd.DataFrame({
            'bid': ticks['bid'].to_list(),
            'ask': ticks['ask'].to_list(),
            'last': ticks['last'].to_list(),
            'volume': ticks['volume'].to_list(),
            'flags': ticks['flags'].to_list()
        }, index=ticks['date'])

        ticks = ticks[np.logical_or(
            ticks['ask'] > 0, ticks['bid'] > 0)]

        self.__format_price(ticks)

        ticks = ticks[np.logical_and(
            ticks['ask'] > 0,
            ticks['bid'] > 0)]

        ticks = ticks[ticks['ask'] > ticks['bid']]

        ticks = ticks.between_time(intraday_start,
                                   intraday_end, inclusive='both')

        return ticks

    def __format_price(self, ticks: pd.DataFrame) -> pd.DataFrame:
        self.__apply_price_sequence(ticks, 'bid')
        self.__apply_price_sequence(ticks, 'ask')

    def __apply_price_sequence(self, ticks: pd.DataFrame, column_name: str):
        state = [float(0)]
        ticks[column_name] = ticks.apply(
            lambda row: self.__apply_price_sequence_func(row, state, column_name), axis=1)

    def __apply_price_sequence_func(self, row: pd.Series, state: list[float], column_name: str):
        if row[column_name] > 0:
            state[0] = float(row[column_name])

        return state[0]


class PlotData:
    def __init__(self, image_dir: str, data_dir: str):
        self.image_dir = image_dir
        self.data_dir = data_dir

    def init_dirs(self):
        if os.path.exists(self.image_dir):
            shutil.rmtree(self.image_dir)
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)

        if not os.path.exists(self.image_dir):
            os.mkdir(self.image_dir)
        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)

    def slice_and_plot(self, ticks: pd.DataFrame, range_minutes: int, limit_samples: int = None):
        count = 1
        range_index = 0
        range_data = []

        logging.info(
            f'Slice and plot, info: data_len: {len(ticks)}, {nameof(range_minutes)}: {range_minutes}, {nameof(limit_samples)}: {limit_samples}')

        for index, row in ticks.iterrows():
            index_time = index.time()

            if index_time.minute // range_minutes != range_index:
                logging.info(f'Slice and plot, range index: {range_index}')

                range_index = index_time.minute // range_minutes
                self.__plot_range(range_data)
                range_data = []
                count = count + 1

                if not limit_samples is None and count > limit_samples:
                    break

            range_data.append([index, row['bid'], row['ask']])

        if len(range_data) > 0:
            self.__plot_range(range_data)

    def __plot_range(self, range: list):
        self.__plot(pd.DataFrame(range, columns=[
            'date', 'bid', 'ask']))

    def __plot(self, ticks: pd.DataFrame):
        slice_name = ticks.iloc[0]['date'].strftime('%Y%m%d%H%M%S')

        ticks.to_csv(
            f'{os.path.join(self.data_dir, slice_name)}.csv', sep='\t')

        plt.plot(ticks['date'], ticks['ask'], 'r-', label='ask')
        plt.plot(ticks['date'], ticks['bid'], 'b-', label='bid')

        plt.axis('off')

        plt.savefig(
            f'{os.path.join(self.image_dir, slice_name)}.png', format='png')
        plt.clf()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            # logging.FileHandler("debug.log"),
            logging.StreamHandler()
        ]
    )

    file = './export_data/WIN@N_202201030855_202203091831_FLAT.csv'
    image_dir = './export_data/images/'
    data_dir = './export_data/data/'

    logging.info('Loading data...')
    ticks_data = TicksData()
    ticks = ticks_data.load(file, time(9), time(18))

    logging.info('Init dir...')
    plot_data = PlotData(image_dir, data_dir)
    plot_data.init_dirs()

    logging.info('Slice and plot...')
    plot_data.slice_and_plot(ticks, range_minutes=5, limit_samples=10)

    logging.info('Done!')


if __name__ == "__main__":
    main()
