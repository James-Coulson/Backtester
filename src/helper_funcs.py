from math import floor
import pandas as pd
from datetime import datetime


def downloaded_filepaths(type, start_date, end_date, symbol_data_required):

    """
    Returns dictionary of downloaded data with key of filepath and value of (symbol, interval)

    :params type: Either klines or trades, depending on the needed data
    :params start_date: The start date of the requested data
    :params end_date: The end date of the requested data
    :symbol_data_required: The symbols required for the backtest
    """

    # Getting list of relevant dates
    start_date = datetime.strptime(start_date, "%d/%m/%Y")
    end_date = datetime.strptime(end_date, "%d/%m/%Y")
    date_range = pd.date_range(start_date, end_date, freq='d')

    # Iterating over required files and adding to dictionary
    file_format = "./test_data/binance/data/spot/daily/{}/{}/{}/{}-{}-{}.zip"
    filepaths = dict()

    for symbol in symbol_data_required.keys():
        for interval in symbol_data_required[symbol]:
            for date in date_range:
                date_format = date.strftime("%Y-%m-%d")
                if type == "klines":
                    filepath = file_format.format(type, symbol, interval, symbol, interval, date_format)
                elif type == "trades":
                    filepath = file_format.format(type, symbol, interval, symbol, type, date_format)
                filepaths[filepath] = (symbol, interval)
    return filepaths


def trade_data_collation(filename, symbol, limit_rows=False, nrows=50000):
    """
    Collates trade data from csv file into 10 second intervals

    :param nrows: The maximum number of rows imported (defaults to 50000)
    :param limit_rows: If set to true the number of rows imported is limited
    :param filename: the pathname of the csv files
    :param symbol: associated symbol of trade data
    """
    # Read CSV file
    if limit_rows:
        df = pd.read_csv(filename, compression='zip', header=None, sep=',', quotechar='"',
                         names=["tradeID", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"],
                         nrows=nrows)
    else:
        df = pd.read_csv(filename, compression='zip', header=None, sep=',', quotechar='"',
                             names=["tradeID", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])
    print(len(df))
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
    Used to split a symbol

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


def get_keys_above(d: dict, min) -> dict:
    """
    Used to get keys of a dictionary that are above a given value
    :param d: Dictionary to get items from
    :param min: Value which keys should be above
    :return: Dictionary with keys in range
    """
    # Make empty dictionary
    ret = dict()

    # Iterate through keys to get items
    for key, val in d.items():
        if int(key) >= min:
            ret[key] = val

    # Return new dictionary
    return ret


def get_keys_below(d: dict, max) -> dict:
    """
    Used to get keys of a dictionary that are below a given value
    :param d: Dictionary to get items from
    :param max: Value which keys should be above
    :return: Dictionary with keys in range
    """
    # Make empty dictionary
    ret = dict()

    # Iterate through keys to get items
    for key, val in d.items():
        if int(key) <= max:
            ret[key] = val

    # Return new dictionary
    return ret