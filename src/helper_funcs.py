from math import floor
import pandas


def trade_data_collation(filename, symbol):
    """
    Collates trade data from csv file into 10 second intervals

    :param filename: the pathname of the csv files
    :param symbol: associated symbol of trade data
    """

    df = pandas.read_csv(filename, compression='zip', header=None, sep=',', quotechar='"',
                         names=["tradeID", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])
    df["time"] = df["time"].floordiv(10000)
    mean_price = pandas.DataFrame(df.groupby(df["time"], as_index=False).price.mean())
    total_quantity = pandas.DataFrame(df.groupby(df["time"], as_index=False).qty.sum())
    merged_df = mean_price.join(total_quantity.set_index("time"), on="time", how="inner")
    merged_df["symbol"] = symbol
    return merged_df


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