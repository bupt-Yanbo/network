import os
import re
import jieba
from sklearn.feature_extraction.text import CountVectorizer
from collections import defaultdict

path = 'netdata'
files = os.listdir(path)


def get_text_list():
    text_list = []

    for i in files:
        f = open(path + '\\' + i, encoding='utf-8')
        text = f.read()
        text_list.append(text)
    return text_list

