from flask import Flask, render_template, request, url_for, redirect, session
import requests
import credentials as cred
from flask_sqlalchemy import SQLAlchemy
import logging
import telegram
import json
import time
import datetime
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

def update_user_info(found_user, user_info):
     found_user.first_name = user_info[1]
     found_user.last_name = user_info[2]
     found_user.pfp_medium = user_info[3]
     found_user.pfp_large = user_info[4]
     return found_user

def get_user_info(authorization_code):
     client_id = cred.client_id
     client_secret = cred.client_secret
     url = "https://www.strava.com/oauth/token?client_id=" + client_id + "&client_secret=" + client_secret + "&code=" + authorization_code + "&grant_type=authorization_code"
     payload = {}
     headers= {}
     response = requests.request("POST", url, headers=headers, data=payload)
     return [response.json()['athlete']['id'], response.json()['athlete']['firstname'], response.json()['athlete']['lastname'], response.json()['athlete']['profile_medium'], response.json()['athlete']['profile'], response.json()['refresh_token']]

def get_new_tokens(refresh_token):
     client_id = cred.client_id
     client_secret = cred.client_secret
     url = "https://www.strava.com/oauth/token?client_id=" + client_id + "&client_secret=" + client_secret + "&refresh_token=" + refresh_token + "&grant_type=refresh_token"
     payload = {}
     headers = {
          'Cookie': '_strava4_session=bqrl6jvvidtv77mavtc2cg41cppuo6ab'
     }
     response = requests.request("POST", url, headers=headers, data=payload)
     return response.json()["access_token"]

def get_activities(access_token, page_number):
     url = "https://www.strava.com/api/v3/athlete/activities?access_token=" + access_token
     payload={'per_page': 200, 'page': page_number}
     headers = {'Cookie': '_strava4_session=bqrl6jvvidtv77mavtc2cg41cppuo6ab'}
     response = requests.request("GET", url, headers=headers, data=payload)
     data = response.json()
     return data
     
def get_image_from_polyline(polyline, summary_polyline, lat, long, distance):
     polyline = reformat_polyline(polyline)
     if distance < 5:
          zoom = 15
          url = "https://maps.googleapis.com/maps/api/staticmap?size=800x400&center=" + str(lat) +"," + str(long) + "&zoom=" + str(zoom) + "&path=weight:4%7Ccolor:0xff006e%7Cenc:" + polyline + "&key=" + cred.google_maps_key
     elif distance < 15:
          zoom = 13
          url = "https://maps.googleapis.com/maps/api/staticmap?size=800x400&center=" + str(lat) +"," + str(long) + "&zoom=" + str(zoom) + "&path=weight:4%7Ccolor:0xff006e%7Cenc:" + summary_polyline + "&key=" + cred.google_maps_key
     else:
          zoom = 11
          url = "https://maps.googleapis.com/maps/api/staticmap?size=800x400&center=" + str(lat) +"," + str(long) + "&zoom=" + str(zoom) + "&path=weight:4%7Ccolor:0xff006e%7Cenc:" + summary_polyline + "&key=" + cred.google_maps_key
     payload={}
     headers = {}
     response = requests.request("GET", url, headers=headers, data=payload)
     return response.content

def reformat_polyline(polyline):
     return polyline.replace('\\\\', '\\')

def get_stats(activities):
     weekly = get_stats_weekly(activities)
     biweekly = get_stats_biweekly(activities)
     monthly = get_stats_monthly(activities)
     bimonthly = get_stats_bimonthly(activities)
     return [weekly, biweekly, monthly, bimonthly]

def get_todays_activities(activities):
     today = datetime.date.today()
     yesterday = today - timedelta(days=1)
     day_list = []
     for k in activities:
          year = int(k["start_date"][0:4])
          month = int(k["start_date"][5:7])
          day = int(k["start_date"][8:10])
          current_date = datetime.date(year, month, day)
          if current_date > today:
               pass
          elif current_date <= yesterday:
               break
          else:
               day_list.append(k)
     return day_list

def get_stats_weekly(activities):
     today = datetime.date.today()
     one_week_back = today - timedelta(days=7)
     week_list = []
     for k in activities:
          year = int(k["start_date"][0:4])
          month = int(k["start_date"][5:7])
          day = int(k["start_date"][8:10])
          current_date = datetime.date(year, month, day)
          if current_date > today:
               pass
          elif current_date < one_week_back:
               break
          else:
               week_list.append(str(year) + str(month) + str(day))
     week_list_set = set(week_list)
     return len(week_list_set)

def get_stats_biweekly(activities):
     today = datetime.date.today()
     two_week_back = today - timedelta(days=14)
     week_list = []
     for k in activities:
          year = int(k["start_date"][0:4])
          month = int(k["start_date"][5:7])
          day = int(k["start_date"][8:10])
          current_date = datetime.date(year, month, day)
          if current_date > today:
               pass
          elif current_date < two_week_back:
               break
          else:
               week_list.append(str(year) + str(month) + str(day))
     week_list_set = set(week_list)
     return len(week_list_set)

def get_stats_monthly(activities):
     today = datetime.date.today()
     one_month_back = today - timedelta(days=30)
     week_list = []
     for k in activities:
          year = int(k["start_date"][0:4])
          month = int(k["start_date"][5:7])
          day = int(k["start_date"][8:10])
          current_date = datetime.date(year, month, day)
          if current_date > today:
               pass
          elif current_date < one_month_back:
               break
          else:
               week_list.append(str(year) + str(month) + str(day))
     week_list_set = set(week_list)
     return len(week_list_set)
     
def get_stats_bimonthly(activities):
     today = datetime.date.today()
     two_month_back = today - timedelta(days=60)
     week_list = []
     for k in activities:
          year = int(k["start_date"][0:4])
          month = int(k["start_date"][5:7])
          day = int(k["start_date"][8:10])
          current_date = datetime.date(year, month, day)
          if current_date > today:
               pass
          elif current_date < two_month_back:
               break
          else:
               week_list.append(str(year) + str(month) + str(day))
     week_list_set = set(week_list)
     return len(week_list_set)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///users.sqlite3"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "hello"

executors = {
    'default': ThreadPoolExecutor(16),
    'processpool': ProcessPoolExecutor(4)
}
sched = BackgroundScheduler(timezone='America/New_York', executors=executors)

db = SQLAlchemy(app)

class user(db.Model):
    uuid = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    pfp_medium = db.Column(db.String(400))
    pfp_large = db.Column(db.String(400))
    refresh_token = db.Column(db.String(100))
    chat_id = db.Column(db.String(200))
    telegram_connected = db.Column(db.Boolean, default=False)

    def __init__(self, uuid, first_name, last_name, pfp_medium, pfp_large):
         self.uuid = uuid
         self.first_name = first_name
         self.last_name = last_name
         self.pfp_medium = pfp_medium
         self.pfp_large = pfp_large
         self.chat_id = ""

def job():
     jk = user.query.all()
     bot = telegram.Bot(token=cred.telegram_bot_token)
     for person in jk:
          if person.telegram_connected:
               access_token = get_new_tokens(person.refresh_token)
               activities = get_activities(access_token, 1)
               today_workouts = get_todays_activities(activities)
               date = datetime.date.today().strftime("%m/%d/%Y")
               if len(today_workouts) > 0:
                    bot_message = "<u>" + date +"</u>" + "\n" + person.first_name + " " + person.last_name + " completed the following activity/activities today:\n\n"
                    for workout in today_workouts:
                         bot_message += workout["name"] +"\n" + "Activity Type: " + workout["type"] + "\n"  + "Time: " 
                         if workout["moving_time"] >= 3600:
                              bot_message += "%d:%02d:%02d" % (workout["moving_time"]//3600, (workout["moving_time"]%3600)//60, (workout["moving_time"]%3600)%60)
                         elif workout["moving_time"] >= 600:
                                   bot_message += "%02d:%02d" % ((workout["moving_time"]%3600)//60, (workout["moving_time"]%3600)%60)
                         else:
                              bot_message += "%d:%02d" % ((workout["moving_time"]%3600)//60, (workout["moving_time"]%3600)%60)

                         bot_message += "\nDistance: " + str(round(workout["distance"]*0.000621371192, 2)) + " mi"
                         if "calories" in workout:
                              bot_message += "\nCalories: " + str(round(workout["calories"])) + "\n\n"
                         else:
                              bot_message += "\n\n"
                    bot.send_message(person.chat_id, bot_message, parse_mode="HTML")
               else:
                    bot.send_message(person.chat_id, "<u>" + date +"</u>\n"+ "No Activity - <b>" + person.first_name + " " + person.last_name + " did not exercise today.</b>", parse_mode="HTML")

sched.add_job(job, 'cron', hour=11, minute=28)

@app.route('/')
def home():
     authorization_code = request.args.get('code', None)
     if authorization_code == None:
          if "user_uuid" in session:
               return redirect(url_for("dashboard"))
          else:
               return render_template('index.html')
     else:
          user_info = get_user_info(authorization_code)
          uuid = user_info[0]
          found_user = user.query.filter_by(uuid=uuid).first()
          if found_user:
               found_user = update_user_info(found_user, user_info)
               db.session.commit()
               session["user_uuid"] = uuid
               session["user_fullname"] = found_user.first_name + " " + found_user.last_name
               session["user_first_name"] = found_user.first_name
               session["profile_medium"] = found_user.pfp_medium
               return redirect(url_for("dashboard"))
          else:
               new_user = user(uuid, user_info[1], user_info[2], user_info[3], user_info[4])
               new_user.refresh_token = user_info[5]
               db.session.add(new_user)
               db.session.commit()
               session["user_uuid"] = uuid
               session["user_fullname"] = new_user.first_name + " " + new_user.last_name
               session["user_first_name"] = new_user.first_name
               session["profile_medium"] = new_user.pfp_medium
               return redirect(url_for("setup"))

@app.route('/setup')
def setup():
     if "user_uuid" in session:
          found_user = user.query.filter_by(uuid=session["user_uuid"]).first()
          if found_user.telegram_connected == 1:
               return redirect(url_for("dashboard"))
          return render_template('setup.html', name=session["user_fullname"], profile_medium=session["profile_medium"])
     else:
          return redirect(url_for("home"))

@app.route('/setup/telegram', methods = ['GET', 'POST'])
def telegram_setup():
     if "user_uuid" in session and user.query.filter_by(uuid=session["user_uuid"]).first().telegram_connected == True:
          return redirect(url_for("dashboard"))
     elif "user_uuid" not in session:
          return redirect(url_for("home"))
     else:
          if request.method == 'POST':
               full_url = request.form['url']
               chat_id = "-" + full_url[full_url.rindex("=")+2:]
               bot = telegram.Bot(token=cred.telegram_bot_token)
               try:
                    bot.send_message(chat_id, "Hello! Thank you for adding me to your group—you can expect daily updates with no further action needed.")
                    found_user = user.query.filter_by(uuid=session["user_uuid"]).first()
                    found_user.chat_id = chat_id
                    found_user.telegram_connected = True
                    db.session.commit()
                    return redirect(url_for("dashboard"))
               except telegram.error.BadRequest:
                    return render_template('telegram_setup.html', name=session["user_fullname"], first_name=session["user_first_name"], profile_medium=session["profile_medium"], message="The chat was not found. Ensure that the entered URL is correct and that you've added the FitCountBot to the group.")
          else:
               return render_template('telegram_setup.html', name=session["user_fullname"], first_name=session["user_first_name"], profile_medium=session["profile_medium"], message="")
     
@app.route('/dashboard')
def dashboard():
     if "user_uuid" in session:
          if user.query.filter_by(uuid=session["user_uuid"]).first().telegram_connected == 0:
               return redirect(url_for("setup"))
          else:
               access_token = get_new_tokens(user.query.filter_by(uuid=session["user_uuid"]).first().refresh_token)
               activities = get_activities(access_token, 1)
               total_distance = 0
               for k in activities:
                    total_distance += k["distance"]
               stats = get_stats(activities)
               return render_template('dashboard.html', stats=stats, activities=activities, name=session["user_fullname"], profile_medium=session["profile_medium"], total_distance=total_distance)
     else:
          return redirect(url_for("home"))

@app.route('/activities/all')
def all_activities():
     if "user_uuid" in session:
          if user.query.filter_by(uuid=session["user_uuid"]).first().telegram_connected == 0:
               return redirect(url_for("setup"))
          else:
               access_token = get_new_tokens(user.query.filter_by(uuid=session["user_uuid"]).first().refresh_token)
               activities = get_activities(access_token, 1)
               return render_template('all_activities.html', activities=activities, name=session["user_fullname"], profile_medium=session["profile_medium"])
     else:
          return redirect(url_for("home"))

@app.route('/activities/<id>')
def activity_by_id(id):
     if not id.isdigit():
          return redirect(url_for("all_activities"))
     else:
          if "user_uuid" in session:
               if user.query.filter_by(uuid=session["user_uuid"]).first().telegram_connected == 0:
                    return redirect(url_for("setup"))
               else:
                    url = 'https://www.strava.com/api/v3/activities/' + str(id)
                    access_token = get_new_tokens(user.query.filter_by(uuid=session["user_uuid"]).first().refresh_token)
                    header = {'Authorization': 'Bearer ' + access_token}
                    h = requests.get(url, headers=header)
                    g = h.json()
                    if h.ok:
                         if g["map"]["polyline"] != "" and "summary_polyline" in g["map"]:
                              image = get_image_from_polyline(g["map"]["polyline"], g["map"]["summary_polyline"], g["start_latitude"],["start_longitutde"], g["distance"]*0.000621371192)
                              image_url = "maps/"+str(g["id"])+'.jpg'
                              with open("static/maps/"+str(g["id"])+'.jpg', 'wb') as handler:
                                   handler.write(image)
                         else:
                              image_url = "maps/no_gps.jpg"
                         return render_template('activity_by_id.html', calories=round(g["calories"]), date=g["start_date"], activity=g, id=id, image=image_url,name=session["user_fullname"], profile_medium=session["profile_medium"])
                    else:
                         return redirect(url_for("all_activities"))
          else:
               return redirect(url_for("home"))

@app.route('/logout')
def logout():
     if "user_uuid" in session:
          session.clear()
          return redirect(url_for("home"))
     else:
          return redirect(url_for("home"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def page_not_working(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    db.create_all()
    sched.start()
    app.run(debug=True, use_reloader=False)