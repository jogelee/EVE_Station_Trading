# Program: market.py
# John Lee

# Description: Pulls Jita 4-4 market data through the EVE API, and calculates margins, average volumes, profitability, and an efficiency score.

import csv
import numpy as np
import requests
import datetime

print('START: ' + str(datetime.datetime.now()))

FORGE = 10000002
JITA44 = 60003760

min_avg_vol = 250
max_avg_vol = 12000
profit_threshold = 15000000
score_threshold = 0.55

types = []
orders = []
orders_dict = {}
output = []

# outlier calculator by Dr. Andrii Gakhov from DATACRUCIS
def is_outlier(value, p25, p75):
    lower = p25 - 1.5 * (p75 - p25)
    upper = p75 + 1.5 * (p75 - p25)

    return value <= lower or value >= upper

def get_indices_of_outliers(values):
    p25 = np.percentile(values, 25)
    p75 = np.percentile(values, 75)

    indices_of_outliers = []
    for ind, value in enumerate(values):
        if is_outlier(value, p25, p75):
            indices_of_outliers.append(ind)
    return indices_of_outliers

# call reference list of type names and IDs
typeids = csv.reader(open('typeids.csv'))
for row in typeids:
    types.append(row)

# number of pages
response = requests.get('https://esi.tech.ccp.is/latest/markets/' + str(FORGE) + '/orders/?datasource=tranquility&order_type=all&page=1')
pages = int(response.headers['X-Pages'])

# filter Forge market orders that aren't from Jita 4-4
for i in range(1, pages + 1):
    page = requests.get('https://esi.tech.ccp.is/latest/markets/' + str(FORGE) + '/orders/?datasource=tranquility&order_type=all&page=' + str(i))
    json = page.json()
    for j in json:
        if j['location_id'] == JITA44:
            orders.append(j)

# split orders by buy and sell, in a dictionary
for i in orders:
    type_id = i['type_id']
    buy = i['is_buy_order']
    if type_id in orders_dict:
        if buy:
            orders_dict[type_id][0].append(i['price'])
        else:
            orders_dict[type_id][1].append(i['price'])
    else:
        if buy:
            orders_dict[type_id] = [[i['price']],[]]
        else:
            orders_dict[type_id] = [[],[i['price']]]

# sort through orders
for i in orders_dict:

    # name from type ID references
    type_id = ''
    for j in types:
        if i == int(j[0]):
            type_id = j[1]
            break
    if type_id != '':

        # buy, sell, margin
        try:
            buy = max(orders_dict[i][0])
        except:
            buy = 0
        try:
            sell = min(orders_dict[i][1])
        except:
            sell = 0
        margin = sell - buy

        # efficiency score
        try:
            score = round(margin / buy, 5)
        except:
            score = 0

        # pull market volume history
        try:
            history = requests.get('https://esi.tech.ccp.is/latest/markets/' + str(FORGE) + '/history/?datasource=tranquility&type_id=' + str(i))
            json = history.json()
        except:
            json = False
        if json != False:

            # last 30 days of history
            count = 0
            vol_list = []
            for j in range(1, 31):
                try:
                    vol_list.append(json[len(json) - j]['volume'])
                    count += 1
                except:
                    break
            if (vol_list != []) & (0 not in vol_list):

                # remove outliers in volume history
                outliers = get_indices_of_outliers(vol_list)
                count -= len(outliers)
                total_vol = 0.0
                for j in range(0, len(vol_list)):
                    if j not in outliers:
                        total_vol += vol_list[j]

                # average volume
                try:
                    avg_vol = total_vol / count
                except:
                    avg_vol = 0.0

                # potential profit
                profit = avg_vol / 2.5 * margin

                # filter by thresholds
                if (min_avg_vol < avg_vol < max_avg_vol) & (profit > profit_threshold) & (score > score_threshold):
                    output.append([type_id, buy, sell, margin, int(round(avg_vol)), profit, score])

output.insert(0, ['TYPE', 'BUY', 'SELL', 'MARGIN', 'AVG VOL', 'PROFIT', 'MARGIN/BUY'])

# output as csv
with open('JITA ' + str(datetime.date.today()) + '.csv', 'w', newline = '') as outputcsv:
    writer = csv.writer(outputcsv)
    writer.writerows(output)

print('END: ' + str(datetime.datetime.now()))