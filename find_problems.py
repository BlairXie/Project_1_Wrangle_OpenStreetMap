import xml.etree.cElementTree as ET
import pandas as pd

OSM_FILE = 'chaozhoucity.osm'
# align the dataframe column display
pd.set_option('display.unicode.east_asian_width', True) 


def tag_key_value(input_file, k):
    """find the value and its amount correspond to key"""

    value = {}
    for event, elem in ET.iterparse(input_file):
        if event == 'end':
            if elem.get('k') == k:
                k_value = elem.get('v')
                try:
                    # if the key already exist, key's amount += 1
                    value[k_value] += 1
                except KeyError:
                    # if the key does not exist, key's amount = 1
                    value[k_value] = 1  
        elem.clear() # discard element 

    # make a dataframe consist of value and its amount  
    value_df = pd.DataFrame(value, index=['amount']).T

    return value_df 

if __name__ == '__main__':

    phone_value_df = tag_key_value(OSM_FILE,"phone")
    street_value_df = tag_key_value(OSM_FILE, "addr:street")
    city_value_df = tag_key_value(OSM_FILE, "addr:city")

# check key_value dataframe 
# phone_value_df
# street_value_df
# city_value_df
