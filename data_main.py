from data_extract import *
from data_preparation import *

if __name__ == '__main__':
    print("加载文件...")
    raw_text_list = get_text_list()
    print("准备完成.")
    print("一共有",len(raw_text_list),"篇文档")
    dic={"1":"网页信息",
         "2": "域名",
         "3": "http版本",
         "4":"Cookie",
         "5":"host",
         "6":"Connection",
         "7":"User - Agent",
         "8":"Accept - Encoding",
         "9": "信息汇总"
         }

    while True:
        print("可供选择抽取信息如下：\n"
              "1网址1 2网址2 3http版本 4Cookie 5host 6Connection 7User-Agent 8Accept-Encoding 9信息汇总\n"
              "请输入抽取信息序号,或输入0退出")
        extracNum = input("> ")

        if extracNum == '0':
            print('Bye')
            exit(0)
        print("检测到的结果：", dic[extracNum])
        result = find(raw_text_list,int(extracNum))

