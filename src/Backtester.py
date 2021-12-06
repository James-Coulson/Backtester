# Standard libraries
from zipfile import ZipFile
import pandas as pd

# Importing user-made libraries
from _binance import BinanceBroker
from helper_funcs import trade_data_collation

class Backtester:
    """
    Class used to conduct a backtest

     - For now will only get the 15 min klines. Once binance implementation handles other methods that functionality can
       be added.
    """

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, start_date: str, end_date: str, symbols_required: list):
        """
        Initializes the brokers and the Logger

        :param start_date: Beginning date of the backtest (format: DD-MM-YYY)
        :param end_date: Ending date of the backtest (format: DD-MM-YYY)
        """
        # Saving required symbols
        self.symbols_required = symbols_required

        # Creating Brokers dictionary
        self.brokers = dict()

        # Creating brokers and adding to dictionary
        self.brokers['binance'] = BinanceBroker()

        # Get data for backtest
        self.data = self.get_binance_data()

        # Get trade data
        self.binance_trade_data = self.get_trade_data(filenames)

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

    def get_binance_data(self, kline_data_files):
        """
        Used to get binance market data
         - For now only gets a respecified data set.

        :param kline_data_files: dictionary of symbols as keys and pathname as value
        :return: Returns a pandas DataFrame of the data
        """
        # Headers for the CSV
        headers = ['open time', 'open', 'high', 'low', 'close', 'volume', 'close time', 'quote asset volume',
                   'number of trades', 'taker buy asset volume', 'taker buy quote asset volume', 'ignore']

        # Returning DataFrame
        kline_data = pd.DataFrame()
        for symbol in kline_data_files.keys():
            part_df = pd.read_csv(kline_data_files[symbol], compression='zip', names=headers)
            part_df["symbol"] = symbol
            kline_data.append(part_df)
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
            part_data = trade_data_collation(filenames[filename], filename)
            trade_data.append(part_data)
        return trade_data.sort_values(by="time")

    # ----------------------------------- Main backtesting Method -----------------------------------

    def run_backtest(self):
        """
        Called to run the backtest
        """
        kline_num = 0

        # Iterates through the trade data
        for i in range(len(self.binance_trade_data)):
            self.time = self.binance_trade_data.iloc(i)["time"]

            # Gets and sends binance trade data to binance broker
            row = self.binance_trade_data.iloc[i]
            self.send_trade_data_to_binance(row=row)

            # When trade data interval overlaps with kline data, send kline data to broker
            if self.data.iloc(kline_num)["close"] <= self.time:
                kline_row = self.data.iloc[kline_num]
                kline_num += 1

                # Send data to binance
                self.send_data_to_binance(row=kline_row)

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

# ----------------------------------- Sending Trade Data ----------------------------------------
    def send_trade_data_to_binance(self, row):
        """
        Gets input row of trade data and gives it to binance

        :param row: row of DataFrame of trade_data
        """
        trade_data = dict()
        trade_data["price"] = row["price"]
        trade_data["qty"] = row["qty"]
        self.brokers['binance'].update_trade_data(trade_data)
