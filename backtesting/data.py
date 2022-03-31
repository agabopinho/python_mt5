
import MetaTrader5 as mt5
from strategy.mt5_client import MT5Client


class Data():
    @staticmethod
    def ticks(symbol, start, end):
        client = MT5Client()
        client.connect()

        status, ticks = client.get_ticks(
            symbol, start, end, mt5.COPY_TICKS_ALL)

        client.disconnect()
        
        if status != mt5.RES_S_OK:
            raise Exception('Error on get ticks.')
        
        return ticks
