from datetime import datetime, timedelta
import json
from typing import Any, Dict, List
import pyotp
import pandas as pd
from pandas import json_normalize
import numpy as np

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

end_date =  datetime.now()
start_date = (datetime.now() - timedelta(days=1))

ret = api.get_time_price_series(exchange='NSE', token='25', starttime=start_date, interval=60)

# ret =api.get_daily_price_series(exchange="NSE",tradingsymbol="INFY-EQ",startdate=start_date, enddate=end_date)
# print(ret)
# exit()

response_df = json_normalize(ret)

# # Converting date to pandas datetime format
response_df['Date'] = response_df['time']

df2 = response_df[::-1]
# df2.reindex(index=df2.index[::-1])

# # Getting week number
# response_df['Week_Number'] = response_df['Date'].dt.isocalendar().week

# # Getting year. Weeknum is common across years to we need to create unique index by using year and weeknum
# response_df['Year'] = response_df['Date'].dt.isocalendar().year

# # Grouping based on required values
# df2 = response_df.groupby(['Year','Week_Number']).agg({'into':'last', 'inth':'max', 'intl':'min', 'intc':'first', 'intv':'sum', 'Date': 'last'})

df2.rename(columns={'into': 'open', 'inth': 'high', 'intl': 'low', 'intc': 'close', 'intv': 'vol'}, inplace=True)

# df2.sort_values(by='time', ascending=True)

df2.loc[df2['open'] <= df2['close'], 'candle_colour'] = 'Green'
df2.loc[df2['open'] > df2['close'], 'candle_colour'] = 'Red'

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

# resistance for situation 2 when pivot is just bigger than all others
df2.loc[ ( df2['max_value'] >= df2['max_value'].shift(1) ) & ( df2['max_value'] > df2['max_value'].shift(2)) & ( df2['max_value'] > df2['max_value'].shift(3)) & ( df2['max_value'] > df2['max_value'].shift(4))
            & ( df2['max_value'] >= df2['max_value'].shift(-1)) & ( df2['max_value'] > df2['max_value'].shift(-2)) & ( df2['max_value'] > df2['max_value'].shift(-3)) & ( df2['max_value'] > df2['max_value'].shift(-4))
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

df2.loc[ (df2['leg']=='green_leg_out') &
        ((df2['pivot'].shift(1) == 'support') | (df2['pivot'].shift(2) == 'support') | (df2['pivot'].shift(3) == 'support') | (df2['pivot'].shift(4) == 'support') | (df2['pivot'].shift(5) == 'support'))
        , 'dz'] = 'Y'

df2.loc[(df2['dz'] == 'Y') & (df2['dz'].shift(1) == 'Y'), 'dz'] = float("NaN")

def get_good_dz(achievement: List[Dict[str, Any]]) -> str:

    # min_value, max_value, pivot, leg, dz, date
    dz_points = []
    for item in achievement:

        if item['pivot'] == 'resistance':
            dz_points.append((item['Date'], item['max_value']))

        if item['dz'] == 'Y':
            dz_points.append((item['Date'], item['dz']))


    for item in dz_points:

        if not item[1] == 'Y':
            continue

        # get index
        current_index = dz_points.index(item)
        previous = current_index - 1
        next = current_index + 1

        previous_r = dz_points[previous]
        next_r = dz_points[next]

        if float(previous_r[1]) < float(next_r[1]):
            return "Good DZ on `date`: %s" % item[0]

        return "Not Good DZ on `date`: %s" % item[0]

    return "No Dz found"

achievement = df2.to_dict('records')

print(get_good_dz(achievement=achievement))

# print(df2[['Date','%', 'avg_%', 'avg_%_green', 'avg_%_red', 'max_value', 'min_value', 'pivot', 'leg', 'dz']].tail(65))
# print(df2[['Date','%', 'high', 'low', 'open', 'close']].tail(65))
