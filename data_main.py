from data_extract import *
from data_preparation import *

if __name__ == '__main__':
    print("加载文件...")
    raw_text_list = get_text_list()
    print("准备完成.")
    print("一共有",len(raw_text_list),"篇文档")
    dic={"1":"网址1",
         "2": "网址2",
         "3": "http版本",
         }

    while True:
        print("可供选择抽取信息如下：\n"
              "1:网址1 2:网址2 3:http版本\n"
              "请输入抽取信息序号,或输入0退出")
        extracNum = input("> ")

        if extracNum == '0':
            print('Bye')
            exit(0)
        print("检测到的结果：", dic[extracNum])
        result = find(raw_text_list,int(extracNum))

