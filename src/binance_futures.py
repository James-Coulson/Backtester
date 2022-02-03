# Standard library imports
from typing import Callable

# User-made imports
from src.helper_funcs import *
from src.Logger import Logger
from constants import *


# class Enums:
#     """
#     Class used to define Enums used by futures binance
#     """
#
#     # ----------------------------------- Order sides -----------------------------------
#
#     SIDE_BID = 0  # Order is a bid
#     SIDE_ASK = 1  # Order is an ask
#
#     # ----------------------------------- Order types -----------------------------------
#
#     TYPE_MKT = 2  # Order is a market order
#     TYPE_LMT = 3  # Order is a limit order
#
#     # ----------------------------------- Futures Type ----------------------------------
#
#     FUTURES_TYPE_USDM = 4 # USDM Futures type
#     FUTURES_TYPE_COINM = 5  # USDM Futures type
#
#     # ----------------------------------- Contract Type ----------------------------------
#
#     CONTRACT_TYPE_PERPETUAL = 6  # Perpetual contract type
#     CONTRACT_TYPE_QUARTERLY = 7  # Quarterly contract type


class Order:
    """
    Internal class used to store information about an order
    """

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, callback: Callable, orderID: int, clientID: int, type_, side, symbol: str, quantity, price=None):
        """
        Initialize the Order object

        :param callback: Callback method for when order is executed
        :param orderID: Client order id
        :param type_: Type of the order
        :param side: Side of order (bid/ask)
        :param symbol: Symbol of order (ie. BTCUSDT)
        :param quantity: Quantity of order (units)
        :param price: Limit price of order (only for limit orders)
        """
        self.orderID = orderID  # Order ID
        self.clientID = clientID  # Client ID of order
        self.side = side  # Side of order
        self.symbol = symbol  # Symbol of order
        self.quantity = quantity  # Quantity of order
        self.callback = callback  # Callback for the order
        self.type_ = type_  # Type of the order

        if type_ is BINANCE_TYPE_MKT:  # <- Order is a market order
            self.locked_price = None  # Price used for locked order
        elif type_ is BINANCE_TYPE_LMT:  # <- Order is a limit order
            self.lmt_price = price  # Limit price of order
        else:
            raise ValueError("Tried to make order with invalid order type: type={}".format(type_))


# ------------------------------ Margin Account Data Structure ------------------------------

class MarginAccountUSDM:
    """
    Internal class used to store information about a USD-M margin account
    """

    def __init__(self, symbol: str, size: float, entry_price: float, leverage: int, mark_price: float,
                 wallet: float,
                 main_rate: float, get_maintenance_rate: Callable):
        """
        Initializes the margin account

        :param symbol: The symbol of the margin account
        :param size: The size of the position in the margin account
        :param entry_price: The entry price of the current position in the margin account
        :param leverage: The leverage level of the current position
        :param mark_price: The current mark price of the symbol
        :param wallet: The current amount of margin in the account wallet
        :param main_rate: The current maintenance rate
        """
        self.symbol = symbol
        self.size = size
        self.entry_price = entry_price
        self.leverage = leverage
        self.mark_price = mark_price
        self.wallet = wallet
        self.main_rate = main_rate

    # Getters

    def get_maintenance_margin(self):
        """
        Calculates and returns the maintenance amount

        :return: The current maintenance amount
        """
        return self.mark_price * self.size * self.main_rate

    def get_liq_price(self):
        """
        Calculates and returns the liquidation price of the current position

        :return: The liquidation price of the current position
        """
        return (self.wallet + self.get_maintenance_margin() - self.size * self.entry_price) / \
               (abs(self.size) * self.main_rate - self.size)

    def get_pnl(self):
        """
        Calculates and returns the PnL of the margin account

        :return: The PnL
        """
        return (self.mark_price - self.entry_price) * self.size

    def get_max_removable(self):
        """
        Calculates and returns the maximum removable amount. From https://www.binance.com/en/support/faq/360038447311

        :return: The maximum removable amount
        """
        min_comp = min(self.wallet - self.get_maintenance_margin(), self.wallet + self.size *
                       (self.mark_price - self.entry_price) - self.mark_price * abs(self.size) * (
                                   1 / self.leverage))
        return max(min_comp, 0)

    def get_margin_balance(self):
        """
        Calculates and returns the margin balance

        :return: The margin balance
        """
        return self.wallet + self.get_pnl()

    # Setters

    def set_mark_price(self, mark_price: float):
        """
        Sets the new mark_price of the margin account

        :param mark_price: The new mark_price
        """
        self.mark_price = mark_price

    def set_leverage(self, leverage: int):
        """
        Attempts to change the leverage of the margin account

        :param leverage:
        :return: True if change was successful, False otherwise
        """
        if self.size != 0 and self.leverage > leverage:
            return False

        self.leverage = leverage
        return True

    # Wallet Interactions

    def add_to_wallet(self, amount):
        """
        Adds the specified amount of USDM to the wallet

        :param amount: The amount to be added
        """
        self.wallet += amount

    def remove_from_wallet(self, amount):
        """
        Attempts to remove the specified amount from the wallet

        :param amount: Amount to be removed
        """
        # Check if it is possible to remove specified amount
        if amount > self.get_max_removable():
            raise ValueError("Tried to remove more than allowable from USD-M {} wallet".format(self.symbol))

        # Remove amount
        self.wallet -= amount

    # Funding fee interactions

    def get_funding_amount(self, funding_rate: float):
        """
        Gets the funding fee for a specific funding rate

        :param funding_rate:
        :return: The funding fee
        """
        return self.size * self.mark_price * funding_rate

    def pay_funding_fee(self, funding_rate: float):
        """
        Pays/receives the funding fee

        :param funding_rate:
        """
        self.wallet += self.get_funding_amount(funding_rate)


# ----------------------------------- Binance Futures Broker -----------------------------------


class BinanceFuturesBroker:
    """
    Emulation of the Binance Futures Cryptocurrency exchange
    """

    # ----------------------------------- Exchange Constants -----------------------------------

    ASSETS = ['USDT', 'BTC', 'ADA', 'AUD']                  # List of assets that can be traded on Binance
    SYMBOLS = ['BTCUSDT', 'ADAAUD']                         # List of symbols that are available on Binance in the spot market
    COMMISSIONS = {'maker': 0.001, 'taker': 0.001}          # Dictionary for commissions
    INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '1d', '3d', '1w',
                 '1M']                                      # Intervals offered by Binance

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, _get_time: Callable, logger: Logger):
        """
        Initalizes the BinanceFuturesBroker

        :param _get_time: Callable to get current time from Backtester
        :param logger: Access to the logger object
        """
        # Access to the logger
        self.logger = logger

        # Order ID holder
        self.orderID = 0

        # Dictionary to store kline data
        self.kline_data = dict()                # { ..., symbol: { ..., interval: kline, ... }, ... }

        # Dictionary to store open sockets
        self.kline_sockets = dict()             # { ..., symbol: { ..., interval: [ ..., (clientID, callback), ... ], ... }, ... }

        # Dictionary to store updated klines
        self.kline_data_updated = dict()        # { ..., symbol: [ ..., interval, ... ], ... }

        # List to store current market orders
        self.market_orders = list()             # [ ..., order, ... ]

        # Dictionaries to store bids and asks
        self.bids = dict()
        self.asks = dict()

        # Dictionary to store current open orders
        self.orders = dict()                    # { ..., orderID: order, ... }

    # ----------------------------------- Initalizing Sockets -----------------------------------

    def start_kline_futures_socket(self, clientID: int, callback: Callable, symbol: str, interval: str, futures_type, contract_type):
        """
        Used to initialize a kline futures socket

        :param clientID: The ID of the client used to initialize
        :param callback: Callback method to send market data too
        :param symbol: Symbol to be streamed
        :param interval: Interval to be streamed
        :param futures_type: The futures type to be streamed
        :param contract_type: The contract type to be streamed
        """
        # Check if symbol is available in Binance Futures
        if symbol not in self.SYMBOLS:
            raise ValueError("Tried to stream symbol that is not available on Binance, SYMBOL={}".format(self))

        # Check interval is offered by Binance
        if interval not in self.INTERVALS:
            raise ValueError(
                "Tried to stream an interval that is not supported by Binance: interval={}".format(interval))

        # Add to streaming symbols
        if symbol not in self.kline_sockets:
            self.kline_sockets[symbol] = dict()

        # Add interval to symbol's dictionary
        if interval not in self.kline_sockets[symbol]:
            self.kline_sockets[symbol][interval] = list()

        # Add tuple to list
        self.kline_sockets[symbol][interval].append((clientID, callback))

    # ----------------------------------- Closing Sockets -----------------------------------

    def stop_kline_futures_socket(self, clientID: int, symbol: str, interval: str):
        """
        Used to close an open kline socket

        :param clientID: The client ID that made the socket
        :param symbol: The symbol of the socket
        :param interval: The interval of the socket
        """
        # Checking symbol is being streamed
        if symbol not in self.kline_sockets:
            raise ValueError("Tried to close socket of symbol that isn't being streamed")

        # Check interval is offered by Binance
        if interval not in self.INTERVALS:
            raise ValueError(
                "Tried to stream an interval that is not supported by Binance: interval={}".format(interval))

        # Get sockets for given symbol
        sockets = self.kline_sockets[symbol][interval]

        # Iterate through streaming list to find stream
        for i in range(len(sockets)):
            if sockets[i][0] == clientID:
                sockets.pop(i)
                break

    # ----------------------------------- Receiving orders -----------------------------------

    def futures_create_order(self, clientID: int, callback: Callable, symbol: str, side: int, type_: int, quantity: int,
                             price=None):
        """
        Used to create an order

        :param clientID: The ID of the client sending the order
        :param symbol: The symbol of the order
        :param side: The side of the order (BUY/SELL)
        :param type_: Order type
        :param quantity: Quantity of the order
        :param price: The limit price (limit order)
        :param callback: Callback method to receive execution dictionary
        :return: The assigned order ID
        """
        # Create order object and increment orderID counter
        order = Order(orderID=self.orderID, clientID=clientID, side=side, type_=type_, quantity=quantity, symbol=symbol,
                      callback=callback, price=price)
        self.orderID += 1

        # Market order
        if type_ is BINANCE_TYPE_MKT:
            # Add order ot market orders list
            self.market_orders.append(order)
        elif type_ is BINANCE_TYPE_LMT:
            # Add limit order to dictionaries
            if order.side is BINANCE_SIDE_BID:
                # If symbol not in bids dictionary
                if symbol not in self.bids:
                    self.bids[symbol] = dict()

                # Adds order to bid dictionary
                if order.lmt_price not in self.bids[symbol]:
                    self.bids[symbol][order.lmt_price] = [order]
                else:
                    self.bids[symbol][order.lmt_price].append(order)

        # Add to open orders dictionary
        self.orders[order.orderID] = order

        # Return orderID to order
        return order.orderID

    # ----------------------------------- Sending Kline Data -----------------------------------

    def send_market_data(self):
        """
        Called by Backtester to send new market data
        """
        # Iterate through updated symbols
        for symbol in self.kline_data_updated:
            for interval in self.kline_data_updated[symbol]:
                # Checks if symbol and interval are being streamed
                if symbol not in self.kline_sockets:
                    continue
                if interval not in self.kline_sockets[symbol]:
                    continue

                # Get sockets
                sockets = self.kline_sockets[symbol][interval]

                # Get kline data dictionary
                kline = self.kline_data[symbol][interval]

                # Use callback to send dict to strategies
                for _tuple in sockets:
                    _tuple[1](kline)

    # ----------------------------------- Updating Market Data -----------------------------------

    def update_kline_data(self, symbol: str, interval: str, kline: dict):
        """
        Called by Backtester to update kline data

        :param symbol: Symbol to be updated
        :param interval: Interval to be updated
        :param kline: Dictionary storing kline data
        """
        # Check if symbol is in self.klines
        if symbol not in self.kline_data:
            self.kline_data[symbol] = dict()

        # Store kline
        self.kline_data[symbol][interval] = kline

        # Check if symbol is in updated dictionary
        if symbol not in self.kline_data_updated:
            self.kline_data_updated[symbol] = []

        # Add updated kline to updated dictionary
        self.kline_data_updated[symbol].append(interval)
