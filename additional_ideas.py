#-*- coding:UTF-8 -*-
import sqlite3
from pprint import pprint

def pretty_print(table):
    for line in table:
        for ele in line:
            print ele,'|',
        print

con = sqlite3.connect('chaozhoucity.db')
cur = con.cursor()

cur.execute("select * from nodes_tags where key = 'street';")
nodes_tags_street = cur.fetchall()

for tu in nodes_tags_street:
    if len(tu[2]) > 20:
        print tu[0], '|', tu[2]

cur.execute("select value from nodes, nodes_tags where nodes.id = nodes_tags.id and nodes.id = 4828099522  ")
nodes_tags_street_long = cur.fetchall()
pretty_print(nodes_tags_street_long)

con.close()
