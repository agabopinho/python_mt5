import logging
import math
import os
import shutil
import time as tm
from datetime import datetime, time
from xmlrpc.client import boolean

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

        logging.info('Parse date and time...')
        ticks['date'] = pd.to_datetime(
            ticks['date'], format='%Y.%m.%d')
        ticks['time'] = pd.to_datetime(
            ticks['time'], format='%H:%M:%S.%f') - datetime(1900, 1, 1)
        ticks['date'] = ticks['date'] + ticks['time']

        logging.info('Drop column time...')
        ticks.drop(columns=['time'], inplace=True)

        logging.info('Create date index...')
        ticks = ticks[['date', 'bid', 'ask', 'last', 'volume', 'flags']]
        ticks.set_index('date', inplace=True)

        logging.info('Filter junk data...')
        ticks = ticks[np.logical_or(
            ticks['ask'] > 0, ticks['bid'] > 0)]

        logging.info('Fill bid and ask prices...')
        self.__format_price(ticks)

        logging.info('Filter junk data...')
        ticks = ticks[np.logical_and(
            ticks['ask'] > 0,
            ticks['bid'] > 0)]

        logging.info('Filter valid trade prices...')
        ticks = ticks[ticks['ask'] > ticks['bid']]

        logging.info('Filter intraday range...')
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


class _ImageData:
    def __init__(self, image_path: str, last_date: datetime, last_bid: float, last_ask: float):
        self.image_path = image_path
        self.last_date = last_date
        self.last_bid = last_bid
        self.last_ask = last_ask


class PlotData:
    def __init__(self, image_dir: str, data_dir: str, label_file: str, debug_csv: boolean = False):
        self.image_dir = image_dir
        self.data_dir = data_dir
        self.label_file = label_file
        self.debug_csv = debug_csv

    def init_dirs(self):
        if os.path.exists(self.image_dir):
            shutil.rmtree(self.image_dir)
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)

        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir, )
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def slice_and_plot(self,
                       ticks: pd.DataFrame,
                       seconds: int,
                       price_step: float = None,
                       limit_samples: int = None):
        count = 1
        range_index = 0
        range_data = []

        logging.info(
            f'Slice and plot, info: len, {len(ticks)}, {nameof(seconds)}, {seconds}, {nameof(limit_samples)}, {limit_samples}')

        last_image = None

        for index, row in ticks.iterrows():
            unixtime = tm.mktime(index.timetuple())

            if range_index == 0:
                range_index = unixtime // seconds

            if unixtime // seconds == range_index:
                range_data.append([index, row['bid'], row['ask']])
                continue

            logging.info(
                f'Slice and plot, {nameof(count)}: {count}, date: {range_data[0][0]}')

            current_frame = pd.DataFrame(
                range_data, columns=['date', 'bid', 'ask'])

            if not last_image is None:
                self.__compute_label(
                    last_image, index, current_frame)

            last = current_frame.iloc[-1]

            image_path = self.__plot(current_frame)
            last_image = _ImageData(
                image_path, last["date"], last['bid'], last['ask'])

            range_index = unixtime // seconds  # new range index
            count = count + 1

            range_data = []  # clean old data

            if not limit_samples is None and count > limit_samples:
                break

            range_data.append([index, row['bid'], row['ask']])

    def __compute_label(self, last_image: _ImageData, index: datetime, current_frame: pd.DataFrame):
        bid = current_frame.iloc[-1]['bid']
        ask = current_frame.iloc[-1]['ask']

        diff = np.mean([bid, ask]) - \
            np.mean([last_image.last_bid, last_image.last_ask])

        if diff > -100 and diff < 100:
            label = f'idle'
        elif diff >= 100:
            label = f'buy'
        else:
            label = f'sell'

        if last_image.last_date.day == index.day:
            self.__append_label(last_image.image_path, label)

    def __plot(self, ticks: pd.DataFrame) -> str:
        slice_name = ticks.iloc[0]['date'].strftime('%Y-%m-%d_%H_%M_%S')
        csv_name = f'{os.path.join(self.data_dir, slice_name)}.csv'
        fig_name = f'{os.path.join(self.image_dir, slice_name)}.png'

        if self.debug_csv:
            ticks.to_csv(csv_name, sep='\t', index=False)

        plt.plot(ticks['date'], ticks['ask'], 'r-', label='ask')
        plt.plot(ticks['date'], ticks['bid'], 'b-', label='bid')
        plt.axis('off')
        plt.savefig(fig_name, format='png')
        plt.clf()

        return fig_name

    def __append_label(self, fig_name: str, label: str):
        with open(self.label_file, 'a') as fd:
            fd.write(f'{os.path.basename(fig_name)}\t{label}' + '\n')


class FormatDataSet:
    def make(self, label_file: str, image_dir: str, output_dir):
        df_labels = pd.read_csv(label_file, sep='\t', names=['path', 'label'])

        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

        for _, row in df_labels.iterrows():
            file_path = os.path.join(image_dir, row['path'])
            output_path = os.path.join(output_dir, row['label'])

            if not os.path.exists(output_path):
                os.makedirs(output_path)

            shutil.copy(file_path, output_path)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            # logging.FileHandler("debug.log"),
            logging.StreamHandler()
        ]
    )

    file = 'WIN@N_202201030855_202203091831_VALIDATION.csv'
    split_seconds = 600

    base_name = os.path.basename(os.path.splitext(file)[0])

    source_file = f'./source_data/{file}'
    out_image_dir = f'./outputs/{base_name}_s{split_seconds}/images/'
    out_data_dir = f'./outputs/{base_name}_s{split_seconds}/data/'
    out_ds_dir = f'./outputs/{base_name}_s{split_seconds}/data_set/'

    out_label = os.path.join(out_data_dir, 'label.csv')

    logging.info('Loading data...')
    ticks_data = TicksData()
    ticks = ticks_data.load(source_file, time(9, 10), time(18))

    logging.info('Init dir...')
    plot_data = PlotData(out_image_dir, out_data_dir, out_label)
    plot_data.init_dirs()

    logging.info('Slice and plot...')
    plot_data.slice_and_plot(
        ticks, seconds=split_seconds, price_step=50, limit_samples=None)

    logging.info('Format data set...')
    format_ds = FormatDataSet()
    format_ds.make(out_label,
                   out_image_dir, out_ds_dir)

    logging.info('Done!')


if __name__ == "__main__":
    main()
