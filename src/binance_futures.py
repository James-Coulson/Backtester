# Standard library imports
from typing import Callable

# User-made imports
from src.helper_funcs import *


class Enums:
    """
    Class used to define Enums used by futures binance
    """

    # ----------------------------------- Order sides -----------------------------------

    SIDE_BID = 0  # Order is a bid
    SIDE_ASK = 1  # Order is an ask

    # ----------------------------------- Order types -----------------------------------

    TYPE_MKT = 2  # Order is a market order
    TYPE_LMT = 3  # Order is a limit order


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

        if type_ is Enums.TYPE_MKT:  # <- Order is a market order
            self.locked_price = None  # Price used for locked order
        elif type_ == Enums.TYPE_LMT:  # <- Order is a limit order
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