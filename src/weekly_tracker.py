from datetime import datetime, timedelta
import json
from typing import Any, Dict, List
import pyotp
import pandas as pd
from pandas import json_normalize
import numpy as np
import time
from lib.shoonya_api.api_helper import ShoonyaApiPy
import logging

#enable dbug to see request and responses
logging.basicConfig(level=logging.DEBUG)

#start of our program
api = ShoonyaApiPy()

totp = pyotp.TOTP('5MI6T7L2X24K6242FEJUR7276QQ32ALG')
totp_value = totp.now()

#credentials
user    = "FA43683"
pwd     = "A@star61"
factor2 = totp_value
vc      = "FA43683_U"
app_key = "e77db609711d2c80d5b81eb4ba04534d"
imei    = "abc1234"

#make the api call
api.login(userid=user, password=pwd, twoFA=factor2, vendor_code=vc, api_secret=app_key, imei=imei)

end_date =  datetime.now().strftime('%s')
start_date = (datetime.now() - timedelta(days=371)).strftime('%s')

# stocks = ['INDUSINDBK-EQ','HDFCLIFE-EQ','EICHERMOT-EQ','SBICARD-EQ','DABUR-EQ','APOLLOHOSP-EQ','POWERGRID-EQ','DLF-EQ','AXISBANK-EQ','BAJAJFINSV-EQ','PNB-EQ', 'KOTAKBANK-EQ','ADANIENT-EQ','ZOMATO-EQ','HINDALCO-EQ','JUBLFOOD-EQ','ICICIBANK-EQ','SBIN-EQ','TATAMOTORS-EQ','ASIANPAINT-EQ', 'BAJFINANCE-EQ','MUTHOOTFIN-EQ', 'DMART-EQ','BOSCHLTD-EQ','ONGC-EQ','HDFC-EQ', 'SRF-EQ','ADANIPORTS-EQ','BANKBARODA-EQ','MARUTI-EQ','ACC-EQ', 'ITC-EQ','HDFCBANK-EQ','PAYTM-EQ','HDFCAMC-EQ', 'RELIANCE-EQ','HAVELLS-EQ','JSWSTEEL-EQ', 'SBILIFE-EQ','LICI-EQ', 'HINDUNILVR-EQ', 'BIOCON-EQ','TATACONSUM-EQ','NESTLEIND-EQ','PIDILITIND-EQ','CHOLAFIN-EQ','INDIGO-EQ','BAJAJ-AUTO-EQ','VEDL-EQ','PIIND-EQ','ADANIGREEN-EQ','TITAN-EQ','ICICIPRULI-EQ','TATASTEEL-EQ','MARICO-EQ','BRITANNIA-EQ','ZYDUSLIFE-EQ','M&M-EQ','SIEMENS-EQ','CIPLA-EQ','ULTRACEMCO-EQ','ICICIGI-EQ','UPL-EQ','TATAPOWER-EQ','GAIL-EQ','COLPAL-EQ','BHARTIARTL-EQ','MCDOWELL-N-EQ','DRREDDY-EQ','TORNTPHARM-EQ','GODREJCP-EQ','NYKAA-EQ','PGHH-EQ','AMBUJACEM-EQ','DIVISLAB-EQ','BERGEPAINT-EQ','GRASIM-EQ','COALINDIA-EQ','NAUKRI-EQ','WIPRO-EQ','IOC-EQ','SHREECEM-EQ','GLAND-EQ','LUPIN-EQ','ADANITRANS-EQ','HEROMOTOCO-EQ','LT-EQ','SUNPHARMA-EQ','SAIL-EQ','BAJAJHLDNG-EQ','BPCL-EQ','INDUSTOWER-EQ','NTPC-EQ','TCS-EQ','HCLTECH-EQ','TECHM-EQ','BANDHANBNK-EQ','INFY-EQ','LTIM-EQ']
stocks = ['ADANIGREEN-EQ']

def colour_code_candle(open, close, date) -> str:


    if open < close:
        print("issues open and close ** ", date, open, close)
        return "Green"

    return "Red"

for stock in stocks:

    ret =api.get_daily_price_series(exchange="NSE",tradingsymbol=stock,startdate=start_date, enddate=end_date)


    response_df = json_normalize([json.loads(item) for item in ret])


    # # Converting date to pandas datetime format
    response_df['Date'] = pd.to_datetime(response_df['time'])

    # Getting week number
    response_df['Week_Number'] = response_df['Date'].dt.isocalendar().week

    # Getting year. Weeknum is common across years to we need to create unique index by using year and weeknum
    response_df['Year'] = response_df['Date'].dt.isocalendar().year

    # Grouping based on required values
    df2 = response_df.groupby(['Year','Week_Number']).agg({'into':'last', 'inth':'max', 'intl':'min', 'intc':'first', 'intv':'sum', 'Date': 'last'})

    df2.rename(columns={'into': 'open', 'inth': 'high', 'intl': 'low', 'intc': 'close', 'intv': 'vol'}, inplace=True)

    # df2.loc[df2['open'] <= df2['close'], 'candle_colour'] = 'Green'
    # df2.loc[df2['open'] > df2['close'], 'candle_colour'] = 'Red'

    df2['candle_colour'] = df2.apply(lambda x: colour_code_candle(x['open'], x['close'], x['Date']), axis=1)

    df2["open"] = pd.to_numeric(df2["open"])
    df2["close"] = pd.to_numeric(df2["close"])

    df2['%'] = ( ( df2['close'] - df2['close'].shift(1) ) / df2['close'].shift()) * 100

    df2['avg_%_green'] = df2.loc[df2['candle_colour'] == "Green", '%'].mean()
    df2['avg_%_red'] = df2.loc[df2['candle_colour'] == "Red", '%'].mean()
    df2['avg_%'] = df2.loc[:, '%'].mean()

    df2.loc[(df2['%'] / df2['avg_%_green']) >= 2.0, 'leg'] = 'green_leg_out'
    df2.loc[(df2['%'] / df2['avg_%_red']) >= 2.0, 'leg'] = 'red_leg_in'

    df2['max_value'] = df2[["open", "close"]].max(axis=1).apply(np.ceil)
    df2['min_value'] = df2[["open", "close"]].min(axis=1).apply(np.floor)

    # resistance for situation 1
    df2.loc[ ( df2['max_value'] >= df2['max_value'].shift(1) ) & ( df2['max_value'].shift(1) > df2['max_value'].shift(2)) & ( df2['max_value'].shift(2) > df2['max_value'].shift(3)) & ( df2['max_value'].shift(3) > df2['max_value'].shift(4))
                & ( df2['max_value'] >= df2['max_value'].shift(-1)) & ( df2['max_value'].shift(-1) > df2['max_value'].shift(-2)) & ( df2['max_value'].shift(-2) > df2['max_value'].shift(-3)) & ( df2['max_value'].shift(-3) > df2['max_value'].shift(-4))
            , 'pivot'] = 'resistance'

    # resistance for situation 2 when pivot is just bigger than all others, TODO: added more candles
    df2.loc[ ( df2['max_value'] >= df2['max_value'].shift(1) ) & ( df2['max_value'] > df2['max_value'].shift(2)) & ( df2['max_value'] > df2['max_value'].shift(3)) & ( df2['max_value'] > df2['max_value'].shift(4)) & ( df2['max_value'] > df2['max_value'].shift(5))
                & ( df2['max_value'] >= df2['max_value'].shift(-1)) & ( df2['max_value'] > df2['max_value'].shift(-2)) & ( df2['max_value'] > df2['max_value'].shift(-3)) & ( df2['max_value'] > df2['max_value'].shift(-4)) & ( df2['max_value'] > df2['max_value'].shift(-5))
            , 'pivot'] = 'resistance'

    # support for situation 1
    df2.loc[ ( df2['min_value'] <= df2['min_value'].shift(1) ) & ( df2['min_value'].shift(1) < df2['min_value'].shift(2)) & ( df2['min_value'].shift(2) < df2['min_value'].shift(3)) & ( df2['min_value'].shift(3) < df2['min_value'].shift(4))
                & ( df2['min_value'] <= df2['min_value'].shift(-1)) & ( df2['min_value'].shift(-1) < df2['min_value'].shift(-2)) & ( df2['min_value'].shift(-2) < df2['min_value'].shift(-3)) & ( df2['min_value'].shift(-3) < df2['min_value'].shift(-4))
            , 'pivot'] = 'support'

    # support for situation 1 when pivot is just smaller than all others
    df2.loc[ ( df2['min_value'] <= df2['min_value'].shift(1) ) & ( df2['min_value'] < df2['min_value'].shift(2)) & ( df2['min_value'] < df2['min_value'].shift(3)) & ( df2['min_value'] < df2['min_value'].shift(4))
                & ( df2['min_value'] <= df2['min_value'].shift(-1)) & ( df2['min_value'] < df2['min_value'].shift(-2)) & ( df2['min_value'] < df2['min_value'].shift(-3)) & ( df2['min_value'] < df2['min_value'].shift(-4))
            , 'pivot'] = 'support'

    # define base( could be <= avg * 0.25), legin (3x) leg out then try finding pivot (pivot could be percent change before and after)

    # TODO: added more candles and more condition
    df2.loc[ (df2['leg']=='green_leg_out') &
            ((df2['pivot'].shift(1) == 'support') | (df2['pivot'].shift(2) == 'support') | (df2['pivot'].shift(3) == 'support') | (df2['pivot'].shift(4) == 'support') | (df2['pivot'].shift(5) == 'support') | (df2['pivot'].shift(6) == 'support'))
            & ((df2['pivot'].shift(1) != 'resistance') & (df2['pivot'].shift(2) != 'resistance') & (df2['pivot'].shift(3) != 'resistance') & (df2['pivot'].shift(4) != 'resistance') & (df2['pivot'].shift(5) != 'resistance') & (df2['pivot'].shift(6) != 'resistance'))
            & ((df2['leg'].shift(1) != 'red_leg_in') & (df2['leg'].shift(2) != 'red_leg_in') & (df2['leg'].shift(3) != 'red_leg_in') & (df2['leg'].shift(4) != 'red_leg_in') & (df2['leg'].shift(5) != 'red_leg_in') & (df2['leg'].shift(6) != 'red_leg_in'))
            , 'dz'] = 'Y'

    # TODO: added new condition
    df2.loc[(df2['dz'] == 'Y') & ((df2['dz'].shift(1) == 'Y') |  (df2['dz'].shift(2) == 'Y')), 'dz'] = float("NaN")

    # TODO added better prints
    def get_good_dz(achievement: List[Dict[str, Any]]) -> str:

        found = False
        # min_value, max_value, pivot, leg, dz, date
        dz_points = []
        for item in achievement:

            if item['pivot'] == 'resistance':
                dz_points.append((item['Date'], item['max_value']))

            if item['dz'] == 'Y':
                dz_points.append((item['Date'], item['dz']))

        # print(dz_points)

        for item in dz_points:

            if not item[1] == 'Y':
                continue

            # get index
            current_index = dz_points.index(item)
            previous = current_index - 1
            next = current_index + 1

            while True:
                if not isinstance(dz_points[previous][1], float):
                    previous  = previous - 1
                    continue

                break

            previous_r = dz_points[previous]

            try:
                # get the next float value only
                while True:
                    if not isinstance(dz_points[next][1], float):
                        next  = next + 1
                        continue

                    break

                next_r = dz_points[next]

            except IndexError:
                print("**** Good DZ for %s on `date`: %s ****" % (stock, item[0]))
                found = True

            if previous_r[1] < next_r[1]:
                print("**** Good DZ for %s on `date`: %s ****" % (stock, item[0]))
                found = True
            else:
                print("Not Good DZ for %s on `date`: %s" % (stock, item[0]))

        return "No Dz found for %s" % stock if not found else "Dz found for %s, please check!" % stock

    achievement = df2.to_dict('records')

    # print(get_good_dz(achievement=achievement))

    time.sleep(4)

    # print(df2[['Date','%', 'avg_%', 'avg_%_green', 'avg_%_red', 'max_value', 'pivot', 'leg', 'dz']])
    # print(df2[['Date','%', 'avg_%', 'avg_%_green', 'avg_%_red', 'max_value', 'pivot', 'leg', 'candle_colour']])
    print(df2.loc[df2['candle_colour'] == "Green", '%'], df2[['Date', 'open', 'close', 'candle_colour']])