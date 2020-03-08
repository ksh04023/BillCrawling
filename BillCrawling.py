import os
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import requests #cmd에서 pip install해줘야함
import datetime
from datetime import timedelta
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db as db
import codecs
#python manage.py runserver 0.0.0.0:8080 로 하기 cmd에서
# bot = telegram.Bot(token='123412345:ABCDEFgHiJKLmnopqr-0StUvwaBcDef0HI4jk')
# # 우선 테스트 봇이니까 가장 마지막으로 bot에게 말을 건 사람의 id를 지정해줄게요.
# # 만약 IndexError 에러가 난다면 봇에게 메시지를 아무거나 보내고 다시 테스트해보세요.
# chat_id = bot.getUpdates()[-1].message.chat.id

class BillData:
    def __init__(self,dataTitle,billID,title,date,link,if_processed,content,coactor):
        self.dataTitle = dataTitle #DB에 저장할 이름 "(날짜) 제목"
        self.billID = billID #의안번호
        self.title = title #의안제목
        self.date = date #날짜
        self.link = link #URL
        self.if_processed = if_processed #True=처리의안, False=계류의안
        self.content = content #개요
        self.coactor = coactor #공동발의자
        #8개
        
cred = credentials.Certificate('C:/Users/user/motionCrawling/mycongressman3-firebase-adminsdk-g3tdk-1b129ac644.json') #이건모지
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mycongressman3.firebaseio.com/'
})

ref = db.reference('의안') #db 위치 지정
page = 1
#과거 시점부터 크롤링을 시작하여 현재 시점까지 진행한다.
def fetch_latest_data():
    path = "C:/Users/user/PythonProjects/chromedriver.exe"
    op = webdriver.ChromeOptions()
    op.add_argument('--headless')
    #driver = webdriver.Chrome(path)
    driver = webdriver.Chrome(path,options=op)
    driver.get("http://likms.assembly.go.kr/bill/BillSearchResult.do")
    driver.find_element_by_xpath("/html/body/div/div[2]/div[1]/div/div[2]/form[1]/div/div[6]/button[1]").click()


    ########################

    with open("C:/Users/user/PythonProjects/BillCrawling/latest.txt", 'r+',"utf-8") as f_read:
        before = f_read.readline()
        #최근 저장된 제목, 크롤링한 최근 발의안이랑 비교해서 이미 업데이트 된건지 알아볼예정, 한글이 안써져서 utf8을 추가햇느데 
        #안됨
        print("before: ", before)

    page = 1
    while page <= 5:
        page_script = "GoPage({0});".format(page)
        driver.execute_script(page_script)
        full_html = driver.page_source #현재 페이지의 모든 코드를 가져와라
        soup = BeautifulSoup(full_html,"html.parser")#스프한테 분석시킨다.
        page_num = soup.find("div",{"class":"paging"}).find("a",{"class":"on"}).text
        page = int(page_num)
        print(page_num)
        if page is not False:
            content_list=[]
            tags = soup.find("table").find("tbody").find_all("tr")
            print("num: ",page_num)
            print("t길이:",len(tags))
            #select('찾으려는 태그의 위치').find_all(태그) 해당 위치의 동일한 태그를 모두 찾는다.
            #xpath처럼 복사하여 찾을 수 있다.
            # if not tags:#태그가 존재하지 않을 경우 리스트 리턴
            # return content_list
            # else:
            for tag in tags: 
                #title,link
                try:
                    temp = tag.select('a')[0]
                    title = str(temp.text).strip()
                    #print("title:",title)
                except AttributeError:
                    print ("NO TITLE")


                try:
                    link = temp["href"]
                    pat = re.split("['']+",link)[1]
                    link = "http://likms.assembly.go.kr/bill/billDetail.do?billId" + pat
                    #print("link: ",link)
                except AttributeError:
                    print ("NO LINK")
                #"javascript:fGoDetail('PRC_H2G0X0Z2E0B7M1W6Z3L9R4A4U9V1O3', 'billSimpleSearch')"
                #if_process "처"or "계"
                try:
                    processed = tag.find("img",{"alt":"계"})["src"]
                    #처리면 True, 계류면 False
                    if "gye" in processed:
                        if_processed = False
                    else:
                        if_processed = True
                    #print("처리 or 계류: ",if_processed)
                except AttributeError:
                    print ("NO 계")

                #td들
                all_td = tag.find_all("td") #dd 텍스트형식으로 저장

                #의안번호
                billID = re.search("\d{5,}",all_td[0].text).string
                #print("id: ", billID)
                    
                #날짜
                date = re.search("\d{4}-\d{2}-\d{2}",all_td[3].text).string
                dataTitle = "("+date+")"+title
                #print("time: ",time)

                #의안 요약 링크
                try:
                    tempLink = all_td[6].select("a")[0]
                    link_td = re.split("['']+",tempLink["href"])[1]
                    content = "http://likms.assembly.go.kr/bill/summaryPopup.do?billId=" + link_td

                except:
                    content = "NO CONTENTS"
                    print("NO CONTENTS")
                #print("content: ",content)

                #공동발의자
                coactor = "http://likms.assembly.go.kr/bill/coactorListPopup.do?billId=" + link_td
                #링크 들어가서 텍스트로 받아와야댐!

                temp_data = BillData(dataTitle,billID,title,date,link,if_processed,content,coactor)
                content_list.append(temp_data)
                print(temp_data.dataTitle)
            print("latest: ",content_list[0].dataTitle)
            latest = content_list[0].dataTitle
            if before != latest:
            # 같은 경우는 에러 없이 넘기고, 다른 경우에만 수정
                for each in content_list:
                    each_object ={
                        "dataTitle" : each.dataTitle,
                        "billID" : each.billID,
                        "title" : each.title,
                        "date" : each.date,
                        "link" : each.link,
                        "if_processed" : each.if_processed,
                        "content": each.content,
                        "coactor" :each.coactor
                    }
                    ref.update({each.dataTitle: each_object})
                    #여기 오류,, 타입이 serializable 하지 않다는데
                with open("C:/Users/user/PythonProjects/BillCrawling/latest.txt", "w+","utf-8") as f_write:
                    f_write.write(latest)
                    f_write.close()
            else:
                print("Already updated")
                break
        page += 1

    return content_list #정상적으로 url을 받지 못했다면 리턴

if __name__ == "__main__":
    #add_new_items(fetch_latest_data())
    fetch_latest_data()