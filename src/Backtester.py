# Standard libraries
import pandas as pd
import os
import shutil

# Importing binance download libraries
from binance_data_download.download_kline import download_daily_klines
from binance_data_download.download_trade import download_daily_trades

# Importing user-made libraries
from src._binance import BinanceBroker
from src.helper_funcs import trade_data_collation
from src.Logger import Logger


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

        :param start_date: Beginning date of the backtest (format: DD-MM-YYY)
        :param end_date: Ending date of the backtest (format: DD-MM-YYY)
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

        # Downloading required data
        self.download_data(symbol_data_required=symbol_data_required, start_data=start_date, end_date=end_date)

        # Get data for backtest
        kline_filepaths = {'BTCUSDT': './test_data/binance/data/spot/daily/klines/BTCUSDT/15m/BTCUSDT-15m-2021-11-01.zip'}
        self.kline_data = self.get_binance_data(kline_filepaths)
        print(self.kline_data['close time'])
        # Get trade data
        trade_filepaths = {'BTCUSDT': './test_data/binance/data/spot/daily/trades/BTCUSDT/BTCUSDT-trades-2021-11-01.zip'}
        self.binance_trade_data = self.get_trade_data(trade_filepaths)
        print(self.binance_trade_data)
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

    def get_binance_data(self, filepaths):
        """
        Used to get binance market data
         - For now only gets a respecified data set.

        :param filepaths: Dictionary of symbols as keys and pathname as value
        :return: Returns a pandas DataFrame of the data
        """
        # Headers for the CSV
        headers = ['open time', 'open', 'high', 'low', 'close', 'volume', 'close time', 'quote asset volume',
                   'number of trades', 'taker buy asset volume', 'taker buy quote asset volume', 'ignore']

        # Returning DataFrame
        kline_data = pd.DataFrame()
        for symbol in filepaths.keys():
            part_df = pd.read_csv(filepaths[symbol], compression='zip', names=headers)
            part_df["symbol"] = symbol
            kline_data = kline_data.append(part_df)
        return kline_data

    # -----------------------------------Getting Trade Data-----------------------------------------

    def get_trade_data(self, filenames):
        """
        Used to get trade data and collate it into 10 second intervals
        - For now only uses established filenames

        :param filenames: dictionary of ticker symbol as key and pathname as value
        :return: Returns a pandas DataFrame of the data
        """
        trade_data = pd.DataFrame()
        for filename in filenames.keys():
            # Importing data with debug features
            if 'limit_trade_imports' in self.debug and self.debug['limit_trade_imports'] is True:
                if 'limit_trade_imports_nrows' in self.debug:
                    part_data = trade_data_collation(filenames[filename], filename,
                                                     limit_rows=self.debug['limit_trade_imports'],
                                                     nrows=self.debug['limit_trade_imports_nrows'])
                else:
                    part_data = trade_data_collation(filenames[filename], filename,
                                                     limit_rows=self.debug['limit_trade_imports'])
            else:
                part_data = trade_data_collation(filenames[filename], filename)
            trade_data = trade_data.append(part_data, ignore_index=True)
        return trade_data.sort_values(by="time")

    # ----------------------------------- Main backtesting Method -----------------------------------

    def run_backtest(self):
        """
        Called to run the backtest
        """
        kline_num = 0

        # Iterates through the trade data
        for i in range(len(self.binance_trade_data)):
            # Set time
            self.time = self.binance_trade_data.iloc[i]["time"]

            # Gets and sends binance trade data to binance broker
            row = self.binance_trade_data.iloc[i]

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

    # ----------------------------------- Downloading Data -----------------------------------

    def download_data(self, symbol_data_required: dict, start_data, end_date) -> list:
        """
        Used to download data from Binance
        """
        print("\n----------------------------------- Downloading Historical Data -----------------------------------")

        trades_base_path = "{}/test_data/binance".format(os.getcwd())
        kline_base_path = "{}/test_data/binance/".format(os.getcwd())

        # for symbol in symbol_data_required.keys():
        # Get all dates between two dates
        dates = pd.date_range(start=start_data, end=end_date, freq='D').to_pydatetime().tolist()
        dates = [date.strftime("%Y-%m-%d") for date in dates]

        # Download daily data
        download_daily_trades(trading_type='spot', symbols=symbol_data_required.keys(), num_symbols=1, dates=dates,
                              start_date=start_data, end_date=end_date, folder=trades_base_path, checksum=0)

        # Iterate through intervals
        for symbol, intervals in symbol_data_required.items():
            # Download interval data
            download_daily_klines(trading_type='spot', symbols=[symbol], num_symbols=1, intervals=intervals,
                                  dates=dates, start_date=start_data, end_date=end_date, folder=kline_base_path,
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