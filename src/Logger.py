import pandas as pd
from typing import Callable


class Logger:
    """
    Class used to log information regarding the backtest
    """

    def __init__(self, _get_time: Callable):
        """
        Initializes the logger information
        """
        self.logged_data = dict()
        self._get_time = _get_time

    def create_log(self, key: str):
        """
        Creates log of data stored within the data dictionary

        :param key: associated key of data
        """
        self.logged_data[key] = pd.DataFrame()

    def add_log_data(self, key: str, data):
        """
        Adds to log of data to log of data

        :param key: associated key of data
        :param data: data to be logged
        """
        data["time"] = self._get_time()
        if key in self.logged_data:
            self.logged_data[key].append(data)
        else:
            raise ValueError("Key ({}) does not correspond with any existing log".format(key))

    def give_log(self):
        """
        Passes the log of the data to be analysed
        :returns logged_data: dictionary of logged data
        """
        return self.logged_data

