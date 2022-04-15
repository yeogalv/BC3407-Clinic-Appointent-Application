# -*- coding: utf-8 -*-
"""
Created on Sat Apr 9 22:15:24 2022

@author: Alpha
"""

import pandas as pd

def apiLink(list_of_patients):
    reminder = pd.DataFrame(list_of_patients)
    for i in reminder.index:
        name = reminder['patient_id'][i]
        adate = reminder['A_Dates'][i]
        time = reminder['ApptTime'][i]
        #receipient = reminder['phoneNumber'][i]
        message = f"""Dear Mr/Ms {name}, You have a consultation at SinkHelth on {adate} at {time}. 
                  To view or reschedule your appointments, logon to our website at sinkhelth.com."""
        data = ['sms.send', 'SMS', name, message]
        print(data)
        
def confirmationList():
    df = pd.read_csv("FutureAppts.csv", parse_dates = ['A_Dates'])
    df.A_Dates = df.A_Dates.dt.date
    datenow = pd.to_datetime("2015-05-25").date()
    to_date = (datenow + pd.DateOffset(days=4)).date()
    to_notify = df[df.A_Dates == to_date]
    apiLink(to_notify)
    
    
if __name__ == '__main__':
    confirmationList()

