from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
import ta
import pytz

import ta.momentum

# Variables
symbol = "ETHUSDm"
flag_entry = False
flag_side = 'LONG' # By Defaulf
point_diff_percent = 0.0007
tr_percent = 0.0025
sl_percent = 0.0025
buy_price = 0
stoploss = 0
target = 0
lot = 1.0

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

# set time zone to UTC
timezone = pytz.timezone("UTC")
last_minute = 0


now  = datetime.now(tz=timezone)

# create 'datetime' object in UTC time zone to avoid the implementation of a local time zone offset
utc_from_date = now + timedelta(days=1)

data_1minute = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, utc_from_date, 1000)

# create DataFrame out of the obtained data
data_frame = pd.DataFrame(data_1minute)
# convert time in seconds into the datetime format
data_frame['time']=pd.to_datetime(data_frame['time'], unit='s')

now = data_frame['time'].iloc[-1]
# print(f'Long Order: {symbol}')
# flag_entry = True
# flag_side = 'LONG'
# buy_price = mt5.symbol_info_tick(symbol).ask
# target = buy_price + buy_price*tr_percent
# stoploss = buy_price - buy_price*sl_percent
# request = {
#     "action": mt5.TRADE_ACTION_DEAL,
#     "symbol": symbol,
#     "volume": lot,
#     "type": mt5.ORDER_TYPE_BUY,
#     "price": buy_price,
#     "sl": stoploss,
#     "tp": target,
#     "deviation": 0,
#     "magic": 0,
#     "comment": "python script: Long",
#     "type_time": mt5.ORDER_TIME_DAY,
#     "type_filling": mt5.ORDER_FILLING_FOK,
# }

# # send a trading request
# result = mt5.order_send(request)
# # check the execution result
# if result.retcode != mt5.TRADE_RETCODE_DONE:
#     print("Order_send failed, retcode={}".format(result.retcode))
#     # request the result as a dictionary and display it element by element
#     result_dict=result._asdict()
#     for field in result_dict.keys():
#         print("   {}={}".format(field,result_dict[field]))
#         # if this is a trading request structure, display it element by element as well
#         if field=="request":
#             traderequest_dict=result_dict[field]._asdict()
#             for tradereq_filed in traderequest_dict:
#                 print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
# print("Order_send done, ", result)
# print(f"Opened Long position with POSITION_TICKET={result.order}, Target: {target}, Stoploss: {stoploss}")

print(f'Short Order: {symbol}')
flag_entry = True
flag_side = 'SHORT'
buy_price = mt5.symbol_info_tick(symbol).ask
target = buy_price - buy_price*tr_percent
stoploss = buy_price + buy_price*sl_percent
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": lot,
    "type": mt5.ORDER_TYPE_SELL,
    "price": buy_price,
    "sl": stoploss,
    "tp": target,
    "deviation": 0,
    "magic": 0,
    "comment": "python script: Short",
    "type_time": mt5.ORDER_TIME_DAY,
    "type_filling": mt5.ORDER_FILLING_FOK,
}

# send a trading request
result = mt5.order_send(request)
# check the execution result
if result.retcode != mt5.TRADE_RETCODE_DONE:
    print("Order_send failed, retcode={}".format(result.retcode))
    # request the result as a dictionary and display it element by element
    result_dict=result._asdict()
    for field in result_dict.keys():
        print("   {}={}".format(field,result_dict[field]))
        # if this is a trading request structure, display it element by element as well
        if field=="request":
            traderequest_dict=result_dict[field]._asdict()
            for tradereq_filed in traderequest_dict:
                print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
print("Order_send done, ", result)
print(f"Opened Short position with POSITION_TICKET={result.order}, Target: {target}, Stoploss: {stoploss}")
