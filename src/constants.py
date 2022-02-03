"""
File contains constants used by the Backtester
"""

# ------------------------------------ BINANCE CONSTANTS ------------------------------------

# Order constants
BINANCE_SIDE_ASK = 0                        # Ask
BINANCE_SIDE_BID = 1                        # Bid
BINANCE_TYPE_MKT = 2                        # Market type order
BINANCE_TYPE_LMT = 3                        # Limit type order
BINANCE_FUTURES_TYPE_USDM = 4               # USDM Futures tyoe
BINANCE_FUTURES_TYPE_COINM = 5              # COINM Futures type
CONTRACT_TYPE_PERPETUAL = 6                 # Perpetual contract type
CONTRACT_TYPE_QUARTERLY = 7                 # Quarterly contract type

# Binance Futures Constants
BINANCE_USDM_SYMBOLS = ['BTCUSDT', 'BTCBUSD']
BINANCE_USDM_USDT_COMMISSIONS = {'maker': 0.0002, 'taker': 0.0004}
BINANCE_USDM_BUSD_COMMISSIONS = {'maker': -0.0001, 'taker': 0.00023}