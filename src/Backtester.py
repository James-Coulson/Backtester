# Standard libraries
import pandas as pd

# Importing user-made libraries
from src._binance import BinanceBroker
from src.helper_funcs import trade_data_collation
from src.Logger import Logger
from src.helper_funcs import downloaded_filepaths


class Backtester:
    """
    Class used to conduct a backtest

     - For now will only get the 15 min klines. Once binance implementation handles other methods that functionality can
       be added.
    """

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, start_date: str, end_date: str, symbol_data_required: dict, debug):
        """
        Initializes the brokers and the Logger

        :param start_date: Beginning date of the backtest (format: DD-MM-YYYY)
        :param end_date: Ending date of the backtest (format: DD-MM-YYYY)
        :param symbol_data_required: The symbols required for the backtest
        :param debug: A dictionary used to enable certain debug features
        """
        # Debug variable
        self.debug = debug

        # Saving required symbols
        self.symbol_data_required = symbol_data_required

        # Creating Brokers dictionary
        self.brokers = dict()

        # Creating brokers and adding to dictionary
        self.brokers['binance'] = BinanceBroker(_get_time=self.get_time)

        # Variable to hold the current time
        self.time = 0

        # Get data for backtest
        self.kline_data = self.get_binance_data(start_date, end_date, symbol_data_required)

        # Get trade data
        self.binance_trade_data = self.get_trade_data(start_date, end_date, symbol_data_required)

        # Adding logger to backtester
        self.logger = Logger()

    # ----------------------------------- Getter Methods -----------------------------------

    def get_brokers(self):
        """
        Used to obtain the brokers

        :return: Returns a dictionary of the different broker objects
        """
        return self.brokers

    def get_time(self):
        """
        When called returns the current time

        :return: The current time in UNIX
        """
        return self.time

    # ----------------------------------- Getting Market Data -----------------------------------

    def get_binance_data(self, start_date, end_date, symbol_data_required):
        """
        Used to get binance market data
         - For now only gets a respecified data set.

        :param filepaths: Dictionary of symbols as keys and pathname as value
        :return: Returns a pandas DataFrame of the data
        """
        # Headers for the CSV
        headers = ['open time', 'open', 'high', 'low', 'close', 'volume', 'close time', 'quote asset volume',
                   'number of trades', 'taker buy asset volume', 'taker buy quote asset volume', 'ignore']

        # Creating DataFrame
        kline_data = pd.DataFrame()

        # Iterating over downloaded files
        filepaths = downloaded_filepaths("klines", start_date, end_date, symbol_data_required)
        for filepath in filepaths.keys():
            part_df = pd.read_csv(filepath, compression='zip', names=headers)
            part_df["symbol"] = filepaths[filepath][0]
            part_df["interval"] = filepaths[filepath][1]
            kline_data.append(part_df)
        kline_data.sort_values(by="close time")
        return kline_data

    # -----------------------------------Getting Trade Data-----------------------------------------

    def get_trade_data(self, start_date, end_date, symbol_data_required):
        """
        Used to get trade data and collate it into 10 second intervals
        - For now only uses established filenames

        :param filenames: dictionary of ticker symbol as key and pathname as value
        :return: Returns a pandas DataFrame of the data
        """
        trade_data = pd.DataFrame()
        filepaths = downloaded_filepaths("trades", start_date, end_date, symbol_data_required)
        for filepath in filepaths.keys():
            # Importing data with debug features
            if 'limit_trade_imports' in self.debug and self.debug['limit_trade_imports'] is True:
                if 'limit_trade_imports_nrows' in self.debug:
                    part_data = trade_data_collation(filepath, filepaths[filepath][0],
                                                     limit_rows=self.debug['limit_trade_imports'],
                                                     nrows=self.debug['limit_trade_imports_nrows'])
                else:
                    part_data = trade_data_collation(filepath, filepaths[filepath][0],
                                                     limit_rows=self.debug['limit_trade_imports'])
            else:
                part_data = trade_data_collation(filepath, filepaths[filepath][0])
            trade_data = trade_data.append(part_data, ignore_index=True)
        return trade_data.sort_values(by="time")

    # ----------------------------------- Main backtesting Method -----------------------------------

    def run_backtest(self):
        """
        Called to run the backtest
        """
        kline_num = 0
        trade_num = 0

        # Iterates through the trade data
        while trade_num in range(len(self.binance_trade_data)):
            # Set time
            self.time = self.binance_trade_data.iloc[trade_num]["time"]

            # Gets and sends binance trade data to binance broker
            row = self.binance_trade_data.iloc[trade_num]

            # Send trade data to BinanceBroker
            self.send_trade_data_to_binance(row=row)

            # Check orders in binance
            self.brokers['binance'].check_orders(symbol=row['symbol'])

            # When trade data interval overlaps with kline data, send kline data to broker
            while self.kline_data.iloc[kline_num]["close time"] <= self.time and kline_num < len(self.kline_data):
                # Get row and increment kline counter
                kline_row = self.kline_data.iloc[kline_num]
                kline_num += 1

                # Send data to binance
                self.send_data_to_binance(row=kline_row)

                # Send new market data
                self.brokers['binance'].send_mkt_data(symbol=row['symbol'])
            trade_num += 1


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

    # ----------------------------------- Sending Trade Data ----------------------------------------

    def send_trade_data_to_binance(self, row):
        """
        Gets input row of trade data and gives it to binance

        :param row: row of DataFrame of trade_data
        """
        # Convert to dictionary
        trade_data = dict()
        trade_data["symbol"] = row["symbol"]
        trade_data["price"] = row["price"]
        trade_data["qty"] = row["qty"]

        # Send trade data to BinanceBroker
        self.brokers['binance'].update_trade_data(trade_data)
