import pandas as pd


class Logger:
    """
    Class used to log information regarding the backtest
    """

    def __init__(self):
        """
        Initializes the logger information
        """
        self.logged_data = dict()

    def create_log(self, key: str):
        """
        Creates log of data stored within the data dictionary
        :param key: associated key of data
        """
        self.logged_data[key] = []

    def add_log_data(self, key, time, data):
        """
        Adds to log of data to log of data
        :param key: associated key of data
        :param time: time of associated data
        :param data: data to be logged
        """
        if key in self.logged_data:
            self.logged_data[key].append((time, data))
        else:
            raise ValueError("Key ({key}) does not correspond with any existing log".format(key))

    def plot_log(self, key: str):
        """Plot the relevant data"""
        df = pd.DataFrame(self.logged_data[key], columns=["time", key])
        df.plot()
