import os
import re

path = 'netdata'
files = os.listdir(path)


def get_text_list():
    text_list = []

    for i in files:
        f = open(path + '\\' + "write_data1.txt", encoding='utf-8')
        text = f.read()
        text_list.append(text)
    return text_list

