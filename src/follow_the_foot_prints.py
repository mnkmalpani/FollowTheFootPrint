from logging import Logger
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict, Any, Tuple
from pandas import DataFrame, json_normalize


class IntervalRunNotPossibleException(Exception):
    """_summary_
    """

class UnknownIntervalException(Exception):
    """_summary_
    """

class FollowTheFootPrints:

    def __init__(self, time_delta_days: int, index: str="nifty100", interval: str="1h") -> None:

        self.nasdaq100_list = ['ATVI','ADBE','ADP','ABNB','ALGN','GOOGL','GOOG','AMZN','AMD','AEP','AMGN','ADI','ANSS','AAPL','AMAT','ASML','AZN','TEAM','ADSK','BKR','BIIB','BKNG','AVGO','CDNS','CHTR','CTAS','CSCO','CTSH','CMCSA','CEG','CPRT','CSGP','COST','CRWD','CSX','DDOG','DXCM','FANG','DLTR','EBAY','EA','ENPH','EXC','FAST','FISV','FTNT','GILD','GFS','HON','IDXX','ILMN','INTC','INTU','ISRG','JD','KDP','KLAC','KHC','LRCX','LCID','LULU','MAR','MRVL','MELI','META','MCHP','MU','MSFT','MRNA','MDLZ','MNST','NFLX','NVDA','NXPI','ORLY','ODFL','PCAR','PANW','PAYX','PYPL','PDD','PEP','QCOM','REGN','RIVN','ROST','SGEN','SIRI','SBUX','SNPS','TMUS','TSLA','TXN','VRSK','VRTX','WBA','WBD','WDAY','XEL','ZM','ZS']

        self.nifty100_list = ['INDUSINDBK.NS','HDFCLIFE.NS','EICHERMOT.NS','SBICARD.NS','DABUR.NS','APOLLOHOSP.NS','POWERGRID.NS','DLF.NS','AXISBANK.NS','BAJAJFINSV.NS','PNB.NS', 'KOTAKBANK.NS','ADANIENT.NS','ZOMATO.NS','HINDALCO.NS','JUBLFOOD.NS','ICICIBANK.NS','SBIN.NS','TATAMOTORS.NS','ASIANPAINT.NS', 'BAJFINANCE.NS','MUTHOOTFIN.NS', 'DMART.NS','BOSCHLTD.NS','ONGC.NS','HDFC.NS', 'SRF.NS','ADANIPORTS.NS','BANKBARODA.NS','MARUTI.NS','ACC.NS', 'ITC.NS','HDFCBANK.NS','PAYTM.NS','HDFCAMC.NS', 'RELIANCE.NS','HAVELLS.NS','JSWSTEEL.NS', 'SBILIFE.NS','LICI.NS', 'HINDUNILVR.NS', 'BIOCON.NS','TATACONSUM.NS','NESTLEIND.NS','PIDILITIND.NS','CHOLAFIN.NS','INDIGO.NS','BAJAJ-AUTO.NS','VEDL.NS','PIIND.NS','ADANIGREEN.NS','TITAN.NS','ICICIPRULI.NS','TATASTEEL.NS','MARICO.NS','BRITANNIA.NS','ZYDUSLIFE.NS','M&M.NS','SIEMENS.NS','CIPLA.NS','ULTRACEMCO.NS','ICICIGI.NS','UPL.NS','TATAPOWER.NS','GAIL.NS','COLPAL.NS','BHARTIARTL.NS','MCDOWELL-N.NS','DRREDDY.NS','TORNTPHARM.NS','GODREJCP.NS','NYKAA.NS','PGHH.NS','AMBUJACEM.NS','DIVISLAB.NS','BERGEPAINT.NS','GRASIM.NS','COALINDIA.NS','NAUKRI.NS','WIPRO.NS','IOC.NS','SHREECEM.NS','GLAND.NS','LUPIN.NS','ADANITRANS.NS','HEROMOTOCO.NS','LT.NS','SUNPHARMA.NS','SAIL.NS','BAJAJHLDNG.NS','BPCL.NS','INDUSTOWER.NS','NTPC.NS','TCS.NS','HCLTECH.NS','TECHM.NS','BANDHANBNK.NS','INFY.NS','LTIM.NS', 'HAL.NS']

        self.nifty200_list = ['NYKAA', 'ZOMATO', 'PFC', 'HINDALCO', 'HEROMOTOCO', 'APOLLOHOSP', 'ASTRAL', 'JINDALSTEL', 'INDIANB', 'HAL', 'DLF', 'HONAUT', 'TRENT', 'RECLTD', 'MPHASIS', 'TATACOMM', 'POLYCAB', 'TVSMOTOR', 'NMDC', 'ABB', 'TATASTEEL', 'OBEROIRLTY', 'PAYTM', 'MARUTI', 'M&M', 'JSWSTEEL', 'AMBUJACEM', 'GODREJPROP', 'MOTHERSON', 'LAURUSLABS', 'SAIL', 'INDIGO', 'DRREDDY', 'TTML', 'SUNPHARMA', 'SRF', 'M&MFIN', 'ABBOTINDIA', 'DIXON', 'BHEL', 'LT', 'BHARTIARTL', 'CANBK', 'IPCALAB', 'PNB', 'CONCOR', 'NAUKRI', 'TITAN', 'PERSISTENT', 'LTTS', 'BANKBARODA', 'INDUSTOWER', 'POONAWALLA', 'ZYDUSLIFE', 'LUPIN', 'UPL', 'ACC', 'COROMANDEL', 'BOSCHLTD', 'GODREJCP', 'HDFCAMC', 'VBL', 'ITC', 'LALPATHLAB', 'POWERGRID', 'BAJAJ-AUTO', 'ZEEL', 'IDEA', 'SBICARD', 'NESTLEIND', 'TATAELXSI', 'ONGC', 'SBIN', 'SUNTV', 'RAMCOCEM', 'INDUSINDBK', 'FEDERALBNK', 'NAVINFLUOR', 'PGHH', 'VEDL', 'DMART', 'BRITANNIA', 'COFORGE', 'DEEPAKNTR', 'LICHSGFIN', 'HINDUNILVR', 'ABCAPITAL', 'PEL', 'GRASIM', 'TORNTPOWER', 'AXISBANK', 'L&TFH', 'AUBANK', 'UNIONBANK', 'SHRIRAMFIN', 'ADANIPORTS', 'AUROPHARMA', 'ICICIGI', 'SIEMENS', 'LTIM', 'BAJAJFINSV', 'MSUMI', 'SONACOMS', 'ADANIPOWER', 'HINDZINC', 'TRIDENT', 'YESBANK', 'JUBLFOOD', 'DABUR', 'OFSS', 'BERGEPAINT', 'KOTAKBANK', 'PRESTIGE', 'HAVELLS', 'TATACONSUM', 'IDFCFIRSTB', 'BEL', 'CUMMINSIND', 'COALINDIA', 'HDFCBANK', 'TATAPOWER', 'INDHOTEL', 'BANKINDIA', 'LICI', 'ICICIBANK', 'APOLLOTYRE', 'CIPLA', 'BAJAJHLDNG', 'TORNTPHARM', 'DALBHARAT', 'MCDOWELL-N', 'TATAMOTORS', 'ULTRACEMCO', 'COLPAL', 'DIVISLAB', 'ALKEM', 'TATACHEM', 'DEVYANI', 'TECHM', 'NTPC', 'EICHERMOT', 'BALKRISIND', 'INFY', 'HDFC', 'JSWENERGY', 'BAJFINANCE', 'PETRONET', 'CHOLAFIN', 'TIINDIA', 'ASIANPAINT', 'MAXHEALTH', 'IRFC', 'RELIANCE', 'SBILIFE', 'CROMPTON', 'HCLTECH', 'WIPRO', 'NHPC', 'ABFRL', 'SHREECEM', 'MUTHOOTFIN', 'ESCORTS', 'TCS', 'GAIL', 'ASHOKLEY', 'HINDPETRO', 'VOLTAS', 'PIDILITIND', 'IOC', 'IRCTC', 'FORTIS', 'WHIRLPOOL', 'UBL', 'SYNGENE', 'BHARATFORG', 'GLAND', 'AWL', 'HDFCLIFE', 'PIIND', 'DELHIVERY', 'BATAINDIA', 'BANDHANBNK', 'ADANIGREEN', 'ICICIPRULI', 'MARICO', 'MRF', 'BPCL', 'FLUOROCHEM', 'POLICYBZR', 'PAGEIND', 'PATANJALI', 'MFSL', 'OIL', 'BIOCON', 'ADANIENT', 'CGPOWER', 'GUJGASLTD', 'ADANITRANS', 'IGL', 'ATGL']

        self.nifty50_list =["HDFCBANK.NS"]

        # self.current_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.current_date = (datetime.now()).strftime("%Y-%m-%d")

        self.start_date = (datetime.now() - timedelta(days=time_delta_days)).strftime("%Y-%m-%d")

        self.index_list = {
            "nasdaq100": self.nasdaq100_list,
            "nifty100": self.nifty100_list,
            "nifty200": self.nifty100_list,
            "nifty50": self.nifty50_list
        }

        self.index = index

        self.interval=interval

        self.good_stocks: List[Dict[str, Any]] = []

        self.mode = self._get_mode(interval=interval)

        self.logger = Logger(name=__name__)

    def _get_mode(self, interval: str) -> str:
        """_summary_

        Args:
            interval (str): _description_

        Returns:
            str: _description_
        """

        if 'h' in interval:
            return "hourly"
        elif 'wk' in interval:
            # raise IntervalRunNotPossibleException("Weekly Mode is not possible with the script as of now")
            return "weekly"
        elif '15min' in interval or '15m' in interval:
            return "15m"
        elif 'yr' in interval:
            raise IntervalRunNotPossibleException("Weekly Mode is not possible with the script as of now")

        raise UnknownIntervalException(f"Provided Interval `{interval}` is unknow to the system, Please raise a request to add it!")


    def calculate_avg_perc_changes(self, data_ohlc: DataFrame):
        """_summary_
        """

        data_ohlc['avg_%_green'] = data_ohlc.loc[data_ohlc['candle_colour'] == "Green", '%'].mean()
        data_ohlc['avg_%_red'] = data_ohlc.loc[data_ohlc['candle_colour'] == "Red", '%'].mean()
        data_ohlc['avg_%'] = data_ohlc.loc[:, '%'].mean()

    def mark_leg_candle(self, data_ohlc: DataFrame):
        """_summary_
        """

        data_ohlc.loc[(data_ohlc['%'] / data_ohlc['avg_%_green']) >= 2.2, 'leg'] = 'green_leg_out'
        data_ohlc.loc[(data_ohlc['%'] / data_ohlc['avg_%_red']) >= 2.0, 'leg'] = 'red_leg_in'

    def mark_resistance_points(self, data_ohlc: DataFrame):
        """_summary_
        """


        # resistance for situation 1 when pivot is just bigger than all others taken next 4 candles
        data_ohlc.loc[ ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(1) ) & ( data_ohlc['max_value'].shift(1) > data_ohlc['max_value'].shift(2)) & ( data_ohlc['max_value'].shift(2) > data_ohlc['max_value'].shift(3)) & ( data_ohlc['max_value'].shift(3) > data_ohlc['max_value'].shift(4))
                    & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-1)) & ( data_ohlc['max_value'].shift(-1) > data_ohlc['max_value'].shift(-2)) & ( data_ohlc['max_value'].shift(-2) > data_ohlc['max_value'].shift(-3)) & ( data_ohlc['max_value'].shift(-3) > data_ohlc['max_value'].shift(-4))
                , 'pivot'] = 'resistance'

        # resistance for situation 2 when pivot is just bigger than all others taken next 5 candles
        data_ohlc.loc[ ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(1) ) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(2)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(3)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(4)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(5))
                    & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-1)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-2)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-3)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-4)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-5))
                , 'pivot'] = 'resistance'

        # resistance for situation 1 when pivot is just bigger than all others taken next 4 candles
        data_ohlc.loc[ ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(1) ) & ( data_ohlc['max_value'].shift(1) > data_ohlc['max_value'].shift(2)) & ( data_ohlc['max_value'].shift(2) > data_ohlc['max_value'].shift(3)) & ( data_ohlc['max_value'].shift(3) > data_ohlc['max_value'].shift(4))
                    & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-1)) & ( data_ohlc['max_value'].shift(-1) > data_ohlc['max_value'].shift(-2)) & ( data_ohlc['max_value'].shift(-2) > data_ohlc['max_value'].shift(-3)) & ( data_ohlc['max_value'].shift(-3) > data_ohlc['max_value'].shift(-4))
                , 'resistance'] = 'Y'

        # resistance for situation 2 when pivot is just bigger than all others taken next 5 candles
        data_ohlc.loc[ ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(1) ) & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(2)) & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(3)) & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(4)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(5))
                    & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-1)) & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-2)) & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-3)) & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-4)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-5))
                , 'resistance'] = 'Y'

    def mark_support_points(self, data_ohlc: DataFrame):
        """_summary_
        """


        # support for situation 1 when pivot is just smaller than all others
        data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'].shift(1) < data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'].shift(2) < data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'].shift(3) < data_ohlc['min_value'].shift(4))
                    & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'].shift(-1) < data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'].shift(-2) < data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'].shift(-3) < data_ohlc['min_value'].shift(-4))
                , 'pivot'] = 'support'

        # support for situation 1 when pivot could be smaller or equal to others base candles upto 4 base candle
        data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(4))
                    & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-4))
                , 'pivot'] = 'support'

        # support for situation 1 when pivot is just smaller than all others
        data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'].shift(1) < data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'].shift(2) < data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'].shift(3) < data_ohlc['min_value'].shift(4))
                    & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'].shift(-1) < data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'].shift(-2) < data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'].shift(-3) < data_ohlc['min_value'].shift(-4))
                , 'support'] = 'Y'

        # support for situation 1 when pivot could be smaller or equal to others base candles upto 4 base candle
        data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(4))
                    & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-4))
                , 'support'] = 'Y'



    # def identify_possible_dz(self, data_ohlc: DataFrame):
    #     """_summary_
    #     """


    #     # TODO: added more candles and more condition
    #     data_ohlc.loc[ (data_ohlc['leg']=='green_leg_out') &
    #             ((data_ohlc['pivot'].shift(1) == 'support') | (data_ohlc['pivot'].shift(2) == 'support') | (data_ohlc['pivot'].shift(3) == 'support') | (data_ohlc['pivot'].shift(4) == 'support') | (data_ohlc['pivot'].shift(5) == 'support') | (data_ohlc['pivot'].shift(6) == 'support'))
    #             & ((data_ohlc['pivot'].shift(1) != 'resistance') & (data_ohlc['pivot'].shift(2) != 'resistance') & (data_ohlc['pivot'].shift(3) != 'resistance') & (data_ohlc['pivot'].shift(4) != 'resistance') & (data_ohlc['pivot'].shift(5) != 'resistance') & (data_ohlc['pivot'].shift(6) != 'resistance'))
    #             & ((data_ohlc['leg'].shift(1) != 'red_leg_in') & (data_ohlc['leg'].shift(2) != 'red_leg_in') & (data_ohlc['leg'].shift(3) != 'red_leg_in') & (data_ohlc['leg'].shift(4) != 'red_leg_in') & (data_ohlc['leg'].shift(5) != 'red_leg_in') & (data_ohlc['leg'].shift(6) != 'red_leg_in'))
    #             , 'dz'] = 'Y'

    #     # TODO: added new condition
    #     data_ohlc.loc[(data_ohlc['dz'] == 'Y') & ((data_ohlc['dz'].shift(1) == 'Y') |  (data_ohlc['dz'].shift(2) == 'Y')), 'dz'] = float("NaN")

    def identify_possible_dz(self, data_ohlc: DataFrame):
        """_summary_
        """


        # TODO: added more candles and more condition
        data_ohlc.loc[ (data_ohlc['leg']=='green_leg_out') &
                ((data_ohlc['support'].shift(1) == 'Y') | (data_ohlc['support'].shift(2) == 'Y') | (data_ohlc['support'].shift(3) == 'Y') | (data_ohlc['support'].shift(4) == 'Y') | (data_ohlc['support'].shift(5) == 'Y') | (data_ohlc['support'].shift(6) == 'Y'))
                & ((data_ohlc['resistance'].shift(1) != 'Y') & (data_ohlc['resistance'].shift(2) != 'Y') & (data_ohlc['resistance'].shift(3) != 'Y') & (data_ohlc['resistance'].shift(4) != 'Y') & (data_ohlc['resistance'].shift(5) != 'Y') & (data_ohlc['resistance'].shift(6) != 'Y'))
                & ((data_ohlc['leg'].shift(1) != 'red_leg_in') & (data_ohlc['leg'].shift(2) != 'red_leg_in') & (data_ohlc['leg'].shift(3) != 'red_leg_in') & (data_ohlc['leg'].shift(4) != 'red_leg_in') & (data_ohlc['leg'].shift(5) != 'red_leg_in') & (data_ohlc['leg'].shift(6) != 'red_leg_in'))
                , 'dz'] = 'Y'

        # TODO: added new condition
        data_ohlc.loc[(data_ohlc['dz'] == 'Y') & ((data_ohlc['dz'].shift(1) == 'Y') |  (data_ohlc['dz'].shift(2) == 'Y')), 'dz'] = float("NaN")

    def get_good_dz(self, achievement: Dict[str, Any], potential_stocks: List[Dict[str, Any]], fresh_zone_helper_list: List[Tuple[str, str, str]], stock: str):
        """_summary_
        """
        # min_value, max_value, pivot, leg, dz, date
        dz_points = []
        for item in achievement:

            # if item['pivot'] == 'resistance':
            #     dz_points.append((item['Datetime'], item['max_value']))

            if item['resistance'] == 'Y':
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
            else:
                print("Not Good DZ for %s on `date`: %s" % (stock, item[0]))

        # return "No Dz found for %s" % stock if not found else "Dz found for %s, please check!" % stock
        return "Analysis Done!"

    def is_it_fresh_zone(self, support_for_dz: Tuple[str, str, str], data_ohlc: DataFrame) -> bool:
        """_summary_
        """

        datetime_filter = support_for_dz[0]

        filtered_df = data_ohlc[data_ohlc['Datetime'] > datetime_filter]

        min_value = filtered_df['low'].loc[filtered_df['low'].idxmin()]      # Minimum in column

        if min_value > support_for_dz[2]:
            return True

        return False


    def get_fresh_zone(self, potential_stocks: List[Dict[str, Any]], fresh_zone_helper_list: List[Tuple[str, str, str]], data_ohlc: DataFrame):
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

                if self.is_it_fresh_zone(support_for_dz=record, data_ohlc=data_ohlc):
                    item['fresh'] = 'Y'
                else:
                    item['fresh'] = 'N'
                break

    def get_stocks_with_follow_through(self, potential_stocks: List[Dict[str, Any]], data_ohlc: DataFrame):
        """
            1. take the datetime for the fresh zone
            2. takeout the dataset that is >= datetime from above
            3. Check if the next 3 candles are green
            4. if yes mark them with follow_through flag
        """

        for item in potential_stocks:

            if item['fresh'] == 'N':
                item['follow_through'] = 'N'
                item['current_closing_price'] = 'N/A'
                item['green_leg_out_low_price'] = 'N/A'
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
            forth_candle = filtered_df['candle_colour'].shift(4).values[8] if len(filtered_df['candle_colour'].shift(4).values) >= 9 else None

            if (first_candle == 'Green') \
                and  (second_candle == 'Green') \
                and  (third_candle == 'Green') \
                :
                item['follow_through'] = 'Y'
                item['green_leg_out_low_price'] = filtered_df['open'].iloc[0]
                item['current_closing_price'] = filtered_df['close'].iloc[-1]
            elif (first_candle == 'Green') \
                and  (second_candle == 'Red') \
                and  (third_candle == 'Green') \
                and  (forth_candle == 'Green') \
                :
                item['follow_through'] = 'Y'
                item['green_leg_out_low_price'] = filtered_df['open'].iloc[0]
                item['current_closing_price'] = filtered_df['close'].iloc[-1]
            elif (first_candle == 'Green') \
                and  (second_candle == 'Green') \
                and  (third_candle == 'Red') \
                and  (forth_candle == 'Green') \
                :
                item['follow_through'] = 'Y'
                item['green_leg_out_low_price'] = filtered_df['open'].iloc[0]
                item['current_closing_price'] = filtered_df['close'].iloc[-1]
            else:
                item['follow_through'] = 'N'
                item['current_closing_price'] = 'N/A'
                item['green_leg_out_low_price'] = 'N/A'

    def is_it_base_candle(self, open: float, close: float, low: float, high: float) -> bool:
        """
        """

        return True if (abs(close-open)/abs(high-low))*100 <= 50.0 else False

    def get_stocks_with_base_before_follow_through(self, potential_stocks: List[Dict[str, Any]], data_ohlc: DataFrame) -> None:
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
                item['follow_through_with_base'] = 'N'
                continue

            # timestamp
            stock_time = item['date']

            filtered_df: DataFrame = data_ohlc[data_ohlc['Datetime'] <= stock_time]

            if not self.is_it_base_candle(open=filtered_df['open'].shift(1).values.tolist().pop(), close=filtered_df['close'].shift(1).values.tolist().pop(), low=filtered_df['low'].shift(1).values.tolist().pop(), high=filtered_df['high'].shift(1).values.tolist().pop()):
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

    @staticmethod
    def get_change(current: float, previous: float):
        if current == previous:
            return 0
        try:
            return (abs(current - previous) / previous) * 100.0
        except ZeroDivisionError:
            return float('inf')

    def add_percentage_of_change(self, potential_stocks: List[Dict[str, Any]]):
        """_summary_

        Args:
            potential_stocks (List[Dict[str, Any]]): _description_
        """

        for item in potential_stocks:

            if item["current_closing_price"] == "N/A" or item["green_leg_out_low_price"] == "N/A":
                item["percentage_of_change"] = "N/A"
                continue

            _perct_number = FollowTheFootPrints.get_change(current=item["current_closing_price"], previous=item["green_leg_out_low_price"])
            item["percentage_of_change"] = "{:.1f}".format(_perct_number)


    def process(self):
        """_summary_

        Returns:
            _type_: _description_
        """

        print(f"====> Analysis started for date range: `{self.start_date} to `{self.current_date}` <======")

        # find out if we want to rename date field
        date_field_rename = False
        if self.interval in ('1wk', 'yr'):
            date_field_rename= True

        for stock in self.index_list[self.index]:

            try:
                # get the stock dataset
                current_price: DataFrame = yf.download(stock, start=self.start_date, end=self.current_date,
                                interval=self.interval, rounding=True)

                data_ohlc = current_price.reset_index() # Resetting the index column

                data_ohlc = data_ohlc[data_ohlc.isna().any(axis=1) == False] # Removing null records

                # std the column names
                data_ohlc.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Vol': 'vol'}, inplace=True)

                if date_field_rename:
                    data_ohlc.rename(columns={'Date': 'Datetime'}, inplace=True)

                # mark candles with colours
                data_ohlc.loc[data_ohlc['open'] <= data_ohlc['close'], 'candle_colour'] = 'Green'
                data_ohlc.loc[data_ohlc['open'] > data_ohlc['close'], 'candle_colour'] = 'Red'

                # datatype change
                data_ohlc["open"] = pd.to_numeric(data_ohlc["open"])
                data_ohlc["close"] = pd.to_numeric(data_ohlc["close"])

                # adds % change column
                data_ohlc['%'] = ( ( data_ohlc['close'] - data_ohlc['close'].shift(1) ) / data_ohlc['close'].shift()) * 100

                self.calculate_avg_perc_changes(data_ohlc = data_ohlc)

                self.mark_leg_candle(data_ohlc = data_ohlc)

                # add columns
                data_ohlc['max_value'] = data_ohlc[["open", "close"]].max(axis=1).apply(np.ceil)
                data_ohlc['min_value'] = data_ohlc[["open", "close"]].min(axis=1).apply(np.floor)

                self.mark_resistance_points(data_ohlc = data_ohlc)
                self.mark_support_points(data_ohlc = data_ohlc)

                self.identify_possible_dz(data_ohlc = data_ohlc)

                # 2023-03-24 09:15:00+05:30
                # print(data_ohlc[data_ohlc['Datetime'] >= "2023-06-09 00:00:00+05:30"].head(50))

                # data is prepared, let's calculate

                fresh_zone_helper_list: List[Tuple[str, str, str]] = []
                potential_stocks: List[Dict[str, Any]] = []

                # get dict
                achievement = data_ohlc.to_dict('records')

                # get good demand zone with achievement
                self.get_good_dz(achievement=achievement, potential_stocks=potential_stocks, fresh_zone_helper_list=fresh_zone_helper_list, stock=stock)

                # get fresh zone
                self.get_fresh_zone(potential_stocks=potential_stocks, fresh_zone_helper_list=fresh_zone_helper_list, data_ohlc=data_ohlc)

                # get follow through
                self.get_stocks_with_follow_through(potential_stocks=potential_stocks, data_ohlc = data_ohlc)

                # get stocks with proper base candles
                self.get_stocks_with_base_before_follow_through(potential_stocks=potential_stocks, data_ohlc = data_ohlc)

                self.add_percentage_of_change(potential_stocks=potential_stocks)

                # appends to the global list of good stocks for WIT
                self.good_stocks.extend(potential_stocks)

            except Exception as ex:
                print(f" Exception raised for stock {stock}, with details {ex}")
                continue

        # normalise into DF
        df = json_normalize(self.good_stocks)

        # get a csv with a follow_through
        # df.sort_values('percentage_of_change').to_csv(f'{self.index}_{self.mode}.csv', encoding='utf-8', index=False)
        df[df['follow_through_with_base'] == 'Y'].sort_values('percentage_of_change').to_csv(f'{self.index}_{self.mode}.csv', encoding='utf-8', index=False)

if __name__ == "__main__":

    # set timedelta to give a range
    time_delta_days = 90

    # default index=nifty100 and interval=1h
    # ffp_obj = FollowTheFootPrints(time_delta_days=time_delta_days, index="nifty200")
    # ffp_obj = FollowTheFootPrints(time_delta_days=time_delta_days, index="nasdaq100")
    # ffp_obj = FollowTheFootPrints(time_delta_days=time_delta_days, interval="1wk")
    # ffp_obj = FollowTheFootPrints(time_delta_days=time_delta_days, interval='15m')
    # ffp_obj = FollowTheFootPrints(index="nifty50", time_delta_days=time_delta_days)
    ffp_obj = FollowTheFootPrints(time_delta_days=time_delta_days)

    # start the process
    ffp_obj.process()
