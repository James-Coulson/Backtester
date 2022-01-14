# Standard library imports
from typing import Callable

# User made imports
from src.helper_funcs import split_symbol, get_keys_below, get_keys_above, clamp, sign
from src.Logger import Logger


# ----------------------------------- Enums -----------------------------------


class Enums:
    """
    Class used to define Enums used by binance
    """

    # ----------------------------------- Order sides -----------------------------------

    SIDE_BID = 0  # Order is a bid
    SIDE_ASK = 1  # Order is an ask

    # ----------------------------------- Order types -----------------------------------

    TYPE_MKT = 2  # Order is a market order
    TYPE_LMT = 3  # Order is a limit order


# ----------------------------------- Order Data Structure -----------------------------------


class Order:
    """
    Internal class used to store information about an order
    """

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, callback: Callable, orderID: int, clientID: int, type_, side, symbol: str, quantity,
                 price=None):
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
        self.orderID = orderID          # Order ID
        self.clientID = clientID        # Client ID of order
        self.side = side                # Side of order
        self.symbol = symbol            # Symbol of order
        self.quantity = quantity        # Quantity of order
        self.callback = callback        # Callback for the order
        self.type_ = type_              # Type of the order

        if type_ is Enums.TYPE_MKT:     # <- Order is a market order
            self.locked_price = None    # Price used for locked order
        elif type_ == Enums.TYPE_LMT:   # <- Order is a limit order
            self.lmt_price = price      # Limit price of order
        else:
            raise ValueError("Tried to make order with invalid order type: type={}".format(type_))

    # ----------------------------------- Calculation Methods -----------------------------------

    def get_value(self, price=None):
        """
        Returns the value of the order

        :param price: If order is a market order then a price needs to be specified, other
        :return: Value of order
        """
        if self.type_ == Enums.TYPE_MKT:  # Order is a market order
            return self.quantity * price
        elif self.type_ == Enums.TYPE_LMT:  # Order is a limit order
            return self.quantity * self.lmt_price

    def set_price(self, price):
        """
        Used to set the price used to lock assets for order (only for market data)

        :param price: Price used for locked amount
        """
        self.locked_price = price

# ------------------------------ Margin Account Data Structure ------------------------------


class MarginAccountUSDM:
    """
    Internal class used to store information about a USD-M margin account
    """
    def __init__(self, symbol: str, size: float, entry_price: float, leverage: int, mark_price: float, wallet: float,
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
                       (self.mark_price - self.entry_price) - self.mark_price * abs(self.size) * self.leverage)
        return max(min_comp, 0)

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

# ----------------------------------- Binance Client -----------------------------------


class BinanceClient:
    """
    Used by a strategy to interact with the BinanceBroker
    """

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, ID: int, start_kline_socket_: Callable,
                 stop_kline_socket_: Callable,
                 start_kline_futures_socket_: Callable,
                 stop_kline_futures_socket_: Callable,
                 start_symbol_mark_price_socket_: Callable,
                 stop_symbol_mark_price_socket_: Callable,
                 get_asset_balances_: Callable,
                 add_account_balance_: Callable,
                 create_mkt_order_: Callable,
                 create_lmt_order_: Callable,
                 close_order_: Callable,
                 get_commissions_: Callable):
        """
        Used by the BinanceBroker to initialize the BinanceClient.

        :param ID: The unique identification number of the BinanceClient
        """
        # Setting ID
        self.ID = ID

        # Saving Callables
        self._start_kline_socket_ = start_kline_socket_
        self._stop_kline_socket_ = stop_kline_socket_
        self._start_kline_futures_socket_ = start_kline_futures_socket_
        self._stop_kline_futures_socket_ = stop_kline_futures_socket_
        self._start_symbol_mark_price_socket_ = start_symbol_mark_price_socket_
        self._stop_symbol_mark_price_socket_ = stop_symbol_mark_price_socket_
        self._get_asset_balances_ = get_asset_balances_
        self._add_account_balance_ = add_account_balance_
        self._create_mkt_order_ = create_mkt_order_
        self._create_lmt_order_ = create_lmt_order_
        self._close_order_ = close_order_
        self._get_commissions_ = get_commissions_

    # ----------------------------------- Starting and Stopping Sockets -----------------------------------

    def start_kline_socket(self, symbol: str, callback: Callable, interval):
        """
        Uses callback function to start kline socket

        :param symbol: Symbol to start socket
        :param callback: Callback method to receive data
        :param interval: Interval of when data is sent
        """
        self._start_kline_socket_(self.ID, symbol, callback, interval)

    def stop_kline_socket(self, symbol: str, interval: str):
        """
        Uses callback function to stop kline socket

        :param symbol: Symbol to be stopper being streamed
        """
        self._stop_kline_socket_(self.ID, symbol, interval)

    def start_kline_futures_socket(self, symbol: str, callback: Callable, interval):
        """
        Uses callback function to start futures kline socket

        :param symbol: Symbol to start socket
        :param callback: Callback method to receive data
        :param interval: Interval of when data is sent
        """
        self._start_kline_futures_socket_(self.ID, symbol, callback, interval)

    def stop_kline_futures_socket(self, symbol: str):
        """
        Uses callback function to stop futures kline socket

        :param symbol: Symbol to be stopper being streamed
        """
        self._stop_kline_futures_socket_(self.ID, symbol)

    def start_symbol_mark_price_socket(self, symbol: str, callback: Callable):
        """
        Uses callback function to start mark price socket

        :param symbol: Symbol to start socket
        :param callback: Callback method to receive data
        """
        self._start_symbol_mark_price_socket_(self.ID, symbol, callback)

    def stop_symbol_mark_price_socket(self, symbol: str):
        """
        Uses callback function to stop mark price socket

        :param symbol: Symbol to be stopper being streamed
        """
        self._stop_symbol_mark_price_socket_(self.ID, symbol)

    # ----------------------------------- Account Balance Methods -----------------------------------

    def get_asset_balances(self):
        """
        Uses callback method to get asset balances

        :return: Dictionary of asset balances
        """
        return self._get_asset_balances_(self.ID)

    def add_account_balance(self, asset: str, amount_added):
        """
        Uses callback method to add assets to account balance

        :param asset: Asset to be added
        :param amount_added: Amount to be added
        """
        self._add_account_balance_(self.ID, asset, amount_added)

    def get_commissions(self):
        """
        Uses callback to get account commissions

        :return: Dictionary of commissions
        """
        return self._get_commissions_(self.ID)

    # ----------------------------------- Order Methods -----------------------------------

    def create_order(self, type_, quantity, symbol: str, side, callback: Callable, price=None):
        """
        Uses callbacks to send order to binance

        :param callback: The callback function to be used to notify of execution
        :param type_: The type of the order (MKT, LMT, ...)
        :param quantity: The quantity wanting to purchase/sell
        :param symbol: Symbol to be traded
        :param side: The side of the order (BID/ASK)
        :param price: If LMT order define the limit price
        :return: The orderID of the trade
        """
        if type_ == Enums.TYPE_MKT:
            # Send market order
            return self._create_mkt_order_(clientID=self.ID, symbol=symbol, quantity=quantity, side=side, callback=callback)
        elif type_ == Enums.TYPE_LMT:
            # Check price is specified
            if price is None:
                raise ValueError("Tried to send a limit order but did not specify limit price")

            # Send limit order
            return self._create_lmt_order_(clientID=self.ID, symbol=symbol, quantity=quantity, side=side,
                                           callback=callback, lmt_price=price)
        else:
            # Raise ValueError if type cannot be found
            raise ValueError("Tried to send order but order type was not recognised: type={}".format(type_))

    def close_order(self, orderID: int):
        """
        Sends request to close order on exchange

        :param orderID: The ID of the order ot be closed
        """
        self._close_order_(orderID=orderID)


# ----------------------------------- Binance Broker -----------------------------------


class BinanceBroker:
    """
    Emulation of the Binance Cryptocurrency exchange.
    """

    # ----------------------------------- Exchange Constants -----------------------------------

    ASSETS = ['USDT', 'BTC', 'ADA', 'AUD']          # List of assets that can be traded on Binance
    SPOT_SYMBOLS = ['BTCUSDT', 'ADAAUD']            # List of symbols that are available on Binance in the spot market
    MARGIN_SYMBOLS = ['BTCUSDT']                    # List of symbols that are available on Binance in the margin market
    COMMISSIONS = {'maker': 0.001, 'taker': 0.001}  # Dictionary for commissions
    INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '1d', '3d', '1w',
                 '1M']                              # Intervals offered by Binance
    INTEREST_RATE = 0.0001                          # The interest rate used for the funding rate

    # ----------------------------------- Initializing -----------------------------------

    def __init__(self, _get_time: Callable, logger: Logger):
        """
        Used to initialize the BinanceBroker.
        """
        # Access to the Logger
        self.logger = logger

        # Dictionary to store kline streaming symbols
        self.kline_streaming_symbols = {'spot': dict(), 'margin': dict()}  # { 'spot': { ..., 'symbols' : { ..., 'interval' : [ ..., (ID, callback), ... ], ... }, ... }, 'margin', { ... } }

        # List to store market orders
        self.mkt_orders = []  # [ ..., order, ... ]

        # Dictionary to store kline data
        self.klines = {'spot': dict(), 'margin': dict()}  # { "spot": { ..., 'symbols' : { ..., 'interval' : kline, ... }, "margin": { ... } }

        # ID counters
        self.orderID = 0
        self.clientID = 0

        # Dictionary to store asset balances
        self.asset_balances = dict()  # { ..., clientID : { ..., 'asset' : (total_amount, locked_amount), ... }, ... }

        # Dictionaries to hold asks and bids
        self.asks = dict()  # { ..., 'symbol' : { ..., price : [ ..., order, ... ], ... }, ... }
        self.bids = dict()  # { ..., 'symbol' : { ..., price : [ ..., order, ... ], ... }, ... }

        # Initializing asks and bids
        for symbol in self.SPOT_SYMBOLS:
            self.asks[symbol] = dict()
            self.bids[symbol] = dict()

        # Dictionary that stores orderIDs and corresponding order objects (for use when deleting orders)
        self.orders = dict()  # { ..., orderID : order, ... }

        # Dictionary to store commissions for each client
        self.commissions = dict()  # { ..., clientID : { ..., 'asset' :  commission, ... }, ... }

        # Dictionary to store trade data
        self.trade_data = {'spot': dict(), 'margin': dict()}  # { "spot": { ..., 'symbol' : trade_dict, ... }, "margin": { ..., 'symbol' : trade_dict, ... } }

        # Get time callable
        self._get_time = _get_time

        # Dictionary to store intervals updated
        self.klines_updated = {'spot': dict(), 'margin': dict()}  # { 'spot': { ..., symbol : [ ..., interval, ... ], ... }, 'margin': { ... } }

        # ---- Margin Trading Variables ----

        # Dictionary to store the current funding rates
        self.funding_rates = dict()   # { ..., 'symbol': percentage, ... }

        # Integer storing the next funding fee payment time
        self.funding_fee_time = -1

        # Dictionary to store mark price kline streaming sockets
        self.mark_price_sockets = dict()    # { ..., 'symbol' : [ ..., (ID, callback), ... ], ... }

        # Dictionary to store mark price klines
        self.mark_price = dict()    # { ..., 'symbol': price, ... }

        # List to store which mark prices have been updated
        self.mark_price_updated = list()     # [ ..., symbol, ... ]

    # ----------------------------------- Obtaining Linked Client method -----------------------------------

    def get_client(self) -> BinanceClient:
        """
        Called by a Strategy to get a linked BinanceClient

        :return: Linked BinanceClient
        """
        # Create BinanceClient
        client = BinanceClient(self.clientID, start_kline_socket_=self.start_kline_socket,
                               stop_kline_socket_=self.stop_kline_socket,
                               start_kline_futures_socket_=self.start_kline_futures_socket,
                               stop_kline_futures_socket_=self.stop_kline_futures_socket,
                               get_asset_balances_=self.get_asset_balances,
                               add_account_balance_=self.add_account_balance,
                               create_mkt_order_=self.create_mkt_order,
                               create_lmt_order_=self.create_lmt_order,
                               close_order_=self.close_order,
                               get_commissions_=self.get_commissions,
                               start_symbol_mark_price_socket_=self.start_symbol_mark_price_socket,
                               stop_symbol_mark_price_socket_=self.stop_symbol_mark_price_socket)

        # Increment clientID counter
        self.clientID += 1

        # Initializing asset_balances
        self.asset_balances[client.ID] = dict()

        # Initializing commission balance
        self.commissions[client.ID] = dict()

        # Return client
        return client

    # ----------------------------------- Exchange Info methods -----------------------------------

    def get_time(self):
        """
        When called get the current time from the Backtester

        :return: Time in UNIX time
        """
        return self._get_time()

    # ----------------------------------- Account Info methods -----------------------------------

    def get_commissions(self, clientID: int):
        """
        Returns the commissions dictionary of a client

        :param clientID: The ID of the client whose commissions are returned
        :return: The corresponding commissions dictionary
        """
        # Check if client ID is in commissions
        if clientID not in self.commissions:
            raise ValueError("Tried to get commissions of clientID that doesn't exist")

        # Return commissions dictionary
        return self.commissions[clientID]

    def get_asset_balances(self, clientID: int):
        """
        Gets the asset balances for a given client ID.

        :param clientID: The clientID for the desired account details
        :return: The asset balances for a desired clientID
        """
        # Check if client ID is in asset_balances, otherwise raise a ValueError
        if clientID in self.asset_balances:
            return self.asset_balances[clientID]
        else:
            raise ValueError("Tried to get asset balances for a clientID that isn't recognised.")

    def get_assets_available(self, clientID: int, asset: str):
        """
        Used to get the available asset balance for a given client and asset.

        :param clientID: The clientId of the desired client
        :param asset: The asset name of the
        :return: Asset available for a given client and asset
        """
        # Check if asset is available on Binance
        if asset not in self.ASSETS:
            raise ValueError("Tried to get asset balance of asset that is not available on Binance")

        # Check if client ID is in asset_balances
        if clientID not in self.asset_balances:
            raise ValueError("Tried to get asset balances of client that isn't in asset_balances")

        # Return available amount of asset (= total - locked)
        return self.asset_balances[clientID][asset][0] - self.asset_balances[clientID][asset][1]

    def change_total_asset_balance(self, clientID: int, asset: str, change):
        """
        Used to change the total asset balances

        :param clientID: Client whose balance is to be changed
        :param asset: Asset to be changed
        :param change: Amount asset balance needs to be changed
        """
        # Check if asset is available on Binance
        if asset not in self.ASSETS:
            raise ValueError("Tried to get asset balance of asset that is not available on Binance")

        # Check if client ID is in asset_balances
        if clientID not in self.asset_balances:
            raise ValueError("Tried to get asset balances of client that isn't in asset_balances")

        # Check if change we cause negative asset balance
        if change < 0 and self.asset_balances[clientID][asset][0] + change < 0:
            raise ValueError("Tried to change asset balance to negative:"
                             " asset={}, total={}, change={}".format(asset, self.asset_balances[clientID][asset][0],
                                                                     change))

        # Change total asset balance
        self.asset_balances[clientID][asset][0] += change

    def change_locked_asset_balance(self, clientID: int, asset: str, change):
        """
        Used to change the locked asset balances

        :param clientID: Client whose locked balance is to be changed
        :param asset: Asset to be changed
        :param change: Amount locked asset balance needs to be changed
        """
        # Check if asset is available on Binance
        if asset not in self.ASSETS:
            raise ValueError("Tried to get asset balance of asset that is not available on Binance")

        # Check if client ID is in asset_balances
        if clientID not in self.asset_balances:
            raise ValueError("Tried to get asset balances of client that isn't in asset_balances")

        # Check if change we cause negative asset balance
        if change < 0 and self.asset_balances[clientID][asset][1] + change < 0:
            raise ValueError("Tried to change locked asset balance to negative:"
                             " asset={}, total={}, change={}".format(asset, self.asset_balances[clientID][asset][1],
                                                                     change))

        # Change locked asset balance
        self.asset_balances[clientID][asset][1] += change

    def add_account_balance(self, clientID: int, asset: str, amount_added):
        """
        Used to add assets to a client

        :param clientID: Client whose assets are being added
        :param asset: Asset to be changed
        :param amount_added: Amount of asset added
        """
        # Check if asset is available on Binance
        if asset not in self.ASSETS:
            raise ValueError("Tried to get asset balance of asset that is not available on Binance")

        # Check if client ID is in asset_balances
        if clientID not in self.asset_balances:
            raise ValueError("Tried to get asset balances of client that isn't in asset_balances")

        # Check if amount_added is positive
        if amount_added < 0:
            raise ValueError("Tried to add negative amount of asset: asset={}, amount_added={}".format(asset,
                                                                                                       amount_added))

        # If asset isn't in account then add dictionary entry
        if asset not in self.asset_balances[clientID]:
            self.asset_balances[clientID][asset] = [0, 0]

        # Add new balance
        self.asset_balances[clientID][asset][0] += amount_added

    # ----------------------------------- Streaming market data -----------------------------------

                                        # ------ Spot ------ #

    def start_kline_socket(self, clientID: int, symbol: str, callback: Callable, interval):
        """
        Called by BinanceClient to start a kline socket for spot market data

        :param callback: Method to be called to send market data
        :param clientID: Client who is initializing socket
        :param symbol: Symbol to begin streaming
        :param interval: The interval of how often market data is streamed
        """
        # Check if symbol is available on Binance
        if symbol not in self.SPOT_SYMBOLS:
            raise ValueError("Tried to stream symbol that is not available on Binance")

        # Check interval is offered by Binance
        if interval not in self.INTERVALS:
            raise ValueError(
                "Tried to stream an interval that is not supported by Binance: interval={}".format(interval))

        # Add to streaming symbol
        if symbol not in self.kline_streaming_symbols['spot']:
            self.kline_streaming_symbols['spot'][symbol] = dict()

        # If interval isn't already being streamed add to dictionary
        if interval not in self.kline_streaming_symbols['spot'][symbol]:
            self.kline_streaming_symbols['spot'][symbol][interval] = list()

        # Add tuple to list
        self.kline_streaming_symbols['spot'][symbol][interval].append((clientID, callback))

    def stop_kline_socket(self, clientID: int, symbol: str, interval: str):
        """
        Called by BinanceClient to stop a stream of spot market data

        :param interval: The interval to stop streaming
        :param clientID: Client whose stopping stream
        :param symbol: Symbol to be stopped being streamed
        """
        # Checking symbol is being streamed
        if symbol not in self.kline_streaming_symbols['spot']:
            raise ValueError("Tried to close socket of symbol that isn't being streamed")

        # Check interval is offered by Binance
        if interval not in self.INTERVALS:
            raise ValueError(
                "Tried to stream an interval that is not supported by Binance: interval={}".format(interval))

        # Get sockets for given symbol
        sockets = self.kline_streaming_symbols['spot'][symbol][interval]

        # Iterate through streaming list to find stream
        for i in range(len(sockets)):
            if sockets[i][0] == clientID:
                sockets.pop(i)
                break

                                        # ------ Margin ------ #

    def start_kline_futures_socket(self, clientID: int, symbol: str, callback: Callable, interval):
        """
        Called by BinanceClient to start futures kline socket

        :param callback: Method to be called to send market data
        :param clientID: Client who is initializing socket
        :param symbol: Symbol to begin streaming
        :param interval: The interval of how often market data is streamed
        """
        # Check if symbol is available on Binance
        if symbol not in self.MARGIN_SYMBOLS:
            raise ValueError("Tried to stream futures symbol that's not available on Binance: symbol={}".format(symbol))

        # Check if interval is offered by binance
        if interval not in self.INTERVALS:
            raise ValueError(
                "Tried to stream an interval that is not supported by Binance: interval={}".format(interval))

        # Add to streaming symbols
        if symbol not in self.kline_streaming_symbols['margin']:
            self.kline_streaming_symbols['margin'][symbol] = dict()

        # If interval isn't already being streamed add to dictionary
        if interval not in self.kline_streaming_symbols['margin'][symbol]:
            self.kline_streaming_symbols['margin'][symbol][interval] = list()

        # Add tuple to list
        self.kline_streaming_symbols['margin'][symbol][interval].append((clientID, callback))

    def stop_kline_futures_socket(self, clientID: int, symbol: str, interval: str):
        """
        Called by BinanceClient to stop a stream of futures market data

        :param interval: The interval to stop streaming
        :param clientID: Client whose stopping stream
        :param symbol: Symbol to be stopped being streamed
        """
        # Checking symbol is being streamed
        if symbol not in self.kline_streaming_symbols['margin']:
            raise ValueError("Tried to close socket of symbol that isn't being streamed")

        # Check interval is offered by Binance
        if interval not in self.INTERVALS:
            raise ValueError(
                "Tried to stream an interval that is not supported by Binance: interval={}".format(interval))

        # Get sockets for given symbol
        sockets = self.kline_streaming_symbols['margin'][symbol][interval]

        # Iterate through streaming list to find stream
        for i in range(len(sockets)):
            if sockets[i][0] == clientID:
                sockets.pop(i)
                break

                                # ------ Mark Price Streaming ------ #

    def start_symbol_mark_price_socket(self, clientID: int, symbol: str, callback: Callable):
        """
        Called by BinanceClient to create a socket to stream Mark Price

        :param clientID: Client who is initializing socket
        :param symbol: The symbol to be streamed
        :param callback: Callback method to give market data
        """
        # Check if symbol is offered by Binance
        if symbol not in self.MARGIN_SYMBOLS:
            raise ValueError("Tried to stream futures mark price for symbol that's not available on Binance: "
                             "symbol={}".format(symbol))

        # Add to streaming symbols
        if symbol not in self.mark_price_sockets:
            self.mark_price_sockets[symbol] = list()

        # Add tuple to list
        self.mark_price_sockets[symbol].append((clientID, callback))

    def stop_symbol_mark_price_socket(self, clientID: int, symbol: str):
        """
        Called by BinanceBroker to stop a stream of mark price data

        :param clientID: Client who initialized socket
        :param symbol: The symbol being streamed
        """
        # Check if symbol is offered by Binance
        if symbol not in self.MARGIN_SYMBOLS:
            raise ValueError("Tried to stream futures mark price for symbol that's not available on Binance: "
                             "symbol={}".format(symbol))

        # Get sockets for a given symbol
        sockets = self.mark_price_sockets[symbol]

        # Iterate through streaming list to find stream
        for i in range(len(sockets)):
            if sockets[i][0] == clientID:
                sockets.pop(i)
                break

                             # ------ Backtester Streaming Method ------ #

    def send_mkt_data(self):
        """
        Called by Backtester to send market data to sockets

        :param symbol: Symbol whose market data has been updated
        """
        # Iterate through updated mark price/funding rate symbols
        for symbol in self.mark_price_updated:
            # Create return dictionary
            mark_price_dict = dict()
            mark_price_dict['symbol'] = symbol

            mark_price_dict['mark price'] = self.mark_price[symbol]
            mark_price_dict['funding rate'] = self.funding_rates[symbol]

            # Get sockets
            sockets = self.mark_price_sockets[symbol]

            # Iterating to through sockets
            for _tuple in sockets:
                _tuple[1](mark_price_dict)

        self.mark_price_updated = list()

        # Iterate through updated spot symbols
        for symbol in self.klines_updated['spot']:
            # Iterate through updated intervals
            for interval in self.klines_updated['spot'][symbol]:
                # Checks if symbol and interval are being streamed
                if symbol not in self.kline_streaming_symbols['spot']:
                    continue
                if interval not in self.kline_streaming_symbols['spot'][symbol]:
                    continue

                # Get sockets
                sockets = self.kline_streaming_symbols['spot'][symbol][interval]

                # Get kline data dictionary
                mkt_data = self.klines['spot'][symbol][interval]

                # Use callback to send dict to strategies
                for _tuple in sockets:
                    _tuple[1](mkt_data)

        # Iterate through updated margin symbols
        for symbol in self.klines_updated['margin']:
            # Iterate through updated intervals
            for interval in self.klines_updated['margin'][symbol]:
                # Checks if symbol and interval are being streamed
                if symbol not in self.kline_streaming_symbols['margin']:
                    continue
                if interval not in self.kline_streaming_symbols['margin'][symbol]:
                    continue

                # Get sockets
                sockets = self.kline_streaming_symbols['margin'][symbol][interval]

                # Get kline data dictionary
                mkt_data = self.klines['margin'][symbol][interval]

                # Use callback to send dict to strategies
                for _tuple in sockets:
                    _tuple[1](mkt_data)

        # Clear self.klines_updated
        self.klines_updated = {'spot': dict(), 'margin': dict()}

    # ----------------------------------- Internal market data methods -----------------------------------

    def get_price(self, symbol: str, mkt: str):
        """
        Internal method to get the price of symbol.

        :param mkt: 'spot' for price in spot market, 'margin' for price in margin market
        :param symbol: Symbol of price that is needed
        :return: Price of symbol if market data is available and -1 otherwise
        """
        # If price in spot market is wanted
        if mkt == 'spot':
            # Symbol not on Binance
            if symbol not in self.SPOT_SYMBOLS:
                raise ValueError("Tried to get price of symbol not on Binance: symbol={}".format(symbol))

            # No market data available
            if symbol not in self.trade_data[mkt]:
                raise ValueError("Tried to get price of symbol on binance that hasn't been updated: symbol={}".format(
                    symbol))

            # Returns open price
            return self.trade_data[mkt][symbol]['price']
        elif mkt == 'margin':   # If price from marking market is wanted
            # Symbol not on Binance
            if symbol not in self.MARGIN_SYMBOLS:
                raise ValueError("Tried to get price of symbol not on Binance: symbol={}".format(symbol))

            # No market data available
            if symbol not in self.trade_data[mkt]:
                raise ValueError("Tried to get price of symbol on binance that hasn't been updated: symbol={}".format(
                    symbol))

            # Returns open price
            return self.trade_data[mkt][symbol]['price']
        else:
            raise ValueError("Tried ot get price in market that wasn't recognised: market={}".format(mkt))

    def get_quantity(self, symbol: str, mkt: str, quote=False):
        """
        Used to get the quantity traded

        :param mkt: 'spot' for price in spot market, 'margin' for price in margin market
        :param symbol: The symbol to get the data for
        :param quote: If the quantity or the quoted quantity is returned (default: False)
        :return: The quantity traded and -1 if no data is available
        """
        # If price in spot market is wanted
        if mkt == 'spot':
            # Symbol not on Binance
            if symbol not in self.SPOT_SYMBOLS:
                raise ValueError("Tried to get quantity of symbol not on Binance: symbol={}".format(symbol))

            # No market data available
            if symbol not in self.trade_data[mkt]:
                raise ValueError("Tried to get quantity of symbol on binance that hasn't been updated: symbol={}".format(
                    symbol))

            # Return quantity
            if quote is False:
                return self.trade_data[mkt][symbol]['quantity']
            else:
                return self.trade_data[mkt][symbol]['quoteQty']
        elif mkt == 'margin':  # If price from marking market is wanted
            # Symbol not on Binance
            if symbol not in self.MARGIN_SYMBOLS:
                raise ValueError("Tried to get quantity of symbol not on Binance: symbol={}".format(symbol))

            # No market data available
            if symbol not in self.trade_data[mkt]:
                raise ValueError(
                    "Tried to get quantity of symbol on binance that hasn't been updated: symbol={}".format(
                        symbol))

            # Return quantity
            if quote is False:
                return self.trade_data[mkt][symbol]['quantity']
            else:
                return self.trade_data[mkt][symbol]['quoteQty']
        else:
            raise ValueError("Tried to get quantity in market that wasn't recognised: market={}".format(mkt))

    # ----------------------------------- Order receiving -----------------------------------

    def create_mkt_order(self, clientID: int, symbol: str, quantity, side, callback: Callable) -> int:
        """
        Used to create a market order

        :param callback: Callback for when order is executed
        :param clientID: ClientID which made the order
        :param symbol: Symbol of the order
        :param quantity: Quantity of the order
        :param side: Side of the order (BID/ASK)
        :return: The orderID of the order created
        """
        # Create order object and increment orderID counter
        order = Order(orderID=self.orderID, clientID=clientID, type_=Enums.TYPE_MKT, side=side, symbol=symbol,
                      quantity=quantity, callback=callback)
        self.orderID += 1

        # Splits symbol
        assets = split_symbol(order.symbol, self.ASSETS)

        # Changing locked amount
        # - For now the case where no market data is available is ignored
        if order.side == Enums.SIDE_BID:
            self.change_locked_asset_balance(clientID=order.clientID, asset=assets[0],
                                             change=order.get_value(price=self.get_price(symbol=symbol, mkt='mkt')))
            order.set_price(price=self.get_price(symbol=symbol, mkt='mkt'))
        elif order.side == Enums.SIDE_ASK:
            self.change_locked_asset_balance(clientID=order.clientID, asset=assets[1], change=order.quantity)
        else:
            raise ValueError("Tried to create market order with invalid order side: side={}".format(order.side))

        # Add to market orders list
        self.mkt_orders.append(order)

        # Add order to orderID list
        self.orders[order.orderID] = order

        # Creating logger row
        log_order = dict(orderID=self.orderID, clientID=clientID, type_=Enums.TYPE_MKT, side=side, symbol=symbol,
                         quantity=quantity)

        # Adds order to Logger
        try:
            self.logger.add_log_data("BINANCE_ORDERS", log_order)
        except ValueError:
            self.logger.create_log("BINANCE_ORDERS")
            self.logger.add_log_data("BINANCE_ORDERS", log_order)

        # Return orderID or order
        return order.orderID

    def create_lmt_order(self, callback: Callable, clientID: int, symbol: str, quantity, side, lmt_price) -> int:
        """
        Used to create a limit order

        :param callback: Callback for when order is executed
        :param clientID: ClientID which made the order
        :param symbol: Symbol of the order
        :param quantity: Quantity of the order
        :param side: Side of the order (BID/ASK)
        :param lmt_price: The limit price of the order
        :return: The orderID of the order created
        """
        # Create order object and increment orderID counter
        order = Order(orderID=self.orderID, clientID=clientID, type_=Enums.TYPE_LMT, side=side, symbol=symbol,
                      quantity=quantity, price=lmt_price, callback=callback)
        self.orderID += 1

        # Splits symbol
        assets = split_symbol(order.symbol, self.ASSETS)

        # Changing locked amount
        # - For now the case where no market data is available is ignored
        if order.side == Enums.SIDE_BID:
            self.change_locked_asset_balance(clientID=order.clientID, asset=assets[0], change=order.get_value())
        elif order.side == Enums.SIDE_ASK:
            self.change_locked_asset_balance(clientID=order.clientID, asset=assets[1], change=order.quantity)
        else:
            raise ValueError("Tried to create market order with invalid order side: side={}".format(order.side))

        # Add limit order to dictionaries
        if order.side == Enums.SIDE_BID:
            # If symbol not in bids dictionary add it
            if symbol not in self.bids:
                self.bids[symbol] = dict()

            # Adds order to bid dictionary
            if order.lmt_price in self.bids[symbol]:
                self.bids[symbol][order.lmt_price].append(order)
            else:
                self.bids[symbol][order.lmt_price] = [order]
        elif order.side == Enums.SIDE_ASK:
            # If symbol not in asks dictionary add it
            if symbol not in self.asks:
                self.asks[symbol] = dict()

            # Adds order to ask dictionary
            if order.lmt_price in self.asks[symbol]:
                self.asks[symbol][order.lmt_price].append(order)
            else:
                self.asks[symbol][order.lmt_price] = [order]

        # Add order to orderID list
        self.orders[order.orderID] = order

        # Create logger row
        log_order = dict(orderID=self.orderID, clientID=clientID, type_=Enums.TYPE_LMT, side=side, symbol=symbol,
                         quantity=quantity)

        # Adds order to Logger
        try:
            self.logger.add_log_data("BINANCE_ORDERS", log_order)
        except ValueError:
            self.logger.create_log("BINANCE_ORDERS")
            self.logger.add_log_data("BINANCE_ORDERS", log_order)

        # Return orderID or order
        return order.orderID

    # ----------------------------------- Order Removing -----------------------------------

    def close_order(self, orderID: int):
        """
        External method called by BinanceClient to close an order

        :param orderID: The ID of the order to be closed
        """
        # Check if orderID exists
        if orderID not in self.orders:
            raise ValueError("Tried to remove order that doesn't exist")

        # Get order
        order = self.orders[orderID]

        # Remove order
        self.remove_order(order)

    def remove_order(self, order: Order):
        """
        Internal method to remove an order

        :param order: Order to be removed
        """
        if order.type_ == Enums.TYPE_MKT:
            # Order is a market order
            for i in range(len(self.mkt_orders)):
                # If order is found remove it and return
                if self.mkt_orders[i].orderID == order.orderID:
                    self.mkt_orders.pop(i)
                    return
        elif order.type_ == Enums.TYPE_LMT:
            # Order is a limit order
            if order.side == Enums.SIDE_BID:
                # Iterate through bids to find order
                for i in range(len(self.bids[order.symbol][order.lmt_price])):
                    # If order is found remove it and return
                    if self.bids[order.symbol][order.lmt_price][i].orderID == order.orderID:
                        self.bids[order.symbol][order.lmt_price].pop(i)
                        return
            elif order.side == Enums.SIDE_ASK:
                # Iterate through asks to find order
                for i in range(len(self.asks[order.symbol][order.lmt_price])):
                    # If order is found remove it and return
                    if self.asks[order.symbol][order.lmt_price][i].orderID == order.orderID:
                        self.asks[order.symbol][order.lmt_price].pop(i)
                        return

        # Remove order from orders list
        self.orders.pop(order.orderID)

    # ----------------------------------- Order Execution -----------------------------------

    def exec_order(self, order: Order, price, commission):
        """
        Used to execute an order

        :param commission: The commission for the order
        :param order: Order to be executed
        :param price: Price at which the order is executed
        """
        # Adjusting price for slippage
        price = self.calc_slippage(price=price, symbol=order.symbol)

        # Create execution dictionary
        execution = dict()
        execution['price'] = price
        execution['quantity'] = order.quantity
        execution['orderID'] = order.orderID
        execution['symbol'] = order.symbol
        execution['side'] = order.side
        execution['commission'] = commission

        # Get assets involved
        assets = split_symbol(order.symbol, self.ASSETS)

        # Change account balances
        if order.side == Enums.SIDE_BID:
            # Decrease locked amount by order value
            if order.type_ == Enums.TYPE_MKT:
                self.change_locked_asset_balance(clientID=order.clientID, asset=assets[0],
                                                 change=-order.get_value(price=order.locked_price))
            else:
                self.change_locked_asset_balance(clientID=order.clientID, asset=assets[0], change=-order.get_value())
            # Decrease sold asset amount
            self.change_total_asset_balance(clientID=order.clientID, asset=assets[0], change=-(order.quantity * price))
            # Increase purchased asset amount
            self.change_total_asset_balance(clientID=order.clientID, asset=assets[1], change=order.quantity)
        else:
            # Decrease locked amount by order value
            self.change_locked_asset_balance(clientID=order.clientID, asset=assets[1], change=-order.quantity)
            # Decrease sold asset amount
            self.change_total_asset_balance(clientID=order.clientID, asset=assets[1], change=-order.quantity)
            # Increase purchased asset amount
            self.change_total_asset_balance(clientID=order.clientID, asset=assets[0], change=(order.quantity * price))

        # Add commissions
        self.add_commission(clientID=order.clientID, asset=assets[0], commission=commission)

        # Log order execution within logger
        try:
            self.logger.add_log_data("BINANCE_EXORDERS", execution)
        except ValueError:
            self.logger.create_log("BINANCE_EXORDERS")
            self.logger.add_log_data("BINANCE_EXORDERS", execution)

        # Execute callback function
        order.callback(execution)

    # ----------------------------------- Slippage Calculation -----------------------------------

    def calc_slippage(self, price, symbol: str):
        """
        Used to change the execution price to take into account slippage. Only takes into account slippage
        caused by large order volumes.
         - For now it does not do anything as orderbook data will be needed to determine slippage.

        :param price: The unadjusted execution price
        :param symbol: The symbol of the order being executed
        :return: The adjusted execution price
        """
        return price

    # ----------------------------------- Commission Methods -----------------------------------

    def calc_commission(self, order, price, maker=True):
        """
        Used to calculate the commission for a given order

        :param order: The order to calculate the commission of
        :param price: The execution price
        :param maker: If the order is a maker or a taker
        :return: The commission price
        """
        # Get commission rate
        if maker:
            rate = self.COMMISSIONS['maker']
        else:
            rate = self.COMMISSIONS['taker']

        # Get order value
        if order.type_ == Enums.TYPE_MKT:
            # Get value of order
            value = order.get_value(price=price)
        elif order.type_ == Enums.TYPE_LMT:
            # Get value of order
            value = order.quantity * price
        else:
            raise ValueError("Tried to calculate commission of order with unrecognised order type")

        # Return commission
        return value * rate

    def add_commission(self, clientID: int, asset: str, commission):
        """
        Logs the commission paid for an order

        :param clientID: The client who is paying commission
        :param asset: The asset that the commission is paid in
        :param commission: The commission amount
        """
        # Check if asset exists
        if asset not in self.ASSETS:
            raise ValueError("Tried to add commission of asset that isn't traded on Binance")

        # Add commissions to dictionary
        if asset not in self.commissions[clientID]:
            self.commissions[clientID][asset] = commission
        else:
            self.commissions[clientID][asset] += commission

    # -----------------------------------------------------------------------------------------------
    # ----------------------------------- Backtester interactions -----------------------------------
    # -----------------------------------------------------------------------------------------------

    # ----------------------------------- Order checking -----------------------------------

    def check_orders(self, symbol: str, mkt: str):
        """
        Called by the backtester to check orders

        :param mkt: Whether the "spot" or "margin" market orders are checked
        :param symbol: Symbol that was most recently updated
        """
        # Get price of symbol
        price = self.get_price(symbol, mkt=mkt)

        # Get valid bids and asks
        valid_asks = None
        if symbol in self.asks:
            valid_asks = get_keys_below(self.asks[symbol], price)

        valid_bids = None
        if symbol in self.bids:
            valid_bids = get_keys_above(self.bids[symbol], price)

        # Execute valid bids and asks
        if valid_bids is not None:
            for orders in valid_bids.values():
                for order in orders:
                    # Get commission
                    comm = self.calc_commission(order=order, price=price, maker=True)

                    # Execute order
                    self.exec_order(order=order, price=price, commission=comm)

                    # Remove order
                    self.remove_order(order=order)

        if valid_asks is not None:
            for orders in valid_asks.values():
                for order in orders:
                    # Get commission
                    comm = self.calc_commission(order=order, price=price, maker=True)

                    # Execute order
                    self.exec_order(order=order, price=price, commission=comm)

                    # Remove order
                    self.remove_order(order=order)

        # Execute market orders
        for order in self.mkt_orders:
            # Get commission
            comm = self.calc_commission(order=order, price=price, maker=False)

            # Execute order
            self.exec_order(order=order, price=price, commission=comm)

        # Create logger row
        asset_balance_log = dict()
        for client in self.asset_balances:
            for asset in self.asset_balances[client]:
                asset_balance_log[asset] = self.asset_balances[client][asset][0]

        # Log asset balances
        try:
            self.logger.add_log_data("ASSETS", asset_balance_log)
        except ValueError:
            self.logger.create_log("ASSETS")
            self.logger.add_log_data("ASSETS", asset_balance_log)

        # Clear market orders
        self.mkt_orders = []

    # ----------------------------------- Updating market data -----------------------------------

    def update_trade_data(self, trade_data: dict, mkt: str):
        """
        Called by Backtester

        :param mkt: Whether the market is "spot" or "margin"
        :param trade_data: The trade dictionary
        """
        self.trade_data[mkt][trade_data['symbol']] = trade_data

    def update_klines(self, symbol: str, interval: str, kline: dict, mkt: str):
        """
        Called by Backtester to update the market data for a given symbol

        :param interval: The interval being updated
        :param symbol: Symbol whose market data is being updated
        :param kline: Dictionary of updated market data
        :param mkt: Whether the market is "spot" or "margin"
        """
        # Check if symbol is in self.klines
        if symbol not in self.klines[mkt]:
            self.klines[mkt][symbol] = dict()

        # Store kline
        self.klines[mkt][symbol][interval] = kline

        # Check if symbol is in updated dictionary
        if symbol not in self.klines_updated[mkt]:
            self.klines_updated[mkt][symbol] = []

        # Add updated kline to updated dictionary
        self.klines_updated[mkt][symbol].append(interval)

    def update_mark_price(self, symbol: str, price):
        """
        Called by Backtester to update a mark price

        :param symbol: Symbol whose market data is being updated
        :param price: Most recent mark price
        """
        # Store kline
        self.mark_price[symbol] = price

        # Check if symbol is in updated dictionary
        if symbol in self.mark_price_updated:
            return

        # Add updated kline to updated dictionary
        self.mark_price_updated.append(symbol)

    def update_funding_rate(self, symbol: str, premium_rate):
        """
        Called by the Backtester to update the funding rate of a specific symbol

        :param symbol: The symbol whose funding rate is being updated
        :param premium_rate: The new premium rate
        """
        # Update new funding rate
        self.funding_rates[symbol] = round(premium_rate + clamp(self.INTEREST_RATE - premium_rate, min_value=-0.0005, max_value=0.0005), 8)

        # Check if symbol is in updated dictionary
        if symbol in self.mark_price_updated:
            return

        # Add updated kline to updated dictionary
        self.mark_price_updated.append(symbol)
