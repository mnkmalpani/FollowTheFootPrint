import json
import yfinance as yf
import pandas as pd
from datetime import date, datetime, timedelta
import time
import numpy as np
from typing import List, Dict, Any, Tuple
from pandas import DataFrame, json_normalize

good_stocks = []

nifty50_list =[
"ITC.NS"
]

nasdaq100_list = ['ATVI','ADBE','ADP','ABNB','ALGN','GOOGL','GOOG','AMZN','AMD','AEP','AMGN','ADI','ANSS','AAPL','AMAT','ASML','AZN','TEAM','ADSK','BKR','BIIB','BKNG','AVGO','CDNS','CHTR','CTAS','CSCO','CTSH','CMCSA','CEG','CPRT','CSGP','COST','CRWD','CSX','DDOG','DXCM','FANG','DLTR','EBAY','EA','ENPH','EXC','FAST','FISV','FTNT','GILD','GFS','HON','IDXX','ILMN','INTC','INTU','ISRG','JD','KDP','KLAC','KHC','LRCX','LCID','LULU','MAR','MRVL','MELI','META','MCHP','MU','MSFT','MRNA','MDLZ','MNST','NFLX','NVDA','NXPI','ORLY','ODFL','PCAR','PANW','PAYX','PYPL','PDD','PEP','QCOM','REGN','RIVN','ROST','SGEN','SIRI','SBUX','SNPS','TMUS','TSLA','TXN','VRSK','VRTX','WBA','WBD','WDAY','XEL','ZM','ZS']

nifty100_list = ['INDUSINDBK.NS','HDFCLIFE.NS','EICHERMOT.NS','SBICARD.NS','DABUR.NS','APOLLOHOSP.NS','POWERGRID.NS','DLF.NS','AXISBANK.NS','BAJAJFINSV.NS','PNB.NS', 'KOTAKBANK.NS','ADANIENT.NS','ZOMATO.NS','HINDALCO.NS','JUBLFOOD.NS','ICICIBANK.NS','SBIN.NS','TATAMOTORS.NS','ASIANPAINT.NS', 'BAJFINANCE.NS','MUTHOOTFIN.NS', 'DMART.NS','BOSCHLTD.NS','ONGC.NS','HDFC.NS', 'SRF.NS','ADANIPORTS.NS','BANKBARODA.NS','MARUTI.NS','ACC.NS', 'ITC.NS','HDFCBANK.NS','PAYTM.NS','HDFCAMC.NS', 'RELIANCE.NS','HAVELLS.NS','JSWSTEEL.NS', 'SBILIFE.NS','LICI.NS', 'HINDUNILVR.NS', 'BIOCON.NS','TATACONSUM.NS','NESTLEIND.NS','PIDILITIND.NS','CHOLAFIN.NS','INDIGO.NS','BAJAJ-AUTO.NS','VEDL.NS','PIIND.NS','ADANIGREEN.NS','TITAN.NS','ICICIPRULI.NS','TATASTEEL.NS','MARICO.NS','BRITANNIA.NS','ZYDUSLIFE.NS','M&M.NS','SIEMENS.NS','CIPLA.NS','ULTRACEMCO.NS','ICICIGI.NS','UPL.NS','TATAPOWER.NS','GAIL.NS','COLPAL.NS','BHARTIARTL.NS','MCDOWELL-N.NS','DRREDDY.NS','TORNTPHARM.NS','GODREJCP.NS','NYKAA.NS','PGHH.NS','AMBUJACEM.NS','DIVISLAB.NS','BERGEPAINT.NS','GRASIM.NS','COALINDIA.NS','NAUKRI.NS','WIPRO.NS','IOC.NS','SHREECEM.NS','GLAND.NS','LUPIN.NS','ADANITRANS.NS','HEROMOTOCO.NS','LT.NS','SUNPHARMA.NS','SAIL.NS','BAJAJHLDNG.NS','BPCL.NS','INDUSTOWER.NS','NTPC.NS','TCS.NS','HCLTECH.NS','TECHM.NS','BANDHANBNK.NS','INFY.NS','LTIM.NS']

for stock in nasdaq100_list:

    current_price: DataFrame = yf.download(stock, start="2023-02-26", end="2023-04-26",
                            interval="1h", rounding=True)

    # current_price["Symbol"] = i # Adding column-Symbol to DataFrame- current_price
    # data_list.append(current_price)

    # data_list = pd.concat(data_list) # Concat columns and Convert to DataFrame

    data_ohlc = current_price.reset_index() # Resetting the index column

    data_ohlc = data_ohlc[data_ohlc.isna().any(axis=1) == False] # Removing null records

    data_ohlc.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Vol': 'vol'}, inplace=True)

    data_ohlc.loc[data_ohlc['open'] <= data_ohlc['close'], 'candle_colour'] = 'Green'
    data_ohlc.loc[data_ohlc['open'] > data_ohlc['close'], 'candle_colour'] = 'Red'

    data_ohlc["open"] = pd.to_numeric(data_ohlc["open"])
    data_ohlc["close"] = pd.to_numeric(data_ohlc["close"])

    data_ohlc['%'] = ( ( data_ohlc['close'] - data_ohlc['close'].shift(1) ) / data_ohlc['close'].shift()) * 100

    data_ohlc['avg_%_green'] = data_ohlc.loc[data_ohlc['candle_colour'] == "Green", '%'].mean()
    data_ohlc['avg_%_red'] = data_ohlc.loc[data_ohlc['candle_colour'] == "Red", '%'].mean()
    data_ohlc['avg_%'] = data_ohlc.loc[:, '%'].mean()

    data_ohlc.loc[(data_ohlc['%'] / data_ohlc['avg_%_green']) >= 2.0, 'leg'] = 'green_leg_out'
    data_ohlc.loc[(data_ohlc['%'] / data_ohlc['avg_%_red']) >= 2.0, 'leg'] = 'red_leg_in'

    data_ohlc['max_value'] = data_ohlc[["open", "close"]].max(axis=1).apply(np.ceil)
    data_ohlc['min_value'] = data_ohlc[["open", "close"]].min(axis=1).apply(np.floor)

    # resistance for situation 1
    data_ohlc.loc[ ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(1) ) & ( data_ohlc['max_value'].shift(1) > data_ohlc['max_value'].shift(2)) & ( data_ohlc['max_value'].shift(2) > data_ohlc['max_value'].shift(3)) & ( data_ohlc['max_value'].shift(3) > data_ohlc['max_value'].shift(4))
                & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-1)) & ( data_ohlc['max_value'].shift(-1) > data_ohlc['max_value'].shift(-2)) & ( data_ohlc['max_value'].shift(-2) > data_ohlc['max_value'].shift(-3)) & ( data_ohlc['max_value'].shift(-3) > data_ohlc['max_value'].shift(-4))
            , 'pivot'] = 'resistance'

    # resistance for situation 2 when pivot is just bigger than all others, TODO: added more candles
    data_ohlc.loc[ ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(1) ) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(2)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(3)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(4)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(5))
                & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-1)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-2)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-3)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-4)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-5))
            , 'pivot'] = 'resistance'

    # support for situation 1
    data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'].shift(1) < data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'].shift(2) < data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'].shift(3) < data_ohlc['min_value'].shift(4))
                & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'].shift(-1) < data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'].shift(-2) < data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'].shift(-3) < data_ohlc['min_value'].shift(-4))
            , 'pivot'] = 'support'

    # support for situation 1 when pivot is just smaller than all others
    data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(4))
                & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(-4))
            , 'pivot'] = 'support'

    # define base( could be <= avg * 0.25), legin (3x) leg out then try finding pivot (pivot could be percent change before and after)

    # TODO: added more candles and more condition
    data_ohlc.loc[ (data_ohlc['leg']=='green_leg_out') &
            ((data_ohlc['pivot'].shift(1) == 'support') | (data_ohlc['pivot'].shift(2) == 'support') | (data_ohlc['pivot'].shift(3) == 'support') | (data_ohlc['pivot'].shift(4) == 'support') | (data_ohlc['pivot'].shift(5) == 'support') | (data_ohlc['pivot'].shift(6) == 'support'))
            & ((data_ohlc['pivot'].shift(1) != 'resistance') & (data_ohlc['pivot'].shift(2) != 'resistance') & (data_ohlc['pivot'].shift(3) != 'resistance') & (data_ohlc['pivot'].shift(4) != 'resistance') & (data_ohlc['pivot'].shift(5) != 'resistance') & (data_ohlc['pivot'].shift(6) != 'resistance'))
            & ((data_ohlc['leg'].shift(1) != 'red_leg_in') & (data_ohlc['leg'].shift(2) != 'red_leg_in') & (data_ohlc['leg'].shift(3) != 'red_leg_in') & (data_ohlc['leg'].shift(4) != 'red_leg_in') & (data_ohlc['leg'].shift(5) != 'red_leg_in') & (data_ohlc['leg'].shift(6) != 'red_leg_in'))
            , 'dz'] = 'Y'

    # TODO: added new condition
    data_ohlc.loc[(data_ohlc['dz'] == 'Y') & ((data_ohlc['dz'].shift(1) == 'Y') |  (data_ohlc['dz'].shift(2) == 'Y')), 'dz'] = float("NaN")

    fresh_zone_helper_list = []
    potential_stocks = []

    # TODO added better prints
    # TODO: added exceptional handling
    def get_good_dz(achievement: List[Dict[str, Any]]) -> str:

        found = False
        # min_value, max_value, pivot, leg, dz, date
        dz_points = []
        for item in achievement:

            if item['pivot'] == 'resistance':
                dz_points.append((item['Datetime'], item['max_value']))

            # if item['pivot'] == 'support':
            #     fresh_zone_helper_list.append((item['Datetime'], item['max_value'], 'support'))

            if item['dz'] == 'Y':
                dz_points.append((item['Datetime'], item['dz']))
                fresh_zone_helper_list.append((item['Datetime'], item['dz'], item['min_value']))

        # print(dz_points)

        for item in dz_points:

            if not item[1] == 'Y':
                continue

            # get index
            current_index = dz_points.index(item)
            previous = current_index - 1
            next = current_index + 1

            try:
                while True:
                    if not isinstance(dz_points[previous][1], float):
                        previous  = previous - 1
                        continue

                    break

                previous_r = dz_points[previous]
            except IndexError:
                previous_r = ("", 0.0)

            try:
                # get the next float value only
                while True:
                    if not isinstance(dz_points[next][1], float):
                        next  = next + 1
                        continue

                    break

                next_r = dz_points[next]

            except IndexError:
                next_r = ("", float("inf"))

            if previous_r[1] < next_r[1]:
                # print("**** Good DZ for %s on `date`: %s ****" % (stock, item[0]))
                potential_stocks.append(
                    {
                        "stock": stock,
                        "date": item[0],
                    }
                )
                found = True
            else:
                print("Not Good DZ for %s on `date`: %s" % (stock, item[0]))

        # return "No Dz found for %s" % stock if not found else "Dz found for %s, please check!" % stock
        return "Analysis Done!"

    def is_it_fresh_zone(support_for_dz: Tuple[str, str, str]) -> bool:
        """_summary_
        """

        datetime_filter = support_for_dz[0]

        filtered_df = data_ohlc[data_ohlc['Datetime'] >= datetime_filter]

        min_value = filtered_df['low'].loc[filtered_df['low'].idxmin()]      # Minimum in column

        if min_value > support_for_dz[2]:
            return True

        return False

    def get_fresh_zone(potential_stocks: List[Dict[str, Any]]) -> None:
        """_summary_
        """

        for item in potential_stocks:

            # timestamp
            stock_time = item['date']

            for record in fresh_zone_helper_list:

                if record[0] != stock_time:
                    continue

                if is_it_fresh_zone(record):
                    item['fresh'] = 'Y'
                else:
                    item['fresh'] = 'N'
                break

    achievement = data_ohlc.to_dict('records')

    get_good_dz(achievement=achievement)
    # print(get_good_dz(achievement=achievement))

    get_fresh_zone(potential_stocks=potential_stocks)

    good_stocks.extend(potential_stocks)


df = json_normalize(good_stocks)
df[df['fresh'] == 'Y'].to_csv('potential_stocks_US.csv', encoding='utf-8', index=False)



# is_it_fresh_zone
# 1. take the datetime for the support
# 2. takeout the dataset that is >= datetime from above
# 3. get the min value for the above filtered data set
# 4. if the min value <= max value of support then false else true