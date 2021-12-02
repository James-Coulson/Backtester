# Standard libraries
from zipfile import ZipFile
import pandas as pd

# Importing user-made libraries
from _binance import BinanceBroker


class Backtester:
    """
    Class used to conduct a backtest

     - For now will only get the 15 min klines. Once binance implementation handles other methods that functionality can
       be added.
    """

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, symbols_required: list):
        """
        Initializes the brokers and the Logger
        """
        # Saving required symbols
        self.symbols_required = symbols_required

        # Creating Brokers dictionary
        self.brokers = dict()

        # Creating brokers and adding to dictionary
        self.brokers['binance'] = BinanceBroker()

        # Get data for backtest
        self.data = self.get_binance_data()

        # Variable to hold the current time
        self.time = 0

    # ----------------------------------- Getter Methods -----------------------------------

    def get_brokers(self):
        """
        Used to obtain the brokers

        :return: Returns a dictionary of the different broker objects
        """
        return self.brokers

    # ----------------------------------- Getting Market Data -----------------------------------

    def get_binance_data(self):
        """
        Used to get binance market data
         - For now only gets a respecified data set.

        :return: Returns a pandas DataFrame of the data
        """
        # Headers for the CSV
        headers = ['open time', 'open', 'high', 'low', 'close', 'volume', 'close time', 'quote asset volume',
                   'number of trades', 'taker buy asset volume', 'taker buy quote asset volume', 'ignore']

        # Returning DataFrame
        return pd.read_csv("./test_data/binance/spot/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-2021-10.zip", compression='zip', names=headers)

    # ----------------------------------- Main backtesting Method -----------------------------------

    def run_backtest(self):
        """
        Called to run the backtest
        """
        # Iterate through market data
        for i in range(len(self.data)):
            # Get current market data
            row = self.data.iloc[i]

            # Send data to binance
            self.send_data_to_binance(row=row)

            # Check orders in binance
            self.brokers['binance'].check_orders(symbol='BTCUSDT')

            # Send new market data
            self.brokers['binance'].send_mkt_data(symbol='BTCUSDT')

    # ----------------------------------- Sending market data -----------------------------------

    def send_data_to_binance(self, row):
        """
        Used to send market data to the BinanceBroker

        :param row: DataFrame row that contains the new market data
        """
        # Convert row to a dictionary
        mkt_data = dict()
        mkt_data['open time'] = row['open time']
        mkt_data['open'] = row['open']
        mkt_data['high'] = row['high']
        mkt_data['low'] = row['low']
        mkt_data['close'] = row['close']
        mkt_data['volume'] = row['volume']
        mkt_data['close time'] = row['close time']
        mkt_data['number of trades'] = row['number of trades']

        # Give data to BinanceBroker
        self.brokers['binance'].update_klines(symbol='BTCUSDT', klines=mkt_data)
