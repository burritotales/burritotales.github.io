"""
Purpose of program: To retrieve a user defined month from a Google Calendar, and then format the relevant activities into a message that will be sent via Telegram.
If the user does not specify the need of a Google Calendar, the bot will return a message with the month's date and days.
In both use cases, the message will be separated by weee, ie. there will be a hyphenated separator between each week

Ideas for bot: 1 function will be to return the month's calendar given a user defined month/year
Another function will return the google calendar in a specified format given the month/year

Formatting requirements:
Month year in bold
list of dates of that month with their corresponding days in bold
list of events retrieved from google calendar with the start-end time in normal font
separate out the weeks of the month with -------------
"""

#telegram dependencies
from typing import Final #a final type means that the variable cannot be reassigned to another value
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import numpy as np
import pandas as pd

#google dependencies
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#string dependencies 
import string
import re
 
TOKEN: Final = '' #token and username hidden for privacy
BOT_USERNAME: Final = ''

#commands. these are the ones that start with /
#async is used in the api to make the commands asynchronous 
async def start_command(update: Update, context:ContextTypes.DEFAULT_TYPE):
    #for codes, insert the logic here, then reply will be at the end
    await update.message.reply_text("Hello! I will help to generate your monthly calendar, please submit your desired month in format month year, Eg. Sep 2024. If you're calling me from a group chat, please start the text with \"calendarize\". If you use \"calendarize refresh gc\" with the month year, pai's google calendar events will be displayed. Eg. calendarize refresh gc sep 2024") #this will be the text that the bot will say when the user clicks on start

async def blank_calendar_command(update: Update, context:ContextTypes.DEFAULT_TYPE):
    new_text = datetime.today().strftime("%b %Y")
    await update.message.reply_text(handle_response(new_text),parse_mode='MarkdownV2')
    
async def google_calendar_command(update: Update, context:ContextTypes.DEFAULT_TYPE):
    new_text = datetime.today().strftime("%b %Y")
    await update.message.reply_text(handle_response("refresh gc " + new_text),parse_mode='MarkdownV2')
    
#handle the responses -> bot can process what the user is typing
def handle_response(text: str) -> str: #will take an input of type string, and return string
    processed: str = text.lower() #py is a case sensitive language
    if "refresh gc" in processed:
        processed = processed.lower().replace("refresh gc", '').strip()
        # print(processed)
        bool_calendar = True
    else:
        bool_calendar = False
    
    format = "%b %Y" #expected month year eg. nov 2024
    # checking if format matches the date 
    res = True
    try:
        res = bool(datetime.strptime(processed, format))
    except ValueError:
        res = False
    # print(res)
    # print(bool_calendar)
    if res == True:
        # if the format is correct, we want to take the month, change it to integer and take the date
        if bool_calendar == False:
            month_text: str = processed.split(" ")[0]
            year: int = processed.split(" ")[1]
            # get current month, get next month
            first_month = int(pd.to_datetime(month_text,format='%b').strftime('%m'))
            if first_month == 12:
                next_month = 1
                next_year = int(year)+1
            else:
                next_month = first_month+1
                next_year = year
        
            second_date = pd.to_datetime(str(next_month)+' '+str(next_year),format='%m %Y').strftime('%Y-%m')
            first_date = pd.to_datetime(processed,format='%b %Y').strftime('%Y-%m')
            # return second_date
            date_range = np.arange(first_date, second_date,dtype='datetime64[D]')
            # if day is sun, join the date with the line separator. encase the start and end of the string with * to make it bold
            return "*" + str(month_text).upper() + ' '+ str(year) + "\n \n" + "\n \n".join(str(pd.to_datetime(x,format='%Y-%m-%d').strftime('%d/%m')) + ' ' + (datetime.strptime(str(x), "%Y-%m-%d").date().strftime("%a") +"\n \n" + "\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-" if datetime.strptime(str(x), "%Y-%m-%d").date().strftime("%a") == "Sun" else datetime.strptime(str(x), "%Y-%m-%d").date().strftime("%a")) for x in date_range) + "*"
        else:
            month_text: str = processed.split(" ")[0]
            year: int = processed.split(" ")[1]
            #get current month, get next month
            first_month = int(pd.to_datetime(month_text,format='%b').strftime('%m'))
            if first_month == 12:
                next_month = 1
                next_year = int(year)+1
            else:
                next_month = first_month+1
                next_year = year
            # print (processed)
            # print(str(next_month)+' '+str(next_year))
                
            first_date = pd.to_datetime(processed,format='%b %Y').strftime('%Y-%m')
            #'%Y-%m-01T00:00:01+08:00'
            second_date = pd.to_datetime(str(next_month)+' '+str(next_year),format='%m %Y').strftime('%Y-%m')
            date_range = np.arange(first_date, second_date,dtype='datetime64[D]')

            SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
            """Shows basic usage of the Google Calendar API.
            Prints the start and name of the next 10 events on the user's calendar.
            """
            creds = None
            # The file token.json stores the user's access and refresh tokens, and is
            # created automatically when the authorization flow completes for the first
            # time.
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
                service = build("calendar", "v3", credentials=creds)

                events_result = (
                    service.events()
                    .list(
                        calendarId="primary",
                        timeMin=first_date+"-01T00:00:00+08:00", # user defined date only has the month year, append 1st of the month to it
                        timeMax = second_date+"-01T00:00:00+08:00",
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
                events = events_result.get("items", [])

                if not events: 
                    return "No upcoming events found\." #escape the . because message is being sent using markdown

                final_output = []
                # loop through the list of dates in the month, then loop through the calendar events. if the events match the date, push the event into the output
                # count the number of events for the day and remove these from the list of events so that the traversing time will not be as long
                
                for generated_date in date_range:
                    # print(generated_date)
                    final_output.append(generated_date)
                    # print(final_output)
                    count_events = 0
                    # if len(events) > 0:
                    for event in events:
                        try:
                            event_date = event["start"].get("dateTime", event["start"].get("date")).split("T")[0]
                            start_time = event["start"].get("dateTime", event["start"].get("date")).split("T")[1].split("+")[0].split(":")[0] + event["start"].get("dateTime", event["start"].get("date")).split("T")[1].split("+")[0].split(":")[1]
                            end_time = event["end"].get("dateTime", event["end"].get("date")).split("T")[1].split("+")[0].split(":")[0] + event["end"].get("dateTime", event["end"].get("date")).split("T")[1].split("+")[0].split(":")[1]
                        except: #event will not have datetime if this is a full day event, try except to handle this
                            event_date = event["start"].get("date", event["start"].get("date"))
                            start_time = ""
                            end_time = ""
                        # print(event["summary"], event_date, start_time, end_time)
                        # print(event_date)
                        
                        if str(event_date) == str(generated_date):
                            # print("trues")
                            count_events=count_events+1
                            chars = re.escape(string.punctuation)
                            # print re.sub('['+chars+']', '',event["summary"])
                            
                            # some events that I do not want to pass into the calendar
                            if event["summary"].lower() == "office" or "travel" in event["summary"].lower() or "vacuum" in event["summary"].lower() or "wash" in event["summary"].lower() or "walk" in event["summary"].lower() or "dinner" in event["summary"].lower() or "weights" in event["summary"].lower() or "smitty" in event["summary"].lower() or "shower" in event["summary"].lower() or "run" in event["summary"].lower():
                                pass
                            else:
                                final_output.append(re.sub('['+chars+']', ' ',event["summary"]) + " " + start_time + "\-" + end_time)
                            # print(event["summary"])
                            # print(final_output)
                            # print(len(final_output))
                        else:
                            # print("false")
                            # print(count_events)
                            if count_events > 0:
                                del events[:count_events]
                                # print(len(events))
                                break
                    # print(final_output)
                # loop through the list, if it cannot be parsed as a date, append it as it is. Else, if the day is monday, add the line separator above it + date + day in bold
                # else, add the date+day in bold
                return  "*" + str(month_text).upper() + ' '+ str(year) + "*" + "\n" + "\n".join((x if bool(re.search("^([1-9]|0[1-9]|1[0-9]|2[0-9]|3[0-1])(\.|-|/)([1-9]|0[1-9]|1[0-2])(\.|-|/)([0-9][0-9]|19[0-9][0-9]|20[0-9][0-9])$|^([0-9][0-9]|19[0-9][0-9]|20[0-9][0-9])(\.|-|/)([1-9]|0[1-9]|1[0-2])(\.|-|/)([1-9]|0[1-9]|1[0-9]|2[0-9]|3[0-1])$",str(x))) == False else  "\n" + "*" + "\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-" + "\n \n" + str(pd.to_datetime(x,format='%Y-%m-%d').strftime('%d/%m')) + " " + datetime.strptime(str(x), "%Y-%m-%d").date().strftime("%a") + "*" if datetime.strptime(str(x), "%Y-%m-%d").date().strftime("%a") == "Mon" else "*" + "\n" + str(pd.to_datetime(x,format='%Y-%m-%d').strftime('%d/%m')) + " " + datetime.strptime(str(x), "%Y-%m-%d").date().strftime("%a") + "*") for x in final_output)
            except HttpError as error:
                print(f"An error occurred: {error}")
    else:
        return "Date is not in the correct format, please submit the date again in month (short form) year. Eg. sep 2024"
    
#this portion will allow the bot to send back the messsage into the chat
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type #inform us whether it's a private chat or a group chat. we don't want the bot to respond unless the user is directly talking to it
    text:str = update.message.text #the message that is incoming

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if message_type == 'group':
        if "calendarize" in text.lower():
            new_text: str = text.lower().replace("calendarize", '').strip() #we don't want to process the bot name in the text. strip is to trim the edge whitespaces
            response: str = handle_response(new_text)
        else:
            return #bot shouldn't respond
    else:
        response: str = handle_response(text)
    
    print ('Bot:', response)
    
    if "Date is not in the correct format" in response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text(response, parse_mode='MarkdownV2')

#error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused the following error {context.error}')

#putting it all together
if __name__ == "__main__":
    print('Starting bot')
    app = Application.builder().token(TOKEN).build()

    #commands
    app.add_handler(CommandHandler('start', start_command)) #put in your commands
    app.add_handler(CommandHandler('blankcalendar', blank_calendar_command))
    app.add_handler(CommandHandler('googlecalendar', google_calendar_command))

    #messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    #errors
    app.add_error_handler(error)

    #polling - for bot to continually check for messages
    print('polling')
    app.run_polling(poll_interval=3) #unit is in seconds

