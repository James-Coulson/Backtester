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
        self.binance.start_kline_socket(symbol="BTCUSDT", callback=self.callback, interval='15m')

    def callback(self, data):
        """
        Callback used for binance

        :param data: kline
        """
        self.binance.create_order(price=43600, type_=Enums.TYPE_LMT, side=Enums.SIDE_ASK, callback=self.executed, symbol="BTCUSDT", quantity=0.00001)

        print(data)

        # print("Priniting posiitons")
        # print(self.binance.get_asset_balances())
        # print("Ending positions")

    def executed(self, data):
        """
        Callback for order execution

        :param data: exec dict
        """
        # print('Received execution')
        # print(data)


if __name__ == '__main__':
    debug = {'limit_trade_imports': False}
    backtester = Backtester(start_date='2021-11-01', end_date='2021-11-02', symbol_data_required={'BTCUSDT': ['15m', '1m'], 'ADAAUD': ['15m']}, debug=debug)
    strategy = TestStrategy(binance=backtester.get_brokers()['binance'].get_client())
    backtester.run_backtest()
    # backtester.delete_historical_data()
