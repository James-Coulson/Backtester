from math import floor
import pandas as pd
from datetime import datetime
import os


def downloaded_filepaths(type_, start_date, end_date, symbol_data_required):
    """
    Returns dictionary of downloaded data with key as filepath and value of (symbol, interval)

    :params type_: Either klines or trades, depending on the needed data
    :params start_date: The start date of the requested data
    :params end_date: The end date of the requested data
    :symbol_data_required: The symbols required for the backtest
    :return: Dictionary of downloaded data with key as filepath and value of (symbol, interval)
    """

    # Getting list of relevant dates
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = pd.date_range(start_date, end_date, freq='d')

    # Iterating over required files and adding to dictionary
    file_format = "{}/test_data/binance/data/spot/daily/{}/{}/{}-{}-{}.zip"

    # Initializing filepaths dictioanry
    filepaths = dict()

    # Generating filepaths
    for symbol in symbol_data_required.keys():
        for interval in symbol_data_required[symbol]:
            for date in date_range:
                date_format = date.strftime("%Y-%m-%d")
                if type_ == "klines":
                    filepath = file_format.format(os.getcwd(), type_, "{}/{}".format(symbol, interval), symbol, interval, date_format)
                elif type_ == "trades":
                    filepath = file_format.format(os.getcwd(), type_, symbol, symbol, type_, date_format)
                filepaths[filepath] = (symbol, interval)

    # Returns Dictionary
    return filepaths


def binance_trade_data_collation(filename, symbol, limit_rows=False, nrows=50000):
    """
    Collates trade data from csv file into 10 second intervals

    :param nrows: The maximum number of rows imported (defaults to 50000)
    :param limit_rows: If set to true the number of rows imported is limited
    :param filename: the pathname of the csv files
    :param symbol: associated symbol of trade data
    :return: Trade data DataFrame
    """
    # Read CSV file
    if limit_rows:
        df = pd.read_csv(filename, compression='zip', header=None, sep=',', quotechar='"',
                         names=["tradeID", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"],
                         nrows=nrows)
    else:
        df = pd.read_csv(filename, compression='zip', header=None, sep=',', quotechar='"',
                             names=["tradeID", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])

    # Floors time to 10 seconds and then converts back to milliseconds
    df["time"] = df["time"].floordiv(10000) * 10000

    # Grouping data and suming and averaging necessary columns
    df = df.groupby("time", as_index=False).agg({'price': 'mean', 'qty': 'sum', 'quoteQty': 'sum'})

    # Add symbol column
    df["symbol"] = symbol

    # Return DataFrame
    return df


def split_symbol(symbol: str, assets) -> tuple:
    """
    Used to split a symbol=

    :param symbol: Symbol to be split
    :param assets: Possible asset tickers
    :return: 2-tuple of asset tickers
    """
    # Iterates through possible pairs and tries to find working pair
    for i in range(len(symbol)):
        if symbol[:i] in assets and symbol[i:] in assets:
            return symbol[:i], symbol[i:]

    # If symbol can't be split throw value error
    raise ValueError("Tried to split symbol that couldn't be split: symbol={}, assets={}".format(symbol, assets))


def round_decimals_down(number:float, decimals:int=2):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return floor(number)

    factor = 10 ** decimals
    return floor(number * factor) / factor


def get_keys_above(d: dict, min_) -> dict:
    """
    Used to get keys of a dictionary that are above a given value
    :param d: Dictionary to get items from
    :param min_: Value which keys should be above
    :return: Dictionary with keys in range
    """
    # Make empty dictionary
    ret = dict()

    # Iterate through keys to get items
    for key, val in d.items():
        if int(key) >= min_:
            ret[key] = val

    # Return new dictionary
    return ret


def get_keys_below(d: dict, max_) -> dict:
    """
    Used to get keys of a dictionary that are below a given value

    :param d: Dictionary to get items from
    :param max_: Value which keys should be above
    :return: Dictionary with keys in range
    """
    # Make empty dictionary
    ret = dict()

    # Iterate through keys to get items
    for key, val in d.items():
        if int(key) <= max_:
            ret[key] = val

    # Return new dictionary
    return ret


def clamp(num, min_value, max_value):
    """
    Mathematical clamp function

    :param num: The number
    :param min_value: Minimum of clamp range
    :param max_value: Maximum of clamp range
    :return: Clamped value
    """
    return max(min(num, max_value), min_value)


def sign(num):
    """
    Mathematical sign function

    :param num: The number
    :return: sign(num)
    """
    if num > 0:
        return 1
    elif num < 0:
        return -1
    else:
        return 0
