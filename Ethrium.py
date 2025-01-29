from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
import ta
import pytz
from time import sleep

import ta.momentum

# Variables
symbol = "ETHUSDm"
flag_entry = False
point_diff_percent = 0.0007
tr_percent = 0.0025
sl_percent = 0.0025
buy_price = 0
stoploss = 0
target = 0
lot = 20.0
position_id = 0

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()


def SUPER_TREND(high, low, close, length, multiplier):
    # ATR
    
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis = 1, join = 'inner').max(axis = 1)
    atr = tr.ewm(length).mean()
    
    # H/L AVG AND BASIC UPPER & LOWER BAND
    
    hl_avg = (high + low) / 2
    upper_band = (hl_avg + multiplier * atr).dropna()
    lower_band = (hl_avg - multiplier * atr).dropna()
    
    # FINAL UPPER BAND
    final_bands = pd.DataFrame(columns = ['upper', 'lower'])
    final_bands.iloc[:,0] = [x for x in upper_band - upper_band]
    final_bands.iloc[:,1] = final_bands.iloc[:,0]
    for i in range(len(final_bands)):
        if i == 0:
            final_bands.iloc[i,0] = 0
        else:
            if (upper_band[i] < final_bands.iloc[i-1,0]) | (close[i-1] > final_bands.iloc[i-1,0]):
                final_bands.iloc[i,0] = upper_band[i]
            else:
                final_bands.iloc[i,0] = final_bands.iloc[i-1,0]
    
    # FINAL LOWER BAND
    
    for i in range(len(final_bands)):
        if i == 0:
            final_bands.iloc[i, 1] = 0
        else:
            if (lower_band[i] > final_bands.iloc[i-1,1]) | (close[i-1] < final_bands.iloc[i-1,1]):
                final_bands.iloc[i,1] = lower_band[i]
            else:
                final_bands.iloc[i,1] = final_bands.iloc[i-1,1]
    
    # SUPERTREND
    
    supertrend = pd.DataFrame(columns = [f'supertrend_{length}'])
    supertrend.iloc[:,0] = [x for x in final_bands['upper'] - final_bands['upper']]
    
    for i in range(len(supertrend)):
        if i == 0:
            supertrend.iloc[i, 0] = 0
        elif supertrend.iloc[i-1, 0] == final_bands.iloc[i-1, 0] and close[i] < final_bands.iloc[i, 0]:
            supertrend.iloc[i, 0] = final_bands.iloc[i, 0]
        elif supertrend.iloc[i-1, 0] == final_bands.iloc[i-1, 0] and close[i] > final_bands.iloc[i, 0]:
            supertrend.iloc[i, 0] = final_bands.iloc[i, 1]
        elif supertrend.iloc[i-1, 0] == final_bands.iloc[i-1, 1] and close[i] > final_bands.iloc[i, 1]:
            supertrend.iloc[i, 0] = final_bands.iloc[i, 1]
        elif supertrend.iloc[i-1, 0] == final_bands.iloc[i-1, 1] and close[i] < final_bands.iloc[i, 1]:
            supertrend.iloc[i, 0] = final_bands.iloc[i, 0]
    
    supertrend = supertrend.set_index(upper_band.index)
    supertrend = supertrend.dropna()[1:]

    return supertrend[f"supertrend_{length}"]


# set time zone to UTC
timezone = pytz.timezone("UTC")
last_minute = 0

while True:
    now  = datetime.now(tz=timezone)

    # create 'datetime' object in UTC time zone to avoid the implementation of a local time zone offset
    utc_from_date = now + timedelta(days=1)

    data_1minute = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, utc_from_date, 1000)
    
    # create DataFrame out of the obtained data
    data_frame = pd.DataFrame(data_1minute)
    # convert time in seconds into the datetime format
    data_frame['time']=pd.to_datetime(data_frame['time'], unit='s')
    
    now = data_frame['time'].iloc[-1]
    if last_minute != now.time().minute:
        print(f'{symbol}: Runtime: {now} Check:')
        last_minute = now.time().minute
        data_frame = data_frame[:-1]

        open = data_frame['open'].iloc[-1]
        high = data_frame['high'].iloc[-1]
        low = data_frame['low'].iloc[-1]
        close = data_frame['close'].iloc[-1]
        prev_close = data_frame['close'].iloc[-2]
        max_high = max(data_frame['high'].iloc[-30:-1])
        min_low = min(data_frame['low'].iloc[-30:-1])
        super_trend = SUPER_TREND(high=data_frame['high'], low=data_frame['low'], close=data_frame['close'], length=10, multiplier=3)
        rsi = ta.momentum.rsi(close=data_frame['close'], window=14)
        

        if (close > super_trend.iloc[-1] and prev_close < super_trend.iloc[-2]) and ( abs(data_frame['close'].iloc[-2] - data_frame['close'].iloc[-1]) < data_frame['close'].iloc[-1]*point_diff_percent ):
            print(f'Call Order: {symbol}')
            if position_id != 0:
                price=mt5.symbol_info_tick(symbol).bid
                request={
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": mt5.ORDER_TYPE_SELL,
                    "position": position_id,
                    "price": price,
                    "deviation": 0,
                    "magic": int(datetime.now().strftime("%d%m%Y")),
                    "comment": "SuperTrend: Put: Exit",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_RETURN,
                }
                # send a trading request
                result=mt5.order_send(request)
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
                print(f"Exit Opened position with POSITION_TICKET={result.order}")
                position_id = 0
                flag_entry = False
                sleep(1)
            buy_price = mt5.symbol_info_tick(symbol).ask
            target = buy_price + buy_price*tr_percent
            stoploss = buy_price - buy_price*sl_percent
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": buy_price,
                "sl": stoploss,
                "tp": target,
                "deviation": 0,
                "magic": 0,
                "comment": "SuperTrend: Call: Open",
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
            print(f"Opened Call position with POSITION_TICKET={result.order}, Target: {target}, Stoploss: {stoploss}")
            flag_entry = True
            position_id = result.order
        

        elif (close < super_trend.iloc[-1] and prev_close > super_trend.iloc[-2]) and ( abs(data_frame['close'].iloc[-2] - data_frame['close'].iloc[-1]) < data_frame['close'].iloc[-1]*point_diff_percent ):
            print(f'Put Order: {symbol}')
            if position_id != 0:
                price=mt5.symbol_info_tick(symbol).bid
                request={
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": mt5.ORDER_TYPE_BUY,
                    "position": position_id,
                    "price": price,
                    "deviation": 0,
                    "magic": int(datetime.now().strftime("%d%m%Y")),
                    "comment": "SuperTrend: Call: Exit",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_RETURN,
                }
                # send a trading request
                result=mt5.order_send(request)
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
                print(f"Exit Opened position with POSITION_TICKET={result.order}")
                position_id = 0
                flag_entry = False
                sleep(1)
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
                "comment": "SuperTrend: Put: Open",
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
            print(f"Opened Put position with POSITION_TICKET={result.order}, Target: {target}, Stoploss: {stoploss}")
            flag_entry = True
            position_id = result.order
