#!/usr/bin/env python
# -*- coding: utf-8 -*-
# code whose function is parsing osm file to csv file refer to the original Case Study scripts.

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "chaozhoucity.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
SUBTRACT = re.compile(r'\-')
WHITESPACE = re.compile(r'\s')
BRACKET = re.compile(r'\)')

SCHEMA = schema.schema

#the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def update_phone(phone):
    """check the phone which has problem pattern and update it"""

    if phone.startswith("0"):
        # remove initial "0" from string
        phone = phone.lstrip("0")
    if BRACKET.search(phone):
        # remove "(0)" in the middle of string
        phone = phone.replace("(0)", "")
    if SUBTRACT.search(phone):
        # remove "-" in the middle of string
        phone = phone.replace("-", "")
    if WHITESPACE.search(phone):
        # remove all whitespace in string
        phone = phone.replace(" ", "")
    if len(phone) == 11 or len(phone) == 10:
        # add "+86" for moilephone phone number(11-digit) and landline number(10-digit) which without "86"
        phone = "+86" + phone
    if not phone.startswith("+"):
        # add "+" for string wfieldhich has "86" without "+"
        phone = "+" + phone
    if len(phone) == 13:
        # make landline number(13-digit) format consistent
        phone = phone[:3] + ' ' + phone[3:6] + ' ' + phone[6:]
    if len(phone) == 14:
        # make mobilephone number(14-digit) format consistent
        phone = phone[:3] + ' ' + phone[3:]
    return phone




def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    n = 0
    
    if element.tag == 'node':
        # get nodes attributes only within NODE_FIELDS 
        for node_field in node_attr_fields:
            node_attribs[node_field] = element.get(node_field)
        for t in element:
            tag = {}
            tag['id'] = node_attribs['id']
            t_k = t.get("k")
            # if the tag "k" value contains problematic characters, ignore the tag 
            if PROBLEMCHARS.search(t_k) == None:
                 '''
                    if the tag "k" value contains a ":", set the characters before the ":" 
                    as the tag type and set characters after the ":" as the tag key.
                    if there are additional ":" in the "k" value, ignored them and kept as part of the tag key. 
                 '''
                if LOWER_COLON.search(t_k) != None:
                    t_split = t.get("k").split(":",1)
                    t_key = t_split[1]
                    t_type = t_split[0]
                    tag['key'] = t_key
                    tag['type'] = t_type
                    tag['value'] = t.get("v")
                else:
                    tag['key'] = t_k
                    tag['type'] = default_tag_type
                    if t_k == "phone":
                    # if tag's key is "phone", audit tag's value and updated it.
                        tag['value'] = update_phone(t.get('v'))
                    else:
                        tag['value'] = t.get("v")
            tags.append(tag)
        return {'node': node_attribs, 'node_tags': tags}
    
    elif element.tag == 'way':
        for way_field in way_attr_fields:
            way_attribs[way_field] = element.get(way_field)
        for child in element:
            # seperate two tag types
            if child.tag == 'nd':
                way_node = {}
                way_node['id'] = way_attribs['id']
                way_node['node_id'] = child.get('ref')
                way_node['position'] = n
                n += 1
                way_nodes.append(way_node)
            elif child.tag == 'tag':
                tag = {}
                tag['id'] = way_attribs['id']
                
                t_k = child.get("k")
                if PROBLEMCHARS.search(t_k) == None:
                    if LOWER_COLON.search(t_k) != None:
                        t_split = child.get("k").split(":",1)
                        t_key = t_split[1]
                        t_type = t_split[0]
                        tag['key'] = t_key
                        tag['type'] = t_type
                        tag['value'] = child.get("v")
                    else:
                        tag['key'] = t_k
                        tag['type'] = default_tag_type
                        if t_k == "phone":
                            tag['value'] = update_phone(child.get('v'))
                        else:
                            tag['value'] = child.get("v")
                tags.append(tag)




        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}



# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    process_map(OSM_PATH, validate=True)
