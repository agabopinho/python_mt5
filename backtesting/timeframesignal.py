
from pprint import pformat
import pandas as pd

from tradingsimulate import Side


class TimeFrameSignal:
    def __init__(self, timeframe: pd.DataFrame, ticks: pd.DataFrame, inverse: bool = False):
        self.timeframe = timeframe
        self.ticks = ticks
        self.inverse = inverse
        self.__items = []

    def signal(self, item: pd.Series) -> Side:
        self.__items.append(item.copy(deep=False))

        if len(self.__items) < 10:
            return None

        window = self.__items[-10:]

        if self.__cross_up_down(window.copy()):
            return Side.SELL if not self.inverse else Side.BUY

        if self.__cross_down_up(window.copy()):
            return Side.BUY if not self.inverse else Side.SELL

        return None

    def __cross_down_up(self, window: list[pd.Series]) -> bool:
        is_down = False
        is_up = False

        window.reverse()

        for item in window:
            if not is_up and item['sma_fast'] > item['sma_slow']:
                is_up = True

            if item['sma_fast'] < item['sma_slow']:
                is_down = True

            if not is_up:
                return False

            if is_down:
                return True

        return False

    def __cross_up_down(self, window: list[pd.Series]) -> bool:
        is_down = False
        is_up = False

        window.reverse()

        for item in window:
            if not is_down and item['sma_fast'] < item['sma_slow']:
                is_down = True

            if item['sma_fast'] > item['sma_slow']:
                is_up = True

            if not is_down:
                return False

            if is_up:
                return True

        return False


if __name__ == "__main__":
    quit()
