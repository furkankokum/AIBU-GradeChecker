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

aibu_login_data = {
    'username': '193405044',
    'password': 'Fdk5800?',
    'X-Requested-With': 'XMLHttpRequest'
}

load_dotenv()
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

    def loginDB(self):
        mycursor = self.db.cursor(buffered=True)
        mycursor.execute(
            "CREATE TABLE IF NOT EXISTS lesson_exams(lessonID int PRIMARY KEY AUTO_INCREMENT,lessonName VARCHAR(50),"
            "exam_results VARCHAR(100))")

        get_sapid = self.s.get("https://ubys.ibu.edu.tr/AIS/Student/Home/Index").text
        soup = BeautifulSoup(get_sapid, 'lxml')

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
            mycursor.execute("SELECT exam_results FROM lesson_exams WHERE lessonName=%s", (lesson_name,))

            db_fetched = mycursor and mycursor.fetchone()  # if the left is not none or false then the right one works.
            db_data = db_fetched and db_fetched[0]

            if db_data is None:
                mycursor.execute("INSERT INTO lesson_exams(lessonName,exam_results) VALUES (%s,%s)",
                                 (lesson_name, exam_results))
                self.db.commit()

            if exam_results == db_data:
                mycursor.execute("UPDATE lesson_exams SET exam_results=%s WHERE lessonName=%s", (exam_results, lesson_name))
                self.db.commit()

            else:
                mycursor.execute("UPDATE lesson_exams SET exam_results=%s WHERE lessonName=%s", (exam_results, lesson_name))
                self.db.commit()
                mycursor.execute("SELECT lessonName,exam_results FROM lesson_exams WHERE lessonName=%s", (lesson_name,))
                changing_data = mycursor.fetchone()
                self.changing_dataa = "".join(changing_data)
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
        aibu_login_data['__RequestVerificationToken'] = \
            soup.find('input', attrs={'name': '__RequestVerificationToken'})[
                'value']

    def login(self):
        print("Logging into the Site...")
        self.getToken()
        print("---------------------------------------")
        self.s.post(self.url + '/Account/Login', headers=header, data=aibu_login_data)
        print("Logging into the Database...")
        self.loginDB()


def log():
    Login().login()


schedule.every(1).seconds.do(log)

while True:
    schedule.run_pending()
