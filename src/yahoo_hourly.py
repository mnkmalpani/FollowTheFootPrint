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
"ASML"
]

nasdaq100_list = ['ATVI','ADBE','ADP','ABNB','ALGN','GOOGL','GOOG','AMZN','AMD','AEP','AMGN','ADI','ANSS','AAPL','AMAT','ASML','AZN','TEAM','ADSK','BKR','BIIB','BKNG','AVGO','CDNS','CHTR','CTAS','CSCO','CTSH','CMCSA','CEG','CPRT','CSGP','COST','CRWD','CSX','DDOG','DXCM','FANG','DLTR','EBAY','EA','ENPH','EXC','FAST','FISV','FTNT','GILD','GFS','HON','IDXX','ILMN','INTC','INTU','ISRG','JD','KDP','KLAC','KHC','LRCX','LCID','LULU','MAR','MRVL','MELI','META','MCHP','MU','MSFT','MRNA','MDLZ','MNST','NFLX','NVDA','NXPI','ORLY','ODFL','PCAR','PANW','PAYX','PYPL','PDD','PEP','QCOM','REGN','RIVN','ROST','SGEN','SIRI','SBUX','SNPS','TMUS','TSLA','TXN','VRSK','VRTX','WBA','WBD','WDAY','XEL','ZM','ZS']

nifty100_list = ['INDUSINDBK.NS','HDFCLIFE.NS','EICHERMOT.NS','SBICARD.NS','DABUR.NS','APOLLOHOSP.NS','POWERGRID.NS','DLF.NS','AXISBANK.NS','BAJAJFINSV.NS','PNB.NS', 'KOTAKBANK.NS','ADANIENT.NS','ZOMATO.NS','HINDALCO.NS','JUBLFOOD.NS','ICICIBANK.NS','SBIN.NS','TATAMOTORS.NS','ASIANPAINT.NS', 'BAJFINANCE.NS','MUTHOOTFIN.NS', 'DMART.NS','BOSCHLTD.NS','ONGC.NS','HDFC.NS', 'SRF.NS','ADANIPORTS.NS','BANKBARODA.NS','MARUTI.NS','ACC.NS', 'ITC.NS','HDFCBANK.NS','PAYTM.NS','HDFCAMC.NS', 'RELIANCE.NS','HAVELLS.NS','JSWSTEEL.NS', 'SBILIFE.NS','LICI.NS', 'HINDUNILVR.NS', 'BIOCON.NS','TATACONSUM.NS','NESTLEIND.NS','PIDILITIND.NS','CHOLAFIN.NS','INDIGO.NS','BAJAJ-AUTO.NS','VEDL.NS','PIIND.NS','ADANIGREEN.NS','TITAN.NS','ICICIPRULI.NS','TATASTEEL.NS','MARICO.NS','BRITANNIA.NS','ZYDUSLIFE.NS','M&M.NS','SIEMENS.NS','CIPLA.NS','ULTRACEMCO.NS','ICICIGI.NS','UPL.NS','TATAPOWER.NS','GAIL.NS','COLPAL.NS','BHARTIARTL.NS','MCDOWELL-N.NS','DRREDDY.NS','TORNTPHARM.NS','GODREJCP.NS','NYKAA.NS','PGHH.NS','AMBUJACEM.NS','DIVISLAB.NS','BERGEPAINT.NS','GRASIM.NS','COALINDIA.NS','NAUKRI.NS','WIPRO.NS','IOC.NS','SHREECEM.NS','GLAND.NS','LUPIN.NS','ADANITRANS.NS','HEROMOTOCO.NS','LT.NS','SUNPHARMA.NS','SAIL.NS','BAJAJHLDNG.NS','BPCL.NS','INDUSTOWER.NS','NTPC.NS','TCS.NS','HCLTECH.NS','TECHM.NS','BANDHANBNK.NS','INFY.NS','LTIM.NS', 'HAL.NS']

current_date = datetime.now().strftime("%Y-%m-%d")

for stock in nifty100_list:

    current_price: DataFrame = yf.download(stock, start="2023-02-26", end=current_date,
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

    data_ohlc.loc[(data_ohlc['%'] / data_ohlc['avg_%_green']) >= 2.2, 'leg'] = 'green_leg_out'
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
    data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(4))
                & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(-4))
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
                fresh_zone_helper_list.append((item['Datetime'], item['dz'], item['low']))

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

        filtered_df = data_ohlc[data_ohlc['Datetime'] > datetime_filter]

        min_value = filtered_df['low'].loc[filtered_df['low'].idxmin()]      # Minimum in column

        if min_value > support_for_dz[2]:
            return True

        return False

    def get_fresh_zone(potential_stocks: List[Dict[str, Any]]) -> None:
        """ is_it_fresh_zone
                1. take the datetime for the support
                2. takeout the dataset that is >= datetime from above
                3. get the min value for the above filtered data set
                4. if the min value <= max value of support then false else true
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

    def get_stocks_with_follow_through(potential_stocks: List[Dict[str, Any]]) -> None:
        """
            1. take the datetime for the fresh zone
            2. takeout the dataset that is >= datetime from above
            3. Check if the next 3 candles are green
            4. if yes mark them with follow_through flag
        """

        for item in potential_stocks:

            if item['fresh'] == 'N':
                item['follow_through'] = 'N'
                continue

            # timestamp
            stock_time = item['date']

            filtered_df = data_ohlc[data_ohlc['Datetime'] >= stock_time]

            # print(filtered_df)
            # print(filtered_df['candle_colour'].shift(1).values[2])
            # print(filtered_df['candle_colour'].shift(2).values[4])
            # print(filtered_df['candle_colour'].shift(3).values[6])

            first_candle = filtered_df['candle_colour'].shift(1).values[2] if len(filtered_df['candle_colour'].shift(1).values) >= 3 else None
            second_candle = filtered_df['candle_colour'].shift(2).values[4] if len(filtered_df['candle_colour'].shift(2).values) >= 5 else None
            third_candle = filtered_df['candle_colour'].shift(3).values[6] if len(filtered_df['candle_colour'].shift(3).values) >= 7 else None

            if (first_candle == 'Green') \
                and  (second_candle == 'Green') \
                and  (third_candle == 'Green') \
                :
                item['follow_through'] = 'Y'
            else:
                item['follow_through'] = 'N'

    def is_it_base_candle(open: float, close: float, low: float, high: float) -> bool:
        """
        """

        return True if (abs(close-open)/abs(high-low))*100 <= 50.0 else False

    def get_stocks_with_base_before_follow_through(potential_stocks: List[Dict[str, Any]]) -> None:
        """
            1. Pick Follow through stocks
            2. check if the candle before is a base candle
            3. if yes, then check if it's max(open, close) is less than 1/3rd of (open+close of leg_out)
                # with above logic we are trying to make sure that the base candle is lower than legout candle
            4. if yes then it is follow_through with proper base candle.
        Args:
            potential_stocks (List[Dict[str, Any]]): _description_
        """

        for item in potential_stocks:

            if item['follow_through'] == 'N':
                continue

            # timestamp
            stock_time = item['date']

            filtered_df = data_ohlc[data_ohlc['Datetime'] <= stock_time]

            if not is_it_base_candle(open=filtered_df['open'].shift(1).values.tolist().pop(), close=filtered_df['close'].shift(1).values.tolist().pop(), low=filtered_df['low'].shift(1).values.tolist().pop(), high=filtered_df['high'].shift(1).values.tolist().pop()):
                item['follow_through_with_base'] = 'N'
                continue

            max_of_base_candle = max(filtered_df['open'].shift(1).values.tolist().pop(), filtered_df['close'].shift(1).values.tolist().pop())
            max_leg_out_candle = max(filtered_df['open'].values.tolist().pop(),filtered_df['close'].values.tolist().pop())
            min_leg_out_candle = min(filtered_df['open'].values.tolist().pop(),filtered_df['close'].values.tolist().pop())
            one_third_of_leg_out_candle = (min_leg_out_candle+(max_leg_out_candle-min_leg_out_candle)/3)

            if max_of_base_candle > one_third_of_leg_out_candle:
                item['follow_through_with_base'] = 'N'
                continue

            item['follow_through_with_base'] = 'Y'


    achievement = data_ohlc.to_dict('records')

    # get good demand zone
    get_good_dz(achievement=achievement)

    # get fresh zone
    get_fresh_zone(potential_stocks=potential_stocks)

    # get follow through
    get_stocks_with_follow_through(potential_stocks=potential_stocks)

    # get stocks with proper base candles
    get_stocks_with_base_before_follow_through(potential_stocks=potential_stocks)

    good_stocks.extend(potential_stocks)


# normalise into DF
df = json_normalize(good_stocks)

# get a csv with a follow_through
df[df['follow_through_with_base'] == 'Y'].to_csv('potential_stocks_US.csv', encoding='utf-8', index=False)