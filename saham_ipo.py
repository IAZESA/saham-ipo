import datetime
import math
from numpy import append
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import tabulate


# VARIABLES

PARAM_SAVE_STOCK_DATA = 'Save Stock Data'
PARAM_HISTORY_PERIOD = 'History Period'
PARAM_TICK_INTERVAL = 'Tick Interval'

backtest_stocks_list = []
backtest_trailing_sl_list = []
backtest_sma_sl_list = []
backtest_params_dict = {}

all_stocks_ticks_df_dict = {}
all_stocks_pl_insight_dict_list = []

# FUNCTIONS ---------------------------------------------------------------------------------------------------------------


# adjust price based-on Indonesia Stock Exchange standard
def get_price_adjustment(p_stock_price: int) -> int:

    int_price_adjusted = 0

    if 200 < p_stock_price < 500:
        int_price_adjusted = int(p_stock_price/2) * 2
    elif 500 < p_stock_price < 2000:
        int_price_adjusted = int(p_stock_price/5) * 5
    elif 2000 < p_stock_price < 5000:
        int_price_adjusted = int(p_stock_price/10) * 10
    elif p_stock_price > 5000:
        int_price_adjusted = int(p_stock_price/25) * 25
    else:
        int_price_adjusted = p_stock_price

    return int_price_adjusted


# get summary of P/L
def get_list_stock_pl_insight(df_p_stock_analysis, int_p_max_pl, int_p_sma):

    dict_insight1_drawdown = {
            'Remark' : '*Drawdown',

            'SMA' : int_p_sma,
            'Trailing Stop %': df_p_stock_analysis['Trailing Stop %'].iloc[0],
            'PL %': round(df_p_stock_analysis.loc[df_p_stock_analysis['PL %'] < 0, 'PL %'].mean(), 0),
            'Symbol' : df_p_stock_analysis.loc[df_p_stock_analysis['PL %'] < 0, 'Symbol'].count(),
            'Days' : math.ceil(df_p_stock_analysis.loc[df_p_stock_analysis['PL %'] < 0, 'Days'].mean())
    }

    dict_insight2_runup = {
            'Remark' : '*Run-Up',

            'SMA' : int_p_sma,
            'Trailing Stop %': df_p_stock_analysis['Trailing Stop %'].iloc[0],
            'PL %': round(df_p_stock_analysis.loc[df_p_stock_analysis['PL %'] >= 0, 'PL %'].mean(), 0),
            'Symbol' : df_p_stock_analysis.loc[df_p_stock_analysis['PL %'] >= 0, 'Symbol'].count(),
            'Days' : math.ceil(df_p_stock_analysis.loc[df_p_stock_analysis['PL %'] >= 0, 'Days'].mean())
    }

    dict_insight3_avg = {
            'Remark' : '*Average',
            
            'SMA' : int_p_sma,
            'Trailing Stop %': df_p_stock_analysis['Trailing Stop %'].iloc[0],
            'PL %': round(df_p_stock_analysis['PL %'].mean(), 0),
            'Symbol' : df_p_stock_analysis['Symbol'].count(),
            'Days' : math.ceil(df_p_stock_analysis['Days'].mean())
    }

    dict_wrapped_insight = {
        'Trailing SL' : df_p_stock_analysis['Trailing Stop %'].iloc[0],
        'SMA SL' : int_p_sma,
        '[Drawdown] Stocks #' : dict_insight1_drawdown['Symbol'],
        '[Drawdown] Avg Loss %' : dict_insight1_drawdown['PL %'],
        '[Drawdown] Avg Days on Hold' : dict_insight1_drawdown['Days'],
        '[Run-Up] Stocks #' : dict_insight2_runup['Symbol'],
        '[Run-Up] Avg Profit %' : dict_insight2_runup['PL %'],
        '[Run-Up] Avg Days on Hold' : dict_insight2_runup['Days'],
        '[Average] Stocks #' : dict_insight3_avg['Symbol'],
        '[Average] Avg Profit %' : dict_insight3_avg['PL %'],
        '[Average] Avg Days on Hold' : dict_insight3_avg['Days'],
        '[Average] PL % per Day' : round(dict_insight3_avg['PL %'] / dict_insight3_avg['Days'], 0)
    }

    all_stocks_pl_insight_dict_list.append(dict_wrapped_insight)

    return [dict_insight1_drawdown, dict_insight2_runup, dict_insight3_avg]


# trailing stop for max profit
def get_dict_stock_pl_backtest(str_p_symbol, int_p_ipo_price, int_p_ts, int_p_sma):

    print('Processing P/L for [', str_p_symbol, ']')
    print()

    df_stock_analysis = all_stocks_ticks_df_dict[str_p_symbol].copy()

    stock_int_ipo_price = int_p_ipo_price
    stock_int_trail_percent = int_p_ts
    stock_int_trailing_stop_price = 0
    stock_int_peak_price = stock_int_ipo_price
    stock_int_selling_price = 0
    stock_int_final_profit_loss_percent = 0
    stock_str_remark = '-'
    stock_dt_ipo_date = pd.to_datetime(df_stock_analysis.index.values[0])
    stock_dt_selling_date = datetime.datetime.now()
    stock_int_days_hold = 0

    stock_int_close_price = stock_int_ipo_price    

    dict_stock_profit_loss = {
        'Symbol': str_p_symbol,
        'IPO Price': stock_int_ipo_price,
        'Trailing Stop %': stock_int_trail_percent,
        'Trailing Stop Price': stock_int_trailing_stop_price,
        'Peak Price': stock_int_peak_price,
        'Sell Price': stock_int_selling_price,
        'PL %': stock_int_final_profit_loss_percent,
        'Remark' : stock_str_remark,
        'IPO Date' : stock_dt_ipo_date,
        'Sell Date' : stock_dt_selling_date,
        'Days' : stock_int_days_hold
    }

    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Change %', 0) # iterative calc

    df_stock_analysis.insert(len(df_stock_analysis.columns), 'IPO Date', stock_dt_ipo_date) # constant
    df_stock_analysis.insert(len(df_stock_analysis.columns), 'IPO Price', stock_int_ipo_price) # constant
    
    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Floating PL %', 0) # 1 formula calc for all
    df_stock_analysis['Floating PL %'] = round(df_stock_analysis['Close'] / stock_int_ipo_price * 100, 1) - 100

    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Peak Price', 0) # iterative calc
    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Trailing Stop %', stock_int_trail_percent)
    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Trailing Stop Price', 0) # iterative calc

    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Sell Price', stock_int_selling_price) # iterative decision
    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Realized PL %', stock_int_final_profit_loss_percent) # iterative decision

    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Days', 0) # iterative calc
    df_stock_analysis.insert(len(df_stock_analysis.columns), 'Remark', stock_str_remark) # iterative calc

    for i in df_stock_analysis.index:
        stock_int_days_hold += 1
        df_stock_analysis.at[i, 'Days'] = stock_int_days_hold
        
        df_stock_analysis.at[i, 'Change %'] = round(df_stock_analysis.at[i, 'Close'] / stock_int_close_price * 100, 1) - 100

        stock_dt_selling_date = i
        stock_int_close_price = int(df_stock_analysis.at[i, 'Close'])
        stock_int_peak_price = int(max(stock_int_peak_price, df_stock_analysis.at[i, 'High']))
        stock_int_trailing_stop_price = int(stock_int_peak_price * (1 + stock_int_trail_percent / 100))
        
        df_stock_analysis.at[i, 'Peak Price'] = stock_int_peak_price
        df_stock_analysis.at[i, 'Trailing Stop Price'] = stock_int_trailing_stop_price

        if (stock_int_selling_price == 0):
            if (int_p_ts < 0) and (stock_int_close_price < stock_int_trailing_stop_price):
                stock_str_remark = 'TS'
            elif (int_p_sma > 0 and stock_int_close_price < df_stock_analysis.at[i, 'SMA_' + str(int_p_sma)]):
                stock_str_remark = 'SMA_' + str(int_p_sma)
            

        if (stock_int_selling_price == 0 and stock_str_remark != '-'):

            stock_int_selling_price = stock_int_close_price
            stock_int_final_profit_loss_percent = round(stock_int_selling_price / stock_int_ipo_price * 100, 1) - 100

            df_stock_analysis.at[i, 'Sell Price'] = stock_int_selling_price
            df_stock_analysis.at[i, 'Realized PL %'] = stock_int_final_profit_loss_percent
            df_stock_analysis.at[i, 'Remark'] = stock_str_remark

            dict_stock_profit_loss['Peak Price'] = stock_int_peak_price
            dict_stock_profit_loss['Trailing Stop Price'] = stock_int_trailing_stop_price
            dict_stock_profit_loss['Sell Price'] = stock_int_selling_price
            dict_stock_profit_loss['PL %'] = stock_int_final_profit_loss_percent
            dict_stock_profit_loss['Remark'] = stock_str_remark
            dict_stock_profit_loss['Sell Date'] = stock_dt_selling_date
            dict_stock_profit_loss['Days'] = stock_int_days_hold


    if stock_str_remark == '-':

        stock_str_remark = 'HOLD'
        stock_int_selling_price = stock_int_close_price
        stock_int_final_profit_loss_percent = round(stock_int_selling_price / stock_int_ipo_price * 100, 1) - 100

        df_stock_analysis.at[i, 'Sell Price'] = stock_int_selling_price
        df_stock_analysis.at[i, 'Realized PL %'] = stock_int_final_profit_loss_percent
        df_stock_analysis.at[i, 'Remark'] = stock_str_remark

        dict_stock_profit_loss['Peak Price'] = stock_int_peak_price
        dict_stock_profit_loss['Trailing Stop Price'] = stock_int_trailing_stop_price
        dict_stock_profit_loss['Sell Price'] = stock_int_selling_price
        dict_stock_profit_loss['PL %'] = stock_int_final_profit_loss_percent
        dict_stock_profit_loss['Remark'] = stock_str_remark
        dict_stock_profit_loss['Sell Date'] = stock_dt_selling_date
        dict_stock_profit_loss['Days'] = stock_int_days_hold
        

    print('--- will return following summary')
    print(dict_stock_profit_loss)
    print()

    print('--- will return following detail')
    print(df_stock_analysis)
    print()
    
    return dict_stock_profit_loss, df_stock_analysis;


# simulate for certain trailing stop
def execute_backtest(int_p_ts, int_p_sma):

    str_filename = 'saham_ipo-TS_' + str(int_p_ts) + '%-SMA_' + str(int_p_sma) + '.xlsx'

    print('//////////')
    print('Prepare ExcelWriter for', str_filename)
    xlsx_writer = pd.ExcelWriter(str_filename, mode='w')
    print('....................')
    print()

    list_stocks_pl_insight_dict = []
    for i in backtest_stocks_list:
        str_symbol = i[0]
        int_ipo_price = i[1]

        print('//////////')
        print('Verify stock [' + i[0] + '] OK')
        dict_stock_profit_loss, df_stock_detail = get_dict_stock_pl_backtest(str_symbol, int_ipo_price, int_p_ts, int_p_sma)
        print('--- returned summary ')
        print(dict_stock_profit_loss)
        print()
        print('--- returned detail ')
        print(df_stock_detail)
        print()

        if backtest_params_dict[PARAM_SAVE_STOCK_DATA]:
            print('Writing to Excel', end=' ')
            df_stock_detail.to_excel(xlsx_writer, sheet_name=str_symbol)
            xlsx_writer.save()
            print('--- DONE')
            print()

        print('....................')
        print()
        list_stocks_pl_insight_dict.append(dict_stock_profit_loss)

    print()

    print('//////////')
    print('wrapped up for IPO stocks P/L')
    list_header = list_stocks_pl_insight_dict[0].keys()
    list_rows = [x.values() for x in list_stocks_pl_insight_dict]
    print(tabulate.tabulate(list_rows, list_header))
    print('....................')
    print()

    print('//////////')
    print('Writing P/L summary to Excel', end=' ')
    df_stocks_pl_insight = pd.DataFrame(list_stocks_pl_insight_dict)
    df_stocks_pl_insight.sort_values(by=['PL %'], axis = 0, ascending = True, inplace = True, na_position ='last')
    list_stocks_pl_insight = get_list_stock_pl_insight(df_stocks_pl_insight, 500, int_p_sma)
    df_stocks_pl_insight = pd.concat([df_stocks_pl_insight, pd.DataFrame(list_stocks_pl_insight)])
    df_stocks_pl_insight.to_excel(xlsx_writer, sheet_name='Summary' )
    print('--- DONE')
    print()

    print('Closing Excel', end=' ')
    xlsx_writer.close()
    print('--- DONE')

    return None


# get ticks for a stock
def retrieve_all_stocks_ticks():
    print('//////////')
    print('Writing raw data to Excel saham_ipo-harian.xlsx')
    print()
    
    print('Preparing ExcelWriter', end=' ')
    xlsx_writer = pd.ExcelWriter('saham_ipo-harian.xlsx', mode='w')
    print('--- DONE')
    print()

    for i in backtest_stocks_list:
        
        print('Fetching data for [' + i[0] + ']', end =' ')
        stock_ticker = yf.Ticker(str(i[0]) + '.JK')
        stock_data_df = stock_ticker.history(period=backtest_params_dict[PARAM_HISTORY_PERIOD], interval=backtest_params_dict[PARAM_TICK_INTERVAL])
        print('--- DONE')

        for x in backtest_sma_sl_list:
            print('Adding TA indicators SMA-', x, end=' ')
            stock_data_df.insert(len(stock_data_df.columns), 'SMA_' + str(x), 0)
            stock_data_df.ta.sma(length=x, append=True)
            print('--- DONE')
        
        print('Writing raw data to Excel', end=' ')
        stock_data_df.to_excel(xlsx_writer, sheet_name=i[0])        
        xlsx_writer.save()
        print('--- DONE')
        print()

        all_stocks_ticks_df_dict[i[0]] = stock_data_df

    print('Closing Excel', end=' ')
    xlsx_writer.close()
    print('--- DONE')
    print()

    for x in all_stocks_ticks_df_dict:
        print('//////////')
        print('Verbose stock data [' + x + '] OK')
        print()
        print(all_stocks_ticks_df_dict[x])
        print('....................')
        print()

    print()

    return None


# load backtest params from Excel
def load_backtest_params():

    str_filename = 'saham_ipo-backtest.xlsx'

    print('//////////')
    print('Loading params from Excel', str_filename)
    print()

    print('Loading params', end=' ')
    df_backtest_params = pd.read_excel(str_filename, sheet_name='Params')
    print('--- DONE')
    print('Loaded from Excel', "\n", df_backtest_params)
    
    for i in df_backtest_params.index:
        backtest_params_dict[df_backtest_params.at[i, 'Param Name']] = df_backtest_params.at[i, 'Param Value']
    
    print('Converted from Excel', "\n", backtest_params_dict)
    print()

    print('Loading list of stocks', end=' ')
    df_stocks_list = pd.read_excel(str_filename, sheet_name='Stocks')
    print('--- DONE')
    print('Loaded from Excel', "\n", df_stocks_list)
    backtest_stocks_list.extend(df_stocks_list.values.tolist())
    print('Converted from Excel', "\n", backtest_stocks_list)
    print()

    print('Loading trailing SL strategies', end=' ')
    df_trailing_sl_list = pd.read_excel(str_filename, sheet_name='Trailing SL')
    print('--- DONE')
    print('Loaded from Excel', "\n", df_trailing_sl_list)
    backtest_trailing_sl_list.extend(df_trailing_sl_list['Trailing SL'].values.tolist())
    print('Converted from Excel', "\n", backtest_trailing_sl_list)
    print()

    print('Loading SMA SL strategies', end=' ')
    df_sma_sl_list = pd.read_excel(str_filename, sheet_name='SMA SL')
    print('--- DONE')
    print('Loaded from Excel', "\n", df_sma_sl_list)
    backtest_sma_sl_list.extend(df_sma_sl_list['SMA SL'].values.tolist())
    print('Converted from Excel', "\n", backtest_sma_sl_list)
    print()

    return None


def main():
    # stock with trailing stop

    # retrieve backtest params from Excel
    load_backtest_params()

    # retrieve from Yahoo
    retrieve_all_stocks_ticks()

    # backtest the strategy based-on various Trailing SL & SMA SL.
    for int_ts in backtest_trailing_sl_list:
        execute_backtest(int_ts, 0)

    for int_sma in backtest_sma_sl_list:
        execute_backtest(0, int_sma)

    for int_ts in backtest_trailing_sl_list:
        for int_sma in backtest_sma_sl_list:
            execute_backtest(int_ts, int_sma)

    print()

    # write all insights to Excel
    print('//////////')
    print('Writing to ExcelWriter for all insights', end=' ')
    str_filename = 'saham_ipo-insights.xlsx'
    pd.DataFrame(all_stocks_pl_insight_dict_list).to_excel(str_filename)
    print('--- DONE')
    print()

    return None    


# MAIN ---------------------------------------------------------------------------------------------------------------

main()