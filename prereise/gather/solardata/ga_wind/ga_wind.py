from collections import OrderedDict

import dateutil
import h5pyd
import numpy as np
import pandas as pd
from tqdm import tqdm

from prereise.gather.solardata.ga_wind.helpers import ll2ij
from prereise.gather.solardata.helpers import get_plant_info_unique_location


def retrieve_data(solar_plant, hs_api_key, start_date='2007-01-01',
                  end_date='2014-01-01'):
    """Retrieves irradiance data from Gridded Atmospheric Wind Integration
        National dataset.

    :param pandas.DataFrame solar_plant: data frame with *'lat'*, *'lon'* and
        *'Pmax'* as columns and *'plant_id'* as indices.
    :param str hs_api_key: API key.
    :param str start_date: start date.
    :param str end_date: end date.
    :return: (*pandas.DataFrame*) -- data frame with *'Pout'*, *'plant_id'*,
        *'ts'* and *'ts_id'* as columns. The power output is in MWh.
    """

    # Identify unique location
    coord = get_plant_info_unique_location(solar_plant)

    # Build query
    hs_endpoint = 'https://developer.nrel.gov/api/hsds/'
    hs_username = None
    hs_password = None

    f = h5pyd.File("/nrel/wtk-us.h5", 'r',
                   username=hs_username,
                   password=hs_password,
                   endpoint=hs_endpoint,
                   api_key=hs_api_key)

    # Get coordinates of nearest location
    lat_origin, lon_origin = f['coordinates'][0][0]
    ij = {}
    for key in coord.keys():
        ij[key] = ll2ij(lon_origin, lat_origin, float(key[0]), float(key[1]))

    # Extract time series
    dt = f['datetime']
    dt = pd.DataFrame({'datetime': dt[:]})
    dt['datetime'] = dt['datetime'].apply(dateutil.parser.parse)

    dt_range = dt.loc[(dt.datetime >= start_date) & (dt.datetime < end_date)]

    data = pd.DataFrame({'Pout': [], 'plant_id': [], 'ts': [], 'ts_id': []})

    for (key, val) in tqdm(ij.items(), total=len(ij)):
        ghi = f['GHI'][min(dt_range.index):max(dt_range.index)+1,
                       val[0], val[1]]
        data_loc = pd.DataFrame({'Pout': ghi})
        data_loc['Pout'] /= max(ghi)
        data_loc['ts_id'] = range(1, len(ghi)+1)
        data_loc['ts'] = pd.date_range(start=start_date,
                                       end=end_date,
                                       freq='H')[:-1]

        for i in coord[key]:
            data_site = data_loc.copy()
            data_site['Pout'] *= i[1]
            data_site['plant_id'] = i[0]

            data = data.append(data_site, ignore_index=True, sort=False)

    data['plant_id'] = data['plant_id'].astype(np.int32)
    data['ts_id'] = data['ts_id'].astype(np.int32)

    data.sort_values(by=['ts_id', 'plant_id'], inplace=True)
    data.reset_index(inplace=True, drop=True)

    return data
