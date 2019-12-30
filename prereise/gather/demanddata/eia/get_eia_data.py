import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pandas as pd
from pandas.tseries.offsets import DateOffset


def from_download(tok, start_date, end_date, offset_days, series_list):
    """Downloads and assemble dataset of demand data per balancing authority \
        for desired date range.

    :param str tok: token obtained by registering with EIA.
    :param datetime.datetime start_date: start date.
    :param datetime.datetime end_date: end data.
    :param list series_list: list of demand series names provided by EIA, e.g.,
        ['EBA.AVA-ALL.D.H', 'EBA.AZPS-ALL.D.H'].
    :param int offset_days: number of business days for data to stabilize.
    :return: (*pandas.DataFrame*) -- data frame indexed with hourly UTC time and
        BA series name for column names.
    """

    timespan = pd.date_range(start_date,
                             end_date - DateOffset(days=offset_days),
                             freq='H')
    df_all = pd.DataFrame(index=timespan)

    for ba in series_list:
        print('Downloading', ba)
        d = EIAgov(tok, [ba])
        df = d.get_data()
        df.index = pd.to_datetime(df['Date'])
        df.drop(columns=['Date'], inplace=True)
        df_all = pd.concat([df_all, df], axis=1)

    return df_all


def from_excel(directory, series_list, start_date, end_date):
    """Assembles EIA balancing authority (BA) data from pre-downloaded Excel
        spreadsheets. The spreadsheets contain data from July 2015 to present.

    :param str directory: location of Excel files.
    :param list series_list: list of BA initials, e.g., ['PSE',BPAT','CISO'].
    :param datetime.datetime start_date: desired start of dataset.
    :param datetime.datetime end_date: desired end of dataset.
    :return: (*pandas.DataFrame*) -- data frame indexed with hourly UTC time and
        BA series name for column names.
    """
    timespan = pd.date_range(start_date, end_date, freq='H')
    df_all = pd.DataFrame(index=timespan)

    for ba in series_list:
        print(ba)
        filename = ba + '.xlsx'
        df = pd.read_excel(io=os.path.join(directory, filename),
                           header=0, usecols='B,U')
        df.index = pd.to_datetime(df['UTC Time'])
        # Fill missing times
        df = df.resample('H').asfreq()
        df.drop(columns=['UTC Time'], inplace=True)
        df.rename(columns={"Published D": ba}, inplace=True)
        df_all = pd.concat([df_all, df], join='inner', axis=1)

    return df_all


def get_BA_demand(ba_code_list, start_date, end_date, api_key):
    """ Downloads the demand between the start and end dates for a list of BAs
        :param pandas.DataFrame ba_code_list: List of balancing authorities to download from eia
        :param datetime.datetime start_date: beginning bound for the demand dataframe
        :param datetime.datetime end_date: end bound for the demand dataframe
        :return: (*pandas.DataFrame*) -- dataframe with columns of demand by BA
    """
    series_list = [f'EBA.{ba}-ALL.D.H' for ba in ba_code_list]
    return from_download(api_key, start_date, end_date, offset_days=0, series_list=series_list)


class EIAgov(object):
    """Copied from `this link <https://quantcorner.wordpress.com/\
        2014/11/18/downloading-eias-data-with-python/>`_.

    :param str token: EIA token.
    :param list series: id code(s) of the series to be downloaded.
    """

    def __init__(self, token, series):
        self.token = token
        self.series = series

    def raw(self, ser):
        """Downloads json files from EIA.

        :param str ser: list of filenames.
        :raises keyError: when URL or file are either not found or not valid.
        """

        url = ('http://api.eia.gov/series/?api_key='
               + self.token + '&series_id=' + ser.upper())

        try:
            response = urlopen(url)
            raw_byte = response.read()
            raw_string = str(raw_byte, 'utf-8-sig')
            jso = json.loads(raw_string)
            return jso

        except HTTPError as e:
            print('HTTP error type.')
            print('Error code: ', e.code)

        except URLError as e:
            print('URL type error.')
            print('Reason: ', e.reason)

    def get_data(self):
        """Converts json files into data frame.

        :return: (*pandas.DataFrame*) -- data frame.
        """

        date_ = self.raw(self.series[0])
        date_series = date_['series'][0]['data']
        endi = len(date_series)
        date = []
        for i in range(endi):
            date.append(date_series[i][0])

        df = pd.DataFrame(data=date)
        df.columns = ['Date']

        lenj = len(self.series)
        for j in range(lenj):
            data_ = self.raw(self.series[j])
            data_series = data_['series'][0]['data']
            data = []
            endk = len(date_series)
            for k in range(endk):
                data.append(data_series[k][1])
            df[self.series[j]] = data

        return df


