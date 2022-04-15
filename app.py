import pandas as pd
import numpy as np
from flask import Flask, render_template, g, request, redirect, url_for, session
from flask_session import Session
from datetime import date, datetime
import csv
import matplotlib.pyplot as plt
import seaborn as sns

# Use patientid 65672 for best demo.

# Create a User Class that contains patient ID and Password to match.
class User:
    def __init__(self, user_id, user_password):
        self.user_id = user_id
        self.user_password = user_password


# Input all user credentials with User Class into a list for verification at log in
patient_info = []
doctor_info = []
with open("appointmentData_Cleaned.csv", 'r') as fp:
    csv_r = csv.reader(fp)
    for row in csv_r:
        patient_info.append(User(user_id=row[-7], user_password=row[-6]))
        doctor_info.append(User(user_id=row[-4], user_password=row[-3]))


app = Flask(__name__)
app.secret_key = 'hello'
app.config["SESSION_PERMANENT"] = True
Session(app)

# Create a function that runs before every request to store the user-id provided by the user during the log in
# session as object g.user
@app.before_request
def before_request():
    g.user = None
    if 'patient_id' in session:
        user = [x for x in patient_info if x.user_id == session['patient_id']][0]
        g.user = user
    elif 'doctor_id' in session:
        user = [x for x in doctor_info if x.user_id == session['doctor_id']][0]
        g.user = user


@app.route('/')
def home():
    return render_template('homepage.html')


#%%-------------------------------------------------------Patient Interface--------------------------------------------------------

# Patient Login Page
@app.route('/patientlogin', methods=['GET', 'POST'])
def patientlogin():
    try:
        error = None
        if request.method == "POST":
            pat_id = request.form['patient_id']
            pat_password = request.form['patient_password']

            user = [x for x in patient_info if x.user_id == pat_id][0]

            # Verify If Patient Password is correct for the ID then set patient id for the session,
            # else return an error message to be shown
            if pat_id != user.user_id or pat_password != user.user_password:
                error = 'Invalid patient ID or password. Please try again'
            else:
                session['patient_id'] = user.user_id
                return redirect('/patient')
    except IndexError:
        error='Invalid credentials. Please try again'
    return render_template('patientlogin.html', error=error)



# Patient's Homepage
@app.route('/patient', methods = ["GET","POST"])
def patient():
    try:
        df = pd.read_csv("FutureAppts.csv", parse_dates=['R_Dates', 'A_Dates'])
        # Don't show cancelled to not confuse patient but it remains in data
        upcoming = df.loc[(df.patient_id == int(g.user.user_id)) & (df.confirm != "Cancelled"), ['ApptNo','R_Dates', 'RegTimes','Day', 'A_Dates',
                                                                                      'ApptTime', 'doctor_id', 'confirm']]
        todaydate = df.A_Dates.min() - pd.to_timedelta(1, unit='d')  # hypothetical date
        daystonextappt = upcoming.A_Dates.min() - todaydate  # Number of Days to next appointment
        indexdata = upcoming.loc[df.confirm != "Confirmed","ApptNo"]
        # All appointment no belonging to patient.

        # Rename Columns for Easier Understanding to Patient
        loaddata = upcoming.rename(columns={'ApptNo':'Appointment No.','R_Dates': 'Registered Date', 'RegTimes': 'Registration Time',
                                            'A_Dates': 'Appointment Dates', 'confirm': 'Status',
                                            'ApptTime': 'Appointment Time',"doctor_id": "Doctor ID"})

        # Only Allow Actions for Appointment in 3-5 days
        if "Awaiting Action" in list(upcoming.confirm):
            nextapptindex = list(upcoming[df.confirm == "Awaiting Action"].ApptNo.head(1))
            daysmax = df[df.ApptNo == nextapptindex[0]].A_Dates.min() - todaydate
            if daysmax.days <= 5:
                nexttype = "action"
            else:
                nexttype = "noaction"
        else:
            # This is in case no upcoming actions
            nextapptindex = list(upcoming.ApptNo.head(1))
            nexttype = "noaction"
        # To get the Appointment Number that Patient wants to cancel if no action required.
        if request.method == "POST":
            indexsel = int(request.form.get("ind"))
            df.loc[df.ApptNo == indexsel, "confirm"] = "Cancelled"
            df.sort_values(by="A_Dates").to_csv("FutureAppts.csv", encoding='utf-8', index=False)
            return redirect('/cancel')
        return render_template('patientmainpage.html', dayleft=daystonextappt.days, data=loaddata.to_html(index=False),
                               nextappt=nextapptindex[0], tdate=todaydate.date(), id=g.user.user_id, ntype=nexttype,
                               indata=indexdata)
    except IndexError:  # In case patient has no upcoming appointments,
        # they will be redirected to make a new appointment.
        return redirect('/error')


@app.route('/action', methods = ["GET", "POST"])
def action():
    df = pd.read_csv("FutureAppts.csv", parse_dates=['A_Dates','R_Dates'])
    upcoming = df.loc[
        (df.patient_id == int(g.user.user_id)) & (df.confirm != "Cancelled"), ['ApptNo','R_Dates', 'RegTimes', 'A_Dates',
                                                                                  'ApptTime',
                                                                                  'doctor_id',
                                                                                  'confirm']]
    # Don't show cancelled to not confuse patient but it remains in data
    # nextapptindex = list(upcoming[df.confirm == "Awaiting Action"].head(1).index)
    try:
        nextapptindex = list(upcoming[df.confirm == "Awaiting Action"].ApptNo.head(1))
        if request.method == "POST":
            option = request.form["action"]
            if option == "confirm":
                df.loc[df.ApptNo==nextapptindex[0],"confirm"] = "Confirmed"
                df.sort_values(by="A_Dates").to_csv("FutureAppts.csv", encoding='utf-8', index=False)
                return redirect('/confirm')
            elif option == "cancel":
                df.loc[df.ApptNo==nextapptindex[0], "confirm"] = "Cancelled"
                df.sort_values(by="A_Dates").to_csv("FutureAppts.csv", encoding='utf-8', index=False)
                return redirect('/cancel')
            else:
                df.loc[df.ApptNo==nextapptindex[0], "confirm"] = "Awaiting Action"
                df.sort_values(by="A_Dates").to_csv("FutureAppts.csv", encoding='utf-8', index=False)
                return redirect('/reschedule')
        return render_template('actionpage.html', id=g.user.user_id, nextappt=nextapptindex[0])
    except IndexError:
        return redirect('/patient')



@app.route('/confirm')
def confirm():
    return render_template('confirmationpage.html', id=g.user.user_id)


@app.route('/cancel')
def cancel():
    return render_template('cancellationpage.html', id=g.user.user_id)


@app.route('/reschedule', methods = ["GET","POST"])
def reschedule():  # put application's code here
    df = pd.read_csv("FutureAppts.csv", parse_dates=['A_Dates', 'R_Dates'])
    upcoming = df.loc[
        (df.patient_id == int(g.user.user_id)) & (df.confirm != "Cancelled"), ['ApptNo','R_Dates', 'RegTimes', 'A_Dates',
                                                                                  'ApptTime',
                                                                                  'doctor_id',
                                                                                  'confirm']]
    # Don't show cancelled to not confuse patient but it remains in data
    # todaydate = df.R_Dates.min()- pd.to_timedelta(1, unit='d')  # hypothetical date
    nextapptindex = list(upcoming[df.confirm == "Awaiting Action"].ApptNo.head(1))
    resapptdate = list(df.loc[df.ApptNo==nextapptindex[0], "A_Dates"])
    resappttime = list(df.loc[df.ApptNo==nextapptindex[0], "ApptTime"])
    todaydate = df.A_Dates.min() - pd.to_timedelta(1, unit='d')  # hypothetical date
    reslimit = todaydate + pd.to_timedelta(3, unit='d')  # To get slots only 3 days later.
    # To get Available Slots:
    grouped = pd.DataFrame(df.groupby(['A_Dates','Day','ApptTime']).size().reset_index(name="slots"))
    filtered = grouped[(grouped.slots < 3)&(grouped.A_Dates > reslimit)]
    slotdates = list(filtered.A_Dates)
    slottimes = list(filtered.ApptTime)
    slotday = list(filtered.Day)
    slotno = list(filtered.index)
    data = list(zip(slotdates,slotday, slottimes, slotno))
    if request.method == "POST":
        option = int(request.form["slotno"])
        seldate = filtered.loc[option, "A_Dates"]
        seltime = filtered.loc[option, "ApptTime"]
        # To Get Doctors that Are available for that timeslot
        bookeddoctors = list(df[(df.A_Dates == seldate) & (df.ApptTime == seltime)].doctor_id)
        doctors = [160590, 160591, 160592]
        freedoctors = []
        for each in doctors:
            if each not in bookeddoctors:
                freedoctors.append(each)
        # Update Rescheduled Details
        df.loc[df.ApptNo == nextapptindex[0],"A_Dates"] = seldate
        df.loc[df.ApptNo == nextapptindex[0], "ApptTime"] = seltime
        df.loc[df.ApptNo == nextapptindex[0], "doctor_id"] = freedoctors[0]
        df.loc[df.ApptNo == nextapptindex[0], "doctor_password"] = freedoctors[0]
        df.loc[df.ApptNo == nextapptindex[0], "Day"] = seldate.strftime("%A")
        freedoctors.clear()
        df.sort_values(by="A_Dates").to_csv("FutureAppts.csv", encoding='utf-8', index=False)
        return redirect('/rescheduled')
    return render_template('reschedulepage.html', datas=data, nextappt=nextapptindex[0], resdate=resapptdate[0],
                           restime=resappttime[0], tdate=todaydate.date(), id=g.user.user_id)


@app.route('/rescheduled')
def rescheduled():  # put application's code here
    return render_template('afterrescheduledpage.html', id=g.user.user_id)


@app.route('/error')
def error():  # put application's code here
    return render_template('error.html', id=g.user.user_id)


@app.route('/appointment', methods = ["GET", "POST"])
def appt():  # put application's code here
    df = pd.read_csv("FutureAppts.csv", parse_dates=['A_Dates', 'R_Dates'])
    df2 = pd.read_csv("PastAppts.csv", parse_dates=['A_Dates', 'R_Dates'])
    todaydate = df.A_Dates.min() - pd.to_timedelta(1, unit='d')  # hypothetical date
    reslimit = pd.to_datetime(todaydate + pd.to_timedelta(3, unit='d'))
    grouped = pd.DataFrame(df.groupby(['A_Dates','Day','ApptTime']).size().reset_index(name="slots"))
    filtered = grouped[(grouped.slots < 3)&(grouped.A_Dates > reslimit)]
    slotdates = list(filtered.A_Dates)
    slottimes = list(filtered.ApptTime)
    slotday = list(filtered.Day)
    slotno = list(filtered.index)
    data = list(zip(slotdates,slotday, slottimes, slotno))
    if request.method == "POST":
        newrec = df2[df2.patient_id == int(g.user.user_id)].head(1).drop(['Show_Up', 'Waiting_Time'], axis=1)
        df = pd.concat([df, newrec], axis=0)
        newappt = list(df.tail(1).index)
        option = int(request.form["slotno"])
        seldate = filtered.loc[option, "A_Dates"]
        seltime = filtered.loc[option, "ApptTime"]
        freedoctors = []
        bookeddoctors = list(df[(df.A_Dates == seldate) & (df.ApptTime == seltime)].doctor_id)
        doctors = list(df.doctor_id.unique())
        for each in doctors:
            if each not in bookeddoctors:
                freedoctors.append(each)
        df.loc[newappt, "A_Dates"] = seldate
        df.loc[newappt, "ApptTime"] = seltime
        df.loc[newappt, "R_Dates"] = todaydate
        df.loc[newappt, "RegTimes"] = datetime.now().strftime("%H:%M:%S")
        df.loc[newappt, "doctor_id"] = freedoctors[0]
        df.loc[newappt, "Doctor_password"] = freedoctors[0]
        df.loc[newappt, "Day"] = seldate.strftime("%A")
        df.loc[newappt,"ApptNo"] = df.ApptNo.max()+1
        df.sort_values(by="A_Dates").to_csv("FutureAppts.csv", encoding='utf-8', index=False)
        return redirect('/patient')
    return render_template('newappt.html', datas=data, tdate=todaydate.date(), id=g.user.user_id)


@app.route('/profile')
def profile():  # put application's code here
    df = pd.read_csv("PastAppts.csv", parse_dates=['A_Dates', 'R_Dates'])
    missed = df.loc[(df.patient_id == int(g.user.user_id)) & (df.Show_Up == "No"), ['Day', 'R_Dates', 'A_Dates',
                                                                                       'ApptTime']]
    showed_up = df.loc[(df.patient_id == int(g.user.user_id)) & (df.Show_Up == "Yes"), ['Day', 'R_Dates', 'A_Dates',
                                                                                           'ApptTime']]
    if len(missed) == 0:
        patient_pctg_miss = 0
    else:
        patient_pctg_miss = (len(missed) / (len(missed) + len(showed_up))) * 100
    overall_miss = len(df.loc[df.Show_Up == "No"])
    overall_pctg_miss = overall_miss/len(df)*100
    diff = round(patient_pctg_miss-overall_pctg_miss, 2)
    miss = missed.rename(columns={'R_Dates': 'Registered Date', 'A_Dates': 'Appointment Date',
                                  'ApptTime': 'Appointment Time'})
    miss = miss.rename_axis('Appointment No.', axis=1)
    show_up = showed_up.rename(columns={'R_Dates': 'Registered Date', 'A_Dates': 'Appointment Date',
                                        'ApptTime': 'Appointment Time'})
    show_up = show_up.rename_axis('Appointment No.', axis=1)

    data = pd.DataFrame({"Missed_Appointments": ["Patient %", "Average Hospital %"],
                         "Visits": [patient_pctg_miss, overall_pctg_miss]})
    sns.set(rc={'axes.facecolor': '#ebf2fa', 'figure.facecolor': '#ebf2fa'})
    fig, ax = plt.subplots()
    sns.barplot(x=data.Missed_Appointments, y=data.Visits, ax=ax)
    ax.set(ylabel = "Visits (%)")
    fig.savefig("static/image/plot.jpg")
    return render_template('profile.html', diff=diff, notimes=len(missed),data1=miss.to_html(),
                           data2=show_up.to_html(), id=g.user.user_id)


#%%-------------------------------------------------------Staff Interface--------------------------------------------------------

@app.route('/employeelogin', methods=['GET', 'POST'])
def doctorlogin():
    try:
        error = None
        if request.method == "POST":
            doctor_id = request.form['doctor_id']
            doctor_password = request.form['doctor_password']

            user = [x for x in doctor_info if x.user_id == doctor_id][0]
            # Verify If Patient Password is correct for the ID then set patient id for the session, else return an error message to be shown
            if doctor_id != user.user_id or doctor_password!=user.user_password:
                error='Invalid Doctor ID or password. Please try again'
            else:
                session['doctor_id']=user.user_id
                return redirect('/doctor')
    except IndexError:
        error='Invalid credentials. Please try again'
    return render_template('doctorlogin.html', error=error)

@app.route('/doctor')
def homepage():
    plt.rcdefaults()
    plt.rcParams.update({'axes.facecolor': '#ebf2fa','figure.facecolor': '#ebf2fa'})
    df = pd.read_csv("FutureAppts.csv", parse_dates=['A_Dates'])
    datenow = (df.A_Dates.min()).date()
    staffid = int(g.user.user_id)
    return render_template('doctorhomepage.html', tdate = datenow, id = staffid)

@app.route('/dashboard-home')
def getdashboard():
    df = pd.read_csv("appointmentData_Cleaned.csv")
    cat = [df.Gender, df.Day, df.Diabetes, df.Drinks, df.HyperTension, df.Handicap, df.Smoker,
           df.Scholarship, df.Tuberculosis, df.Sms_Reminder]
    cat1 = ['Gender', 'Day', 'Diabetes', 'Drinks', 'HyperTension', 'Handicap', 'Smoker', 'Scholarship', 'Tuberculosis',
            'Sms_Reminder', 'AgeGroup']
    # plt.rcdefaults()
    # plt.rcParams.update({'axes.facecolor': '#ebf2fa','figure.facecolor': '#ebf2fa'})
    for i in range(len(cat)):
        pd.crosstab(cat[i], df.Show_Up, normalize="index").plot.bar()
        plt.title(f'Show-up across {cat1[i]}', fontdict={'fontweight': 'bold', 'fontsize': 18})
        plt.xlabel(f'{cat1[i]}',fontdict={'fontweight': 'bold'})
        plt.ylabel('Percentage of Show-Up',fontdict={'fontweight': 'bold'})
        plt.savefig(f'static/image/Show-up across {cat1[i]}.png', dpi=300)
    plt.clf()
    wt = pd.crosstab(df.Waiting_Time, df.Show_Up, normalize='index')
    wt[-50:].plot()
    plt.ylabel('Percentage of Show-Up')
    plt.title('Show-up across Waiting Time', fontdict={'fontweight': 'bold', 'fontsize': 18})
    plt.savefig(f'static/image/Show-up across Waiting Time', dpi=300)
    plt.clf()
    median_age_noshow = df[df['Show_Up'] == "No"]['Age'].median()
    median_age_show = df[df['Show_Up'] == "Yes"]['Age'].median()
    age_show = [median_age_noshow, median_age_show]
    x_names = ['No Show', 'Show Up']
    plt.bar(x_names, age_show)
    plt.title('Median age across show up', fontdict={'fontweight': 'bold', 'fontsize': 18})
    plt.ylabel('Median age')
    plt.savefig(f'static/image/Median age across show up.png', dpi=300)
    return render_template("dashboard_home.html")

@app.route('/dashboard-smoker-drinks')
def getsd():
    return render_template("dashboard_smoker_drinks.html")

@app.route('/dashboard-diabetes-handicap')
def getdh():
    return render_template("dashboard_Diabetes_Handicap.html")

@app.route('/dashboard-hyper-tuber')
def getht():
    return render_template("dashboard_Hyper_Tuber.html")

@app.route('/dashboard-gender-scholarship')
def getgs():
    return render_template("dashboard_Gender_Scholarship.html")

@app.route('/dashboard-waitingtime-age')
def getwa():
    return render_template("dashboard_Waitingtime_Age.html")

@app.route('/KPI')
def getKpi():
    df = pd.read_csv('PastAppts.csv', parse_dates=['A_Dates','R_Dates'])
    df['A_month'] = df['A_Dates'].dt.month
    df['A_Year'] = df['A_Dates'].dt.year
    date = '2015/04/01'
    filtered1 = df.loc[(df.A_Year == 2015) & (df.A_month == 4) & (df.A_Dates <= date)] #get KPI for the month
    plt.clf()
    filtered1.Show_Up.value_counts(normalize='index').plot.pie(autopct='%.2f %%')
    plt.title('KPI for the month', fontdict={'fontweight': 'bold', 'fontsize': 18})
    plt.savefig(f'static/image/KPI for the month.png', dpi=300)
    plt.clf()
    filtered2 = df.loc[(df.A_Year==2015)&(df.A_Dates<=date)]
    filtered2.Show_Up.value_counts(normalize='index').plot.pie(autopct='%.2f %%')
    plt.title('KPI for the Year', fontdict={'fontweight':'bold', 'fontsize': 18})
    plt.savefig(f'static/image/KPI for the year.png', dpi=300)
    plt.clf()
    filtered3 = df.loc[df.A_Dates<=date]
    filtered3.Show_Up.value_counts(normalize='index').plot.pie(autopct='%.2f %%')
    plt.title('KPI till date', fontdict={'fontweight':'bold', 'fontsize': 18})
    plt.savefig(f'static/image/KPI till date.png', dpi=300)
    KPI_month = round(filtered1.Show_Up.value_counts(normalize='index')[1]*100,2)
    KPI_year = round(filtered2.Show_Up.value_counts(normalize='index')[1] * 100, 2)
    KPI_tilldate = round(filtered3.Show_Up.value_counts(normalize='index')[1] * 100, 2)
    return render_template("KPI.html", KPI_month = KPI_month, KPI_year = KPI_year, KPI_tilldate = KPI_tilldate)

@app.route('/schedule')
def schedule():
    if int(g.user.user_id) in (160590, 160591, 160592):
        sch = pd.read_csv("FutureAppts.csv", parse_dates=['A_Dates'])
        sch.A_Dates = sch.A_Dates.dt.date
        datenow = sch.A_Dates.min()
        datenow = pd.to_datetime(datenow)
        datenow = datenow.date()
        upcoming = sch.loc[
            (sch.A_Dates == datenow) & (sch.confirm != "Cancelled") & (sch.doctor_id == int(g.user.user_id)), ['patient_id', 'ApptTime',
                                                                                              'confirm']]
        upcoming = upcoming.sort_values(by='ApptTime').reset_index(drop=True)
        upcoming.index += 1
        loaddata = upcoming.rename(
            columns={'patient_id': 'Patient_ID', 'ApptTime': 'Appointment Timing', 'confirm': 'Status'})
        loaddata = loaddata.rename_axis('Patient No.', axis=1)
        loaddata['Attendance_Rate'] = 0.0
        past = pd.read_csv("PastAppts.csv")
        past.Show_Up = np.where(past['Show_Up'] == 'Yes', 1, 0)

        for i in loaddata.Patient_ID:
            locater = past.loc[past.patient_id == i]
            if len(locater) > 0:
                show_up_rate = round(locater.Show_Up.sum() / len(locater), 2)
                loaddata.loc[loaddata.Patient_ID == i, 'Attendance_Rate'] = show_up_rate * 100
            elif len(locater) == 0:
                loaddata.loc[loaddata.Patient_ID == i, 'Attendance_Rate'] = 100.0

        loaddata = loaddata.rename(columns={'Attendance_Rate': 'Attendance Rate'})
        return render_template('docpage.html', data=loaddata.to_html(),DocID = g.user.user_id, tdate = datenow)

@app.route('/search', methods=["GET","POST"])
def search():
    try:
        error = None
        if request.method == "POST":
            patientid = int(request.form['patientid'])
            spast = pd.read_csv("PastAppts.csv", parse_dates=['A_Dates'])
            sfutu = pd.read_csv("FutureAppts.csv", parse_dates=['A_Dates'])
            rec1 = spast[spast.patient_id == patientid]
            rec2 = sfutu[sfutu.patient_id == patientid]
            combined = pd.concat([rec1, rec2]).reset_index(drop=True)
            inter = combined.loc[combined.patient_id == patientid, ['A_Dates', 'ApptTime', 'Show_Up', 'doctor_id']].reset_index(
                drop=True)
            for i in inter.columns:
                if i == 'Show_Up':
                    inter.loc[inter[i].isnull(), 'Show_Up'] = 'NA'
            inter = inter.rename(columns={'A_Dates': 'Appointment Dates', 'ApptTime': 'Appointment Timing', 'Show_Up': 'Show Up?', 'doctor_id':'Doctor ID'})
            inter.index += 1
            attend_rate = 100.0
            rec1.Show_Up = np.where(rec1.Show_Up == 'Yes', 1, 0)
            if len(rec1) > 0:
                attend_rate = int(round(rec1.Show_Up.sum() / len(rec1), 2) * 100)

            last_cond = rec1[-1:]
            last_cond = last_cond.set_index('patient_id')
            last_cond.index.name = None
            disp_cond = last_cond.loc[:,['Age','Gender','Diabetes','Drinks','HyperTension', 'Handicap', 'Smoker', 'Scholarship', 'Tuberculosis']]
            for i in disp_cond.columns:
                if i not in ('Age', 'Gender'):
                    disp_cond[i] = np.where(disp_cond[i] == 0, 'No', 'Yes')

            if len(rec1) > 0:
                return render_template("searchresult.html", data=disp_cond.to_html(), data1=inter.to_html(),showUpRate = attend_rate)
            elif len(rec1) == 0:
                return render_template("noresults.html")
    except ValueError:
        error = 'Please enter only numeric characters'
    return render_template("search.html", error = error)

@app.route('/filter',methods=["GET","POST"])
def no_show_filter():
    try:
        error = None
        if request.method == "POST":
            df = pd.read_csv('PastAppts.csv')
            df = df.loc[df.Show_Up == 'No']
            no_of_noshows = int(request.form['threshold'])
            limit = int(request.form['limit'])
            filtered = df.groupby(by='patient_id').count()['Show_Up'].sort_values(ascending=False)
            filtered.index = filtered.index.rename('Patient ID')
            filtered = filtered[filtered >= no_of_noshows][:limit]
            filtered = pd.DataFrame(filtered).rename(columns={'Show_Up': 'No. of No Shows'})
            return render_template("filterresults.html", data = filtered.to_html(), threshold = no_of_noshows, limit = limit)
        return render_template("noshowfilter.html")
    except ValueError:
        error = 'Please enter only numeric characters'
    return(render_template("noshowfilter.html", error = error))



#%%-------------------------------------------------------Logout--------------------------------------------------------


@app.route('/logout')
def logout():
    if 'patient_id' in session:
        session.pop('patient_id',None)
    elif 'doctor_id' in session:
        session.pop('doctor_id',None)
    return redirect('/')


if __name__ == '__main__':
    app.run()