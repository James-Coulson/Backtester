# Standard libraries
import pandas as pd
import os
import shutil

# Importing binance download libraries
from binance_data_download.download_kline import download_daily_klines
from binance_data_download.download_trade import download_daily_trades

# Importing user-made libraries
from src._binance import BinanceBroker
from src.helper_funcs import binance_trade_data_collation
from src.Logger import Logger
from src.helper_funcs import downloaded_filepaths


class Backtester:
    """
    Class used to conduct a backtest
    """

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, start_date: str, end_date: str, symbol_data_required: dict, debug: dict):
        """
        Initializes the brokers and the Logger

        :param start_date: Beginning date of the backtest (format: DD-MM-YYYY)
        :param end_date: Ending date of the backtest (format: DD-MM-YYYY)
        :param symbol_data_required: The symbols required for the backtest
        :param debug: A dictionary used to enable certain debug features
        """
        # Debug variable
        self.debug = debug

        # Adding logger to backtester
        self.logger = Logger(_get_time=self.get_time)

        # Saving required symbols
        self.symbol_data_required = symbol_data_required

        # Creating Brokers dictionary
        self.brokers = dict()

        # Creating brokers and adding to dictionary
        self.brokers['binance'] = BinanceBroker(_get_time=self.get_time, logger=self.logger)

        # Variable to hold the current time
        self.time = 0

        # Downloading required data
        self.download_binance_data(symbol_data_required=symbol_data_required, start_date=start_date, end_date=end_date)

        # Get data for backtest
        self.kline_data = self.get_binance_kline_data(start_date, end_date, symbol_data_required)

        # Get trade data
        self.binance_trade_data = self.get_binance_trade_data(start_date, end_date, symbol_data_required)

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

    def get_logger(self):
        """
        Returns the Logger

        :return: The Logger class
        """
        return self.logger

    # ----------------------------------- Getting Market Data -----------------------------------

    def get_binance_kline_data(self, start_date, end_date, symbol_data_required):
        """
        Used to get binance market data

        :param start_date: The start date of the data wanting the be obtained
        :param end_date: The finish date of the data wanting the be obtained
        :param symbol_data_required: Dictionary of symbols as keys and pathname as value
        :return: Returns a pandas DataFrame of the kline data
        """
        # Headers for the CSV
        headers = ['open time', 'open', 'high', 'low', 'close', 'volume', 'close time', 'quote asset volume',
                   'number of trades', 'taker buy asset volume', 'taker buy quote asset volume', 'ignore']

        # Creating DataFrame
        kline_data = pd.DataFrame()

        # Iterating over downloaded files
        filepaths = downloaded_filepaths("klines", start_date, end_date, symbol_data_required)
        for filepath in filepaths.keys():
            part_df = pd.read_csv(filepath, compression='zip', names=headers)   # read csv
            part_df["symbol"] = filepaths[filepath][0]                          # Add symbol column
            part_df["interval"] = filepaths[filepath][1]                        # Add interval column
            kline_data = kline_data.append(part_df)                             # Append to master DataFrame

        # Ordering data by time and returning data
        kline_data = kline_data.sort_values(by="close time")
        return kline_data

    # -----------------------------------Getting Trade Data-----------------------------------------

    def get_binance_trade_data(self, start_date, end_date, symbol_data_required):
        """
        Used to get trade data and collate it into 10 second intervals

        :param start_date: The start date of the data wanting the be obtained
        :param end_date: The finish date of the data wanting the be obtained
        :param symbol_data_required: Dictionary of symbols as keys and pathname as value
        :return: Returns a pandas DataFrame of the trade data
        """
        # Initialize DataFrame
        trade_data = pd.DataFrame()

        # Get filepaths
        filepaths = downloaded_filepaths("trades", start_date, end_date, symbol_data_required)

        # Iterate over filepaths
        for filepath in filepaths.keys():
            # Importing data with debug features
            if 'limit_trade_imports' in self.debug and self.debug['limit_trade_imports'] is True:
                if 'limit_trade_imports_nrows' in self.debug:
                    part_data = binance_trade_data_collation(filepath, filepaths[filepath][0],
                                                             limit_rows=self.debug['limit_trade_imports'],
                                                             nrows=self.debug['limit_trade_imports_nrows'])
                else:
                    part_data = binance_trade_data_collation(filepath, filepaths[filepath][0],
                                                             limit_rows=self.debug['limit_trade_imports'])
            else:
                part_data = binance_trade_data_collation(filepath, filepaths[filepath][0])

            # Append data
            trade_data = trade_data.append(part_data, ignore_index=True)

        # Sort and return trade data
        return trade_data.sort_values(by="time")

    # ----------------------------------- Main backtesting Method -----------------------------------

    def run_backtest(self) -> dict:
        """
        Called to run the backtest

        :return: Returns dictionary containing DataFrame logs
        """
        kline_num = 0
        trade_num = 0

        # Iterates through the trade data
        while trade_num in range(len(self.binance_trade_data)):
            # Set time
            self.time = self.binance_trade_data.iloc[trade_num]["time"]

            # Updates new trade data
            while trade_num < len(self.binance_trade_data) and self.binance_trade_data.iloc[trade_num]["time"] <= self.time:
                # Gets and sends binance trade data to binance broker
                row = self.binance_trade_data.iloc[trade_num]

                # Send trade data to BinanceBroker
                self.send_trade_data_to_binance(row=row)

                # Check orders in binance
                self.brokers['binance'].check_orders(symbol=row['symbol'], mkt="spot")

                # Incrementing trade_num
                trade_num += 1

            # When trade data interval overlaps with kline data, send kline data to broker
            while kline_num < len(self.kline_data) and self.kline_data.iloc[kline_num]["close time"] <= self.time:
                # Get row and increment kline counter
                kline_row = self.kline_data.iloc[kline_num]
                kline_num += 1

                # Send data to binance
                self.send_kline_data_to_binance(row=kline_row)

            # Send new market data
            self.brokers['binance'].send_mkt_data()

        # Returns log dictionary
        return self.logger.give_log()

    # ----------------------------------- Sending market data -----------------------------------

    def send_kline_data_to_binance(self, row):
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
        mkt_data['interval'] = row['interval']
        mkt_data['symbol'] = row['symbol']

        # Give data to BinanceBroker
        self.brokers['binance'].update_klines(symbol=row['symbol'], kline=mkt_data, interval=row['interval'], mkt="spot")

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
        self.brokers['binance'].update_trade_data(trade_data, mkt="spot")

    # ----------------------------------- Downloading Data -----------------------------------

    def download_binance_data(self, symbol_data_required: dict, start_date, end_date):
        """
        Used to download data from Binance.

        :param start_date: The start date
        :param end_date: The end date
        :param symbol_data_required: Dictionary with symbols as keys and a list of required intervals as values
        """
        print("\n----------------------------------- Downloading Historical Data -----------------------------------\n")

        trades_base_path = "{}/test_data/binance".format(os.getcwd())
        kline_base_path = "{}/test_data/binance/".format(os.getcwd())

        # for symbol in symbol_data_required.keys():
        # Get all dates between two dates
        dates = pd.date_range(start=start_date, end=end_date, freq='D').to_pydatetime().tolist()
        dates = [date.strftime("%Y-%m-%d") for date in dates]

        # Download daily data
        download_daily_trades(trading_type='spot', symbols=symbol_data_required.keys(), num_symbols=1, dates=dates,
                              start_date=start_date, end_date=end_date, folder=trades_base_path, checksum=0)

        # Iterate through intervals
        for symbol, intervals in symbol_data_required.items():
            # Download interval data
            download_daily_klines(trading_type='spot', symbols=[symbol], num_symbols=1, intervals=intervals,
                                  dates=dates, start_date=start_date, end_date=end_date, folder=kline_base_path,
                                  checksum=0)

        print("\n----------------------------------- Finished Downloading Historical Data ---------"
              "--------------------------\n")

    # ----------------------------------- Deleting Data -----------------------------------

    def delete_historical_data(self):
        """
        Deletes historical data used for the backtest
        """
        # Get path to delete
        path = "{}/test_data/binance".format(os.getcwd())

        # Delete historical data
        print("Deleting historical data files")
        shutil.rmtree(path=path)