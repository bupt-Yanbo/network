import re

from jieba import analyse


def extract_1(data):

    res=re.findall(r'nLocation[^\\]*',data,0)

    return res


def extract_3(data):

    res=re.findall(r'HTTP/[^\\]*',data,0)

    return res

def extract_2(data):

    res=re.findall(r'[A-Za-z]+\.[A-Za-z]+\.[A-Za-z]+',data,0)

    return res

def extract_4(data):

    res=re.findall(r'nCookie[^\\]*',data,0)

    return res

def extract_5(data):

    res=re.findall(r'[^\\]*Host[^\\]*',data,0)

    return res

def extract_6(data):

    res=re.findall(r'[^\\]*Connection[^\\]*',data,0)

    return res


def extract_7(data):

    res=re.findall(r'[^\\]*User-Agent[^\\]*',data,0)

    return res

def extract_8(data):

    res=re.findall(r'[^\\]*nAccept-Encoding:[^\\]*',data,0)

    return res


def extract_9(data):
    res =re.findall(r'[A-Za-z][^\\]*[A-Za-z][^\\]*[A-Za-z][^\\]*[A-Za-z][^\\]*[A-Za-z][^\\]*[A-Za-z][^\\]*[A-Za-z][^\\]*',data,0)
    return res

def choose_part(choice,temp):
    if choice == 1:
        part = extract_1(temp)
    elif choice == 2:
        part = extract_2(temp)
    elif choice == 3:
        part = extract_3(temp)
    elif choice == 4:
        part = extract_4(temp)
    elif choice == 5:
        part = extract_5(temp)
    elif choice == 6:
        part = extract_6(temp)
    elif choice == 7:
        part = extract_7(temp)
    elif choice == 8:
        part = extract_8(temp)
    elif choice == 9:
        part = extract_9(temp)
    return part


def find(datas,choice):
    check(datas, choice)
    data_len=len(datas)
    for i in range(0,data_len):
        temp=datas[i]
        part=choose_part(choice,temp)
        if(standard(part)!="NULL"):
            print("第",i,"个文件： ",standard(part))
    check(datas, choice)

def check(datas,choice):
    if choice >7:
        return
    data_len = len(datas)
    if_exist=[]
    for i in range(0, data_len):
        temp = datas[i]
        part=choose_part(choice,temp)
        res=standard(part)
        if res != "NULL":
            if_exist.append(i)
    print("在文件",if_exist)
    print("中存在，共",len(if_exist),"个文件")


def standard(sentence):
    temp=str(sentence)
    temp=temp.replace('(',"")
    temp = temp.replace(')', "")
    temp = temp.replace('[', "")
    temp = temp.replace(']', "")
    temp = temp.replace('\'', "")
    if(len(temp)<1):
        temp="NULL"
    return temp