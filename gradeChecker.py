import json
import requests
from bs4 import BeautifulSoup
import mysql.connector
import schedule
import os
from dotenv import load_dotenv

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 "
                  "Safari/537.36",
}

load_dotenv()


aibu_login_data = {
     'X-Requested-With': 'XMLHttpRequest'
}

login_mysql = mysql.connector.connect(
    host=os.getenv("host"),
    user=os.getenv("user"),
    password=os.getenv("password"),
    port=os.getenv("port")
)

mycursor = login_mysql.cursor()
mycursor.execute("CREATE DATABASE IF NOT EXISTS %s" % os.getenv("database"))


class Login:
    def __init__(self):
        self.users={}
        self.token_value = None
        self.changing_dataa = None
        self.url = "https://ubys.ibu.edu.tr"
        self.s = requests.Session()
        load_dotenv()
        self.db = mysql.connector.connect(
            host=os.getenv("host"),
            user=os.getenv("user"),
            password=os.getenv("password"),
            port=os.getenv("port"),
            database=os.getenv("database")
        )
    def getUsers(self):
        mycursor = self.db.cursor(buffered=True, dictionary=True)
        mycursor.execute(
            "CREATE TABLE IF NOT EXISTS users(id int PRIMARY KEY AUTO_INCREMENT,username VARCHAR(50),"
            "password VARCHAR(100))")
        mycursor.execute("SELECT * FROM users")
        self.users = mycursor.fetchall()

    def getUser(self,userId):
        for i in range(len(self.users)):
            global user
            user=self.users[i]
            # print(user['id'])
            if user["id"] == userId:
                return user

    def log_in(self,userId):
        user=self.getUser(userId)
        aibu_login_data['username']=user["username"]
        aibu_login_data['password']=user["password"]
        self.s.post(self.url + '/Account/Login', headers=header, data=aibu_login_data)
        # self.loginDB(userId)

    def loginDB(self,userId):
        mycursor=self.db.cursor(buffered=True)
        mycursor.execute("CREATE TABLE IF NOT EXISTS lessons(id int PRIMARY KEY AUTO_INCREMENT,lessonName VARCHAR(50))")
        mycursor = self.db.cursor(buffered=True)
        mycursor.execute(
            "CREATE TABLE IF NOT EXISTS user_grades(id int PRIMARY KEY AUTO_INCREMENT,user_id int,lesson_id int,FOREIGN KEY (user_id) REFERENCES users(id),FOREIGN KEY(lesson_id) REFERENCES lessons(id),"
            "exam_results VARCHAR(100))")
        # mycursor.execute("SELECT id from USERS")
        # user_id_tuple=mycursor.fetchone()
        # print(user_id_tuple)
        # user_id_str="".join(map(str,user_id_tuple))
        get_sapid = self.s.get("https://ubys.ibu.edu.tr/AIS/Student/Calender/Index").text
        soup = BeautifulSoup(get_sapid, 'lxml')
        # print(soup)
        sapid = soup.find('a', onclick=True)
        sapid = sapid['onclick'].split("'")[1]

        res = self.s.get(
            'https://ubys.ibu.edu.tr/AIS/Student/Class/Index?sapid=' + sapid).text
        soup = BeautifulSoup(res, 'lxml')
        pair = 0
        odd = 1
        print("---------------------------------------")

        tr_text = soup.find('tbody').find_all('tr', recursive=False)
        count_of_tr = str(tr_text).count("<tr>")

        while pair < count_of_tr / 2:
            lesson_name = soup.find('tbody').find_all('tr', recursive=False)[pair].find_all_next('td')[1].text
            pair = pair + 2

            exam_results = soup.find('tbody').find_all('tr', recursive=False)[odd].find_next('td').text
            odd = odd + 2

            mycursor.execute("SELECT id FROM lessons WHERE lessonName=%s", (lesson_name,))
            db_fetched3=mycursor and mycursor.fetchone()
            lesson_id=db_fetched3 and db_fetched3[0]

            if lesson_id==None:
                mycursor.execute("INSERT INTO lessons(lessonName) VALUES(%s)",(lesson_name,))
            else:
                pass

            mycursor.execute("SELECT id FROM users WHERE username=%s", (user["username"],))
            db_fetched2 = mycursor and mycursor.fetchone()
            db_userId = db_fetched2 and db_fetched2[0]

            mycursor.execute("SELECT exam_results FROM user_grades WHERE lesson_id=%s AND user_id=%s", (lesson_id,db_userId))
            # print(user["username"])
            db_fetched = mycursor and mycursor.fetchone()  # if the left one is not none or false then the right one works.
            db_data = db_fetched and db_fetched[0]

            # mycursor.execute("SELECT id FROM users WHERE username=%s", (user["username"],))
            # db_fetched2=mycursor and mycursor.fetchone()
            # db_userId=db_fetched2 and db_fetched2[0]

            mycursor.execute("SELECT lessonName FROM lessons WHERE id=%s",(lesson_id,))
            db_fetched4=mycursor and mycursor.fetchone()
            db_lessonName=db_fetched4 and db_fetched4[0]

            if db_data is None or db_userId!=userId:
                mycursor.execute("SELECT id FROM lessons WHERE lessonName=%s", (lesson_name,))
                db_fetched3 = mycursor and mycursor.fetchone()
                lesson_id2 = db_fetched3 and db_fetched3[0]
                mycursor.execute("INSERT INTO user_grades(user_id,lesson_id,exam_results) VALUES (%s,%s,%s)",
                                 (userId,lesson_id2,exam_results))
                self.db.commit()

            if exam_results == db_data and db_userId==userId:
                 mycursor.execute("UPDATE user_grades SET exam_results=%s WHERE lesson_id=%s AND user_id=%s", (exam_results,lesson_id,db_userId))
                 self.db.commit()

            if exam_results!=db_data and db_data is not None :
                mycursor.execute("UPDATE user_grades SET exam_results=%s,user_id=%s WHERE lesson_id=%s", (exam_results,userId,lesson_id))
                self.db.commit()
                mycursor.execute("SELECT lessons.lessonName,user_grades.exam_results FROM lessons JOIN user_grades ON user_grades.lesson_id=lessons.id WHERE lessons.id=%s ", (lesson_id,))
                changing_data = mycursor.fetchone()
                self.changing_dataa = "".join(changing_data)
                # print(self.changing_dataa)
                # print(type(self.changing_dataa))
                self.pushNotification()

    def pushNotification(self):
        url = "https://onesignal.com/api/v1/notifications"

        payload = {
            "app_id": "%s" % os.getenv("app_id"),
            "included_segments": ["Subscribed Users"],
            "contents": {
                "en": self.changing_dataa
            },
            "headings": {"en": "Your Note is Announced"},
            "name": "GradeChecker",
        }

        headers = {
            "Accept": "application/json",
            "Authorization": "Basic %s" % os.getenv("Authorization"),
            "Content-Type": "application/json"
        }

        requests.post(url, json=payload, headers=headers)

    def getToken(self):
        res = self.s.get(self.url).text
        soup = BeautifulSoup(res, 'html5lib')
        self.token_value = soup.find('input', attrs={'name': '__RequestVerificationToken'}).get('value')
        aibu_login_data['__RequestVerificationToken'] = self.token_value
        # print(self.token_value)

    def login(self):
        print("Logging into the Site...")
        self.getToken()
        print("---------------------------------------")
        self.getUsers()
        self.getUser(1)
        self.log_in(1)
        self.loginDB(1)
        # self.s.post(self.url + '/Account/Login', headers=header, data=aibu_login_data)
        print("Logging into the Database...")
        # self.loginDB()
        # self.get_login_data_from_mysql()

Login().login()


# def log():
#     Login().login()
#
#
# schedule.every(2).seconds.do(log)
#
# while True:
#     schedule.run_pending()
