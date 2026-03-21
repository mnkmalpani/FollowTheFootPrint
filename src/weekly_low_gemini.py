import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from logging import Logger
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict, Any, Tuple
from pandas import DataFrame, json_normalize
import traceback
import requests
import os
import io

class IntervalRunNotPossibleException(Exception):
    """Interval not supported"""

class UnknownIntervalException(Exception):
    """Interval unknown"""

class FollowTheFootPrints:

    def __init__(self, time_delta_days: int, index: str="nifty100", interval: str="1h",
                 telegram_token: str = None, telegram_chat_id: str = None) -> None:

        self.logger = Logger(name=__name__)
        self.index = index
        self.interval = interval
        self.mode = self._get_mode(interval=interval)
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id

        # Dates
        self.current_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.start_date = (datetime.now() - timedelta(days=time_delta_days)).strftime("%Y-%m-%d")

        # 1. Dynamic Stock Fetching
        self.stock_list = self._get_stock_list_dynamically(index)

        self.good_stocks: List[Dict[str, Any]] = []

    def _get_stock_list_dynamically(self, index_name: str) -> List[str]:
        """
        Fetches Nifty indices and sanitizes the data to remove bad rows/disclaimers.
        """
        print(f"Fetching latest stock list for {index_name}...")

        nifty_map = {
            "nifty50": "nifty50",
            "nifty100": "nifty100",
            "nifty200": "nifty200",
            "nifty500": "nifty500",
            "niftybank": "niftybank",
            "niftyit": "niftyit"
        }

        # Hardcoded blocklist for known bad entries in NSE CSVs
        BLOCKLIST = ["DUMMYHDLVR", "SYMBOL", "JERSEY"]

        if index_name in nifty_map:
            try:
                url = f"https://www.niftyindices.com/IndexConstituent/ind_{nifty_map[index_name]}list.csv"
                headers = {'User-Agent': 'Mozilla/5.0'}

                response = requests.get(url, headers=headers)
                response.raise_for_status()

                df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))

                # 1. Normalize column names (strip spaces)
                df.columns = [c.strip() for c in df.columns]

                # 2. Find the correct column (It's usually 'Symbol')
                symbol_col = next((c for c in df.columns if 'Symbol' in c), None)

                if not symbol_col:
                    print(f"Could not find Symbol column for {index_name}")
                    return []

                # 3. Clean the data
                # Drop NaNs
                df = df.dropna(subset=[symbol_col])

                # Convert to string, strip whitespace, and uppercase
                raw_symbols = df[symbol_col].astype(str).str.strip().str.upper()

                # 4. FILTERING LOGIC
                valid_tickers = []
                for sym in raw_symbols:
                    # Skip if in blocklist
                    if sym in BLOCKLIST:
                        continue
                    # Skip if it contains "NIFTY" (header row)
                    if "NIFTY" in sym:
                        continue
                    # Skip if it's too long (NSE tickers are rarely > 10 chars, DUMMYHDLVR is 10)
                    # We can set a safe limit or just trust the blocklist.
                    # Let's trust the blocklist + standard regex.
                    if not sym.replace('-', '').isalnum():
                        continue

                    valid_tickers.append(f"{sym}.NS")

                print(f"Successfully fetched {len(valid_tickers)} stocks for {index_name}")
                return valid_tickers

            except Exception as e:
                print(f"Error fetching dynamic list for {index_name}: {e}")
                return []

        elif index_name == "nasdaq100":
             # Your existing manual list...
            return ['ATVI', 'ADBE', 'AMD', 'ALXN', 'ALGN', 'GOOGL', 'GOOG', 'AMZN', 'AAL', 'AMGN', 'ADI', 'AAPL', 'AMAT', 'ASML', 'ADSK', 'ADP', 'BIDU', 'BIIB', 'BMRN', 'BKNG', 'AVGO', 'CDNS', 'CERN', 'CHTR', 'CHKP', 'CTAS', 'CSCO', 'CTXS', 'CTSH', 'CMCSA', 'CPRT', 'COST', 'CSX', 'CTRP', 'DXCM', 'XRAY', 'DOCU', 'DLTR', 'EBAY', 'EA', 'EXC', 'EXPE', 'EXPD', 'FAST', 'FISV', 'GILD', 'HAS', 'HOLX', 'IDXX', 'ILMN', 'SYNH', 'INTC', 'INTU', 'ISRG', 'JD', 'KLAC', 'LRCX', 'LBTYA', 'LIN', 'LULU', 'MAR', 'MXIM', 'MELI', 'MCHP', 'MU', 'MSFT', 'MDLZ', 'MNST', 'NFLX', 'NTES', 'NVDA', 'NXPI', 'ORLY', 'PCAR', 'PAYX', 'PYPL', 'PCLN', 'QCOM', 'REGN', 'ROST', 'SGEN', 'SBUX', 'SRCL', 'SYMC', 'SNPS', 'TTWO', 'TSLA', 'TXN', 'KHC', 'PCLN', 'ULTA', 'UAL', 'VRSN', 'VRTX', 'WBA', 'WDAY', 'WYNN', 'XEL', 'XLNX']

        else:
            raise ValueError(f"Index {index_name} not supported.")

    def _get_mode(self, interval: str) -> str:
        if 'h' in interval:
            return "hourly"
        elif 'wk' in interval:
            return "weekly"
        elif '15min' in interval:
            return "15mins"
        elif 'yr' in interval:
            raise IntervalRunNotPossibleException("Yearly Mode is not possible")
        raise UnknownIntervalException(f"Provided Interval `{interval}` is unknown")

    def calculate_avg_perc_changes(self, data_ohlc: DataFrame):
        data_ohlc['avg_%_green'] = data_ohlc.loc[data_ohlc['%_of_change'] >= 0.0, '%_of_change'].mean()
        data_ohlc['avg_%_red'] = data_ohlc.loc[data_ohlc['%_of_change'] < 0, '%_of_change'].mean()
        data_ohlc['avg_%'] = data_ohlc.loc[:, '%_of_change'].mean()

    def mark_leg_candle(self, data_ohlc: DataFrame):
        data_ohlc.loc[(data_ohlc['%_of_change'] / data_ohlc['avg_%_green']) >= 1.7, 'leg'] = 'green_leg_out'
        data_ohlc.loc[(data_ohlc['%_of_change'] / data_ohlc['avg_%_red']) >= 2.0, 'leg'] = 'red_leg_in'

    def mark_resistance_points(self, data_ohlc: DataFrame):
        data_ohlc.loc[ ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(1) ) & ( data_ohlc['max_value'].shift(1) > data_ohlc['max_value'].shift(2)) & ( data_ohlc['max_value'].shift(2) > data_ohlc['max_value'].shift(3)) & ( data_ohlc['max_value'].shift(3) > data_ohlc['max_value'].shift(4))
                    & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-1)) & ( data_ohlc['max_value'].shift(-1) > data_ohlc['max_value'].shift(-2)) & ( data_ohlc['max_value'].shift(-2) > data_ohlc['max_value'].shift(-3)) & ( data_ohlc['max_value'].shift(-3) > data_ohlc['max_value'].shift(-4))
                , 'pivot'] = 'resistance'

        data_ohlc.loc[ ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(1) ) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(2)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(3)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(4)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(5))
                    & ( data_ohlc['max_value'] >= data_ohlc['max_value'].shift(-1)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-2)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-3)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-4)) & ( data_ohlc['max_value'] > data_ohlc['max_value'].shift(-5))
                , 'pivot'] = 'resistance'

    def mark_support_points(self, data_ohlc: DataFrame):
        data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'].shift(1) < data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'].shift(2) < data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'].shift(3) < data_ohlc['min_value'].shift(4))
                    & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'].shift(-1) < data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'].shift(-2) < data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'].shift(-3) < data_ohlc['min_value'].shift(-4))
                , 'pivot'] = 'support'

        data_ohlc.loc[ ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(1) ) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(2)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(3)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(4))
                    & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-1)) & ( data_ohlc['min_value'] <= data_ohlc['min_value'].shift(-2)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(-3)) & ( data_ohlc['min_value'] < data_ohlc['min_value'].shift(-4))
                , 'pivot'] = 'support'

    def identify_possible_dz(self, data_ohlc: DataFrame):
        data_ohlc.loc[ (data_ohlc['leg']=='green_leg_out') &
                ((data_ohlc['pivot'].shift(1) == 'support') | (data_ohlc['pivot'].shift(2) == 'support') | (data_ohlc['pivot'].shift(3) == 'support') | (data_ohlc['pivot'].shift(4) == 'support') | (data_ohlc['pivot'].shift(5) == 'support') | (data_ohlc['pivot'].shift(6) == 'support'))
                & ((data_ohlc['pivot'].shift(1) != 'resistance') & (data_ohlc['pivot'].shift(2) != 'resistance') & (data_ohlc['pivot'].shift(3) != 'resistance') & (data_ohlc['pivot'].shift(4) != 'resistance') & (data_ohlc['pivot'].shift(5) != 'resistance') & (data_ohlc['pivot'].shift(6) != 'resistance'))
                & ((data_ohlc['leg'].shift(1) != 'red_leg_in') & (data_ohlc['leg'].shift(2) != 'red_leg_in') & (data_ohlc['leg'].shift(3) != 'red_leg_in') & (data_ohlc['leg'].shift(4) != 'red_leg_in') & (data_ohlc['leg'].shift(5) != 'red_leg_in') & (data_ohlc['leg'].shift(6) != 'red_leg_in'))
                , 'dz'] = 'Y'

        data_ohlc.loc[(data_ohlc['dz'] == 'Y') & ((data_ohlc['dz'].shift(1) == 'Y') |  (data_ohlc['dz'].shift(2) == 'Y')), 'dz'] = float("NaN")

    def get_good_dz(self, achievement: Dict[str, Any], potential_stocks: List[Dict[str, Any]], fresh_zone_helper_list: List[Tuple[str, str, str]], stock: str):
        dz_points = []
        for item in achievement:
            if item['pivot'] == 'resistance':
                dz_points.append((item['Datetime'], item['max_value']))

            if item['dz'] == 'Y':
                dz_points.append((item['Datetime'], item['dz']))
                fresh_zone_helper_list.append((item['Datetime'], item['dz'], item['low']))

        for item in dz_points:
            if not item[1] == 'Y':
                continue

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
                while True:
                    if not isinstance(dz_points[next][1], float):
                        next  = next + 1
                        continue
                    break
                next_r = dz_points[next]
            except IndexError:
                next_r = ("", float("inf"))

            if previous_r[1] < next_r[1]:
                potential_stocks.append({ "stock": stock, "date": item[0] })

    def is_it_fresh_zone(self, support_for_dz: Tuple[str, str, str], data_ohlc: DataFrame) -> bool:
        datetime_filter = support_for_dz[0]
        filtered_df = data_ohlc[data_ohlc['Datetime'] > datetime_filter]

        if filtered_df.empty: return True # If no data after, it is fresh

        min_value = filtered_df['low'].min()
        if min_value > support_for_dz[2]:
            return True
        return False

    def get_fresh_zone(self, potential_stocks: List[Dict[str, Any]], fresh_zone_helper_list: List[Tuple[str, str, str]], data_ohlc: DataFrame):
        for item in potential_stocks:
            stock_time = item['date']
            for record in fresh_zone_helper_list:
                if record[0] != stock_time: continue

                if self.is_it_fresh_zone(support_for_dz=record, data_ohlc=data_ohlc):
                    item['fresh'] = 'Y'
                else:
                    item['fresh'] = 'N'
                break

    def get_stocks_with_follow_through(self, potential_stocks: List[Dict[str, Any]], data_ohlc: DataFrame):
        for item in potential_stocks:
            stock_time = item['date']
            filtered_df = data_ohlc[data_ohlc['Datetime'] >= stock_time]

            # Need at least 4 candles to check follow through properly
            if len(filtered_df) < 5:
                item['follow_through'] = 'N'
                item['current_closing_price'] = 'N/A'
                item['green_leg_out_low_price'] = 'N/A'
                continue

            first_candle = filtered_df['candle_colour'].iloc[1] if len(filtered_df) > 1 else None
            second_candle = filtered_df['candle_colour'].iloc[2] if len(filtered_df) > 2 else None
            third_candle = filtered_df['candle_colour'].iloc[3] if len(filtered_df) > 3 else None
            forth_candle = filtered_df['candle_colour'].iloc[4] if len(filtered_df) > 4 else None

            item['green_leg_out_low_price'] = filtered_df['open'].iloc[0]
            item['current_closing_price'] = filtered_df['close'].iloc[-1]

            if (first_candle == 'Green') and (second_candle == 'Green') and (third_candle == 'Green'):
                item['follow_through'] = 'Y'
            elif (first_candle == 'Green') and (second_candle == 'Red') and (third_candle == 'Green') and (forth_candle == 'Green'):
                item['follow_through'] = 'Y'
            elif (first_candle == 'Green') and (second_candle == 'Green') and (third_candle == 'Red') and (forth_candle == 'Green'):
                item['follow_through'] = 'Y'
            else:
                item['follow_through'] = 'N'

    @staticmethod
    def get_change(current: float, previous: float):
        if current == previous: return 0
        try:
            return ((current - previous) / previous) * 100.0
        except ZeroDivisionError:
            return float('inf')

    def add_percentage_of_change(self, potential_stocks: List[Dict[str, Any]]):
        for item in potential_stocks:
            if item["current_closing_price"] == "N/A" or item["green_leg_out_low_price"] == "N/A":
                item["percentage_of_change"] = -0.0
                continue
            _perct_number = FollowTheFootPrints.get_change(current=item["current_closing_price"], previous=item["green_leg_out_low_price"])
            item["percentage_of_change"] = "{:.1f}".format(_perct_number)

    def send_telegram_alert(self, csv_filename: str, count: int):
        """Sends the generated CSV to Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            print("Telegram credentials not provided. Skipping alert.")
            return

        try:
            print(f"Sending results to Telegram ({self.telegram_chat_id})...")

            # 1. Send Summary Message
            msg_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            msg_data = {
                "chat_id": self.telegram_chat_id,
                "text": f"📊 *Market Scan Completed*\n\nIndex: {self.index}\nInterval: {self.interval}\nStocks Found: {count}\n\nFile attached below 👇",
                "parse_mode": "Markdown"
            }
            requests.post(msg_url, data=msg_data)

            # 2. Send CSV File (filename tuple required for proper multipart upload)
            doc_url = f"https://api.telegram.org/bot{self.telegram_token}/sendDocument"
            with open(csv_filename, 'rb') as f:
                requests.post(
                    doc_url,
                    data={"chat_id": self.telegram_chat_id},
                    files={"document": (os.path.basename(csv_filename), f)},
                    timeout=30,
                )

            print("Telegram alert sent successfully!")

        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")

    def process(self):
        print(f"====> Analysis started for {self.index} from `{self.start_date}` to `{self.current_date}` <======")

        date_field_rename = False
        if self.interval in ('1wk', 'yr'):
            date_field_rename= True

        for stock in self.stock_list:
            try:
                # Silence yfinance progress bar
                current_price: DataFrame = yf.download(stock, start=self.start_date, end=self.current_date,
                                interval=self.interval, rounding=True, progress=False)

                if current_price.empty:
                    continue

                data_ohlc = current_price.reset_index()
                data_ohlc = data_ohlc[data_ohlc.isna().any(axis=1) == False]

                # Handling MultiIndex columns if yfinance returns them (common in newer versions)
                if isinstance(data_ohlc.columns, pd.MultiIndex):
                    data_ohlc.columns = data_ohlc.columns.get_level_values(0)

                data_ohlc.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Vol': 'vol', 'Date': 'Datetime'}, inplace=True)

                # Ensure Datetime column exists (sometimes yfinance index name varies)
                if 'Datetime' not in data_ohlc.columns and 'Date' not in data_ohlc.columns:
                     # If reset_index didn't result in a named column, the index might have been unnamed
                     data_ohlc['Datetime'] = data_ohlc.index

                # mark candles with colours
                data_ohlc.loc[data_ohlc['open'] <= data_ohlc['close'], 'candle_colour'] = 'Green'
                data_ohlc.loc[data_ohlc['open'] > data_ohlc['close'], 'candle_colour'] = 'Red'

                data_ohlc["open"] = pd.to_numeric(data_ohlc["open"])
                data_ohlc["close"] = pd.to_numeric(data_ohlc["close"])

                data_ohlc['%_of_change'] = ( ( data_ohlc['close'] - data_ohlc['close'].shift(1) ) / data_ohlc['close'].shift(1)) * 100

                self.calculate_avg_perc_changes(data_ohlc = data_ohlc)
                self.mark_leg_candle(data_ohlc = data_ohlc)

                data_ohlc['max_value'] = data_ohlc[["open", "close"]].max(axis=1).apply(np.ceil)
                data_ohlc['min_value'] = data_ohlc[["open", "close"]].min(axis=1).apply(np.floor)

                self.mark_resistance_points(data_ohlc = data_ohlc)
                self.mark_support_points(data_ohlc = data_ohlc)
                self.identify_possible_dz(data_ohlc = data_ohlc)

                achievement = data_ohlc.to_dict('records')
                fresh_zone_helper_list: List[Tuple[str, str, str]] = []
                potential_stocks: List[Dict[str, Any]] = []

                self.get_good_dz(achievement=achievement, potential_stocks=potential_stocks, fresh_zone_helper_list=fresh_zone_helper_list, stock=stock)
                self.get_fresh_zone(potential_stocks=potential_stocks, fresh_zone_helper_list=fresh_zone_helper_list, data_ohlc=data_ohlc)
                self.get_stocks_with_follow_through(potential_stocks=potential_stocks, data_ohlc = data_ohlc)
                self.add_percentage_of_change(potential_stocks=potential_stocks)

                self.good_stocks.extend(potential_stocks)

            except Exception as e:
                # print(f"Skipping {stock}: {e}") # Uncomment for debugging
                continue

        if not self.good_stocks:
            print("No stocks found matching criteria.")
            return

        df = json_normalize(self.good_stocks)

        # Filter logic
        result_df = df[(df['follow_through'] == 'Y') & ~(df['percentage_of_change'].str.startswith('-', na=False))].sort_values('percentage_of_change')

        filename = f'{self.index}_{self.mode}.csv'
        result_df.to_csv(filename, encoding='utf-8', index=False)
        print(f"Results saved to {filename}")

        # Send Telegram Alert
        self.send_telegram_alert(filename, len(result_df))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # --- CONFIGURATION ---
    # Loaded from .env or environment: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

    # Options: nifty50, nifty100, nifty200, nifty500, niftybank, niftyit
    INDEX_TO_SCAN = "nifty50"

    # --- EXECUTION ---
    ffp_obj = FollowTheFootPrints(
        time_delta_days=1000,
        index=INDEX_TO_SCAN,
        interval="1wk",
        telegram_token=TELEGRAM_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID
    )

    ffp_obj.process()