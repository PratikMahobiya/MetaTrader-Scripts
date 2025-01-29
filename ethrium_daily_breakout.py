from datetime import datetime, timedelta, time
import MetaTrader5 as mt5
import pandas as pd
import pytz

# Variables
symbol = "ETHUSDm"
lot = 1.0
flag_side = 'Call' # By Default
flag_magic = 0
position_id = 0

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()


# get open positions on XCUUSDm
print(f"Trying to fetch Breakout Open Position for {symbol}..")
positions=mt5.positions_get(symbol=symbol)
for position in positions:
    position = position._asdict()
    if int(datetime.now().strftime("%d%m%Y")) == position['magic']:
        flag_magic = position['magic']
        position_id = position['ticket']
        flag_side = 'Call' if 'Call' in position['comment'] else 'Put'
        print(f"Successfully fetched Open Position: Magic: {flag_magic}, Position ID: {position_id} ..")
        break

if flag_magic == 0:
    print(f"No Open Position Found..")

# set time zone to UTC
timezone = pytz.timezone("UTC")

while True:
    now  = datetime.now(tz=timezone)


    if now.time() > time(hour=23, minute=30) and flag_magic not in [0, '0', None] and position_id not in [0, '0', None]:
        price=mt5.symbol_info_tick(symbol).bid
        request={
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_SELL if flag_side == 'Put' else mt5.ORDER_TYPE_BUY,
            "position": position_id,
            "price": price,
            "deviation": 0,
            "magic": int(datetime.now().strftime("%d%m%Y")),
            "comment": f"Exit : {flag_side} Daily Breakout",
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
        flag_magic = 0
        position_id = 0

    elif now.time() < time(hour=23, minute=30) and flag_magic in [0, '0', None] and position_id in [0, '0', None]:
        # create 'datetime' object in UTC time zone to avoid the implementation of a local time zone offset
        utc_from_date = now + timedelta(days=1)

        data_candle = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_D1, utc_from_date, 10)
        
        # create DataFrame out of the obtained data
        data_frame = pd.DataFrame(data_candle)
        # convert time in seconds into the datetime format
        data_frame['time']=pd.to_datetime(data_frame['time'], unit='s')

        open = data_frame['open'].iloc[-1]
        high = data_frame['high'].iloc[-1]
        low = data_frame['low'].iloc[-1]
        close = data_frame['close'].iloc[-1]
        prev_open = data_frame['open'].iloc[-2]
        prev_high = data_frame['high'].iloc[-2]
        prev_low = data_frame['low'].iloc[-2]
        prev_close = data_frame['close'].iloc[-2]
        max_high = max(data_frame['high'].iloc[-30:-1])
        min_low = min(data_frame['low'].iloc[-30:-1])


        if close > prev_high:
            print(f'Call Order: {symbol}')
            buy_price = mt5.symbol_info_tick(symbol).ask
            target = 0
            stoploss = prev_open
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": buy_price,
                "sl": stoploss,
                "tp": target,
                "deviation": 0,
                "magic": int(datetime.now().strftime("%d%m%Y")),
                "comment": "Call : Daily Breakout",
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
            flag_magic = result.magic
            position_id = result.order
        

        elif close < prev_low:
            print(f'Put Order: {symbol}')
            buy_price = mt5.symbol_info_tick(symbol).ask
            target = 0
            stoploss = prev_open
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": buy_price,
                "sl": stoploss,
                "tp": target,
                "deviation": 0,
                "magic": int(datetime.now().strftime("%d%m%Y")),
                "comment": "Put : Daily Breakout",
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
            flag_magic = result.magic
            position_id = result.order
    else:
        pass
