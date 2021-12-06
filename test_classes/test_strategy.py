from src._binance import Enums, BinanceClient
from src.Backtester import Backtester


class TestStrategy():
    """
    Test strategy that buys and then sells at the current price
    """
    def __init__(self, binance: BinanceClient):
        """
        Initialize the strategy

        :param binance: A BinanceBroker client
        """
        self.binance = binance
        self.binance.add_account_balance(asset="USDT", amount_added=1000000)
        self.binance.add_account_balance(asset="BTC", amount_added=1000)
        self.binance.start_kline_socket(symbol="BTCUSDT", callback=self.callback, interval=None)
        self.sent = 0
        self.received = 0

    def callback(self, data):
        """
        Callback used for binance

        :param data: kline
        """
        self.sent += 1
        self.binance.create_order(price=43600, _type=Enums.TYPE_LMT, side=Enums.SIDE_BID, callback=self.executed, symbol="BTCUSDT", quantity=0.00001)

    def executed(self, data):
        """
        Callback for order execution

        :param data: exec dict
        """
        self.received += 1
        print('Received execution')
        print(data)


if __name__ == '__main__':
    backtester = Backtester(start_date='2', end_date='2', symbols_required=['BTCUSDT'])
    strategy = TestStrategy(binance=backtester.get_brokers()['binance'].get_client())
    backtester.run_backtest()
