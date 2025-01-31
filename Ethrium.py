import pytz
import ta.momentum
import pandas as pd
from time import sleep
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# Variables
symbol = "ETHUSDm"
flag_entry = False
flag_side = 'Call' # By Default
tr_percent = 0.015
sl_percent = 0.005
buy_price = 0
stoploss = 0
target = 0
lot = 1.7
position_id = 0

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()


# get open positions on XCUUSDm
print(f"Trying to fetch Min_Breakout Open Position for {symbol}..")
positions=mt5.positions_get(symbol=symbol)
for position in positions:
    position = position._asdict()
    if 'Call_Minute' == position['comment']:
        position_id = position['ticket']
        flag_side = 'Call'
        flag_entry = True
        target = position['tp']
        stoploss = position['sl']
        print(f"Successfully fetched Open Position: Side: {flag_side}, Position ID: {position_id} ..")
        break
    elif 'Put_Minute' == position['comment']:
        position_id = position['ticket']
        flag_side = 'Put'
        flag_entry = True
        target = position['sl']
        stoploss = position['tp']
        print(f"Successfully fetched Open Position: Side: {flag_side}, Position ID: {position_id} ..")
        break

if position_id == 0:
    print(f"No Open Position Found..")


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
    if flag_entry:
        if data_frame['close'].iloc[-1] >= target or data_frame['close'].iloc[-1] <= stoploss:
            print(f"Exit: {now} {flag_entry}, Side: {flag_side}, TR: {target}, Sl: {stoploss}, Ltp: {data_frame['close'].iloc[-1]}")
            position_id = 0
            flag_entry = False
            target = 0
            stoploss = 0
    if last_minute != now.time().minute:
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
        
        print(f'{symbol}: Runtime: {now} Entry: {flag_entry}, Side: {flag_side}, TR: {target}, Sl: {stoploss}, Ltp: {close}, PosID: {position_id}')

        if flag_entry:
            if (flag_side == 'Call' and ((rsi.iloc[-2] > 60 and rsi.iloc[-2] > rsi.iloc[-1]) or (rsi.iloc[-2] < 30 and rsi.iloc[-1] < 30)) ) or (flag_side == 'Put' and ((rsi.iloc[-2] < 40 and rsi.iloc[-2] < rsi.iloc[-1]) or (rsi.iloc[-2] > 70 and rsi.iloc[-1] > 70)) ):
                price=mt5.symbol_info_tick(symbol).bid
                request={
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": mt5.ORDER_TYPE_SELL if flag_side == 'Call' else mt5.ORDER_TYPE_BUY,
                    "position": position_id,
                    "price": price,
                    "deviation": 0,
                    "magic": int(datetime.now().strftime("%d%m%Y")),
                    "comment": f"Min_BrkOut: {flag_side}: Exit",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
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
                target = 0
                stoploss = 0
                flag_entry = False


        elif flag_entry == False and rsi.iloc[-1] > 30 and rsi.iloc[-2] < 30 and rsi.iloc[-3] > 30:
            print(f'Call Order: {symbol}')
            if position_id != 0:
                price=mt5.symbol_info_tick(symbol).bid
                request={
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": mt5.ORDER_TYPE_SELL if flag_side == 'Call' else mt5.ORDER_TYPE_BUY,
                    "position": position_id,
                    "price": price,
                    "deviation": 0,
                    "magic": int(datetime.now().strftime("%d%m%Y")),
                    "comment": f"Min_BrkOut: {flag_side}: Exit",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
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
                target = 0
                stoploss = 0
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
                "comment": "Call_Minute",
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
            flag_side = 'Call'
            position_id = result.order
            target = result.request.tp
            stoploss = result.request.sl
        

        elif flag_entry == False and rsi.iloc[-1] < 70 and rsi.iloc[-2] > 70 and rsi.iloc[-3] < 70:
            print(f'Put Order: {symbol}')
            if position_id != 0:
                price=mt5.symbol_info_tick(symbol).bid
                request={
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": mt5.ORDER_TYPE_SELL if flag_side == 'Call' else mt5.ORDER_TYPE_BUY,
                    "position": position_id,
                    "price": price,
                    "deviation": 0,
                    "magic": int(datetime.now().strftime("%d%m%Y")),
                    "comment": f"Min_BrkOut: {flag_side}: Exit",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
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
                target = 0
                stoploss = 0
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
                "comment": "Put_Minute",
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
            flag_side = 'Put'
            position_id = result.order
            target = result.request.sl
            stoploss = result.request.tp
