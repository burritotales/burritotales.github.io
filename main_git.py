'''
Aim of this process: My dog requires hydrotherapy every few weeks, and as part of tracking his fitness, I will submit a tabulation of his daily walk durations to his hydrotherapist.
I have created a Python script that integrates Strava and Google Sheets to automate this.

Program will read the google sheets, find the last instance of "Hydro" and check the date
Then go to strava api, return the activities that were started >= the date from (1)
Have a dataframe that Nrows (number of dates) Ncols (5), populate all with 0s
Loop through each strava activity. If 0000-1100 - morning. 1101-1600 - afternoon, 1601-2100 - evening, 2101-2359 - night
Strava API returns the elapsed time in seconds, change it to minutes. if >60, change to h and m
Insert the dataframe into the google sheets starting from the last "Hydro" row
'''

# Retrieve activities
import pandas as pd
import requests
import json
from datetime import datetime
import numpy as np
import math
import time

import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SAMPLE_SPREADSHEET_ID = "" #remove for privacy
SAMPLE_RANGE_NAME = "Sheet1!A2:G"

creds = None
if os.path.exists("token.json"):
	creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		flow = InstalledAppFlow.from_client_secrets_file(
          	"credentials.json", SCOPES
      	)
		creds = flow.run_local_server(port=0)
    		# Save the credentials for the next run
		with open("token.json", "w") as token:
			token.write(creds.to_json())
try:
    service = build("sheets", "v4", credentials=creds)
    # Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
        .execute()
    )
    values = result.get("values", [])
    
    if not values:
        print("No data found")
    
    # print(values)
    
    bool_break = False
    for row in reversed(values):
        if bool_break == False:
            for element in row:
                if "hydro" in element.lower():
                    last_hydro_date = row[0]
                    print(last_hydro_date)
                    bool_break = True
        else:
            break
except HttpError as err:
    print(err)

## Get the tokens from file to connect to Strava
with open('strava_tokens.json') as json_file:
    strava_tokens = json.load(json_file)
## If access_token has expired then use the refresh_token to get the new access_token
if strava_tokens['expires_at'] < time.time():
#Make Strava auth API call with current refresh token
    response = requests.post(
                        url = 'https://www.strava.com/oauth/token',
                        data = {
                                'client_id': '', #removed for privacy
                                'client_secret': '', #removed for privacy
                                'grant_type': 'refresh_token',
                                'refresh_token': strava_tokens['refresh_token']
                                }
                    )
#Save response as json in new variable
    new_strava_tokens = response.json()
# Save new tokens to file
    with open('strava_tokens.json', 'w') as outfile:
        json.dump(new_strava_tokens, outfile)
#Use new Strava tokens from now
    strava_tokens = new_strava_tokens
    
# Loop through all activities
page = 1
url = "https://www.strava.com/api/v3/activities"
access_token = strava_tokens['access_token']
# Create the dataframe ready for the API call to store your activity data
activities = pd.DataFrame(
    columns = [
            "start_date_local",
            "distance",
            "elapsed_time",
    ]
)
while True:
    # get page of activities from Strava
    r = requests.get(url + '?access_token=' + access_token + '&per_page=200' + '&page=' + str(page))
    r = r.json()
    
    # if no results then exit loop
    if (not r):
        break
    
    # otherwise add new data to dataframe
    for x in range(len(r)):
        #need to read the google sheets and return the date of the last hydro
        if datetime.strptime(r[x]['start_date_local'], '%Y-%m-%dT%H:%M:%SZ').toordinal() >= datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal():
            activities.loc[x + (page-1)*200,'start_date_local'] = r[x]['start_date_local']
            activities.loc[x + (page-1)*200,'distance'] = r[x]['distance']
            activities.loc[x + (page-1)*200,'elapsed_time'] = r[x]['elapsed_time']
        else:
            break
    # increment page
    page += 1
activities.to_csv('strava_activities.csv')

##read in the activity csv
df = pd.read_csv('strava_activities.csv')
df = df.reset_index()  # make sure indexes pair with number of rows

#get the number of rows for formatted df
number_of_rows = datetime.strptime(df['start_date_local'].iloc[0], '%Y-%m-%dT%H:%M:%SZ').toordinal() - datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal()+1
#cols of df are start_date_local	distance	elapsed_time
feature_list = ["date", "morning", "afternoon", "evening", "night", "total"]
formatted_df = pd.DataFrame(0, index=np.arange(number_of_rows), columns=feature_list) 

for index, row in df.iterrows():
    #extract the time from between T and Z
    row['start_date_local']=row['start_date_local'].replace("T","*")
    row['start_date_local']=row['start_date_local'].replace("Z","*")
    re=row['start_date_local'].split("*")
    timestart=re[1]
    datestart = re[0]
    
    #extract the hour, minute
    hr_min = timestart.split(":")
    hr = int(hr_min[0]) * 3600 #convert to seconds
    sec = int(hr_min[1]) * 60
    time_start_in_seconds = hr + sec
    
    #fill in the date
    formatted_df.loc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal(),'date'] = datetime.strptime(datestart, '%Y-%m-%d').strftime("%d/%m/%Y")

    #If 0000-1100 - morning. 1101-1630 - afternoon, 1631-2100 - evening, 2101-2359 - night
    if time_start_in_seconds > 21*3600:
        formatted_df.loc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal(),'night'] = formatted_df['night'].iloc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal()] + math.floor(int(row['elapsed_time'])/60)
    elif time_start_in_seconds > 16*3600:
        formatted_df.loc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal(),'evening'] = formatted_df['evening'].iloc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal()] + math.floor(int(row['elapsed_time'])/60)
    elif time_start_in_seconds > 11*3600:
        formatted_df.loc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal(),'afternoon'] = formatted_df['afternoon'].iloc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal()] + math.floor(int(row['elapsed_time'])/60)
    else: 
        formatted_df.loc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal(),'morning'] = formatted_df['morning'].iloc[datetime.strptime(datestart, '%Y-%m-%d').toordinal()- datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal()] + math.floor(int(row['elapsed_time'])/60)

#loop through the formatted_df 

row_num = 0
for index, row in formatted_df.iterrows():
    total_time_for_day = int(row['morning']) + int(row['afternoon']) + int(row['evening']) + int(row['night'])
    
    if total_time_for_day >= 60:
        formatted_df.loc[row_num,'total'] = str(math.floor(total_time_for_day/60)) + "h " + str(total_time_for_day - math.floor(total_time_for_day/60)*60) + "m"
    else:
        formatted_df.loc[row_num,'total'] = str(total_time_for_day) + "m"
    
    list_of_cols = ['morning', 'afternoon', 'evening', 'night']
    for col in list_of_cols:
        if int(row[col]) >= 60:
            formatted_df.loc[row_num,col] = str(math.floor(int(row[col])/60)) + "h " + str(int(row[col]) - math.floor(int(row[col])/60)*60) + "m"
        elif int(row[col]) == 0:
            formatted_df.loc[row_num,col] = 0
        else:
            formatted_df.loc[row_num,col] = str(row[col]) + "m"
    
    row_num = row_num+1
formatted_df.to_csv('format_strava_activities.csv', index=False)

# Read the CSV file, find which gsheet row to start writing, send API
df = pd.read_csv('format_strava_activities.csv')
df = df.drop('date', axis=1)

values = [df.columns.values.tolist()]
values = df.values.tolist()
service = build("sheets", "v4", credentials=creds)
body = {"values": values}
result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=SAMPLE_SPREADSHEET_ID,
            range="Sheet1!C" + str(datetime.strptime(last_hydro_date, '%d/%m/%Y').toordinal() - datetime.strptime("27/10/2023", '%d/%m/%Y').toordinal() +3),
            valueInputOption='RAW',
            body=body,
        )
        .execute()
    )
