import time
import pickle
import os.path
import datetime
import post_sm
from dotenv import load_dotenv
from urlextract import URLExtract
from urllib.parse import urlparse
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


def main():
    load_dotenv()
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    data_range = 'A3:H'
    while True:
        check_spreadsheet(spreadsheet_id, data_range)
        time.sleep(300)

def check_spreadsheet(spreadsheet_id, data_range):
    sheet = authorize_spreadsheets_api()
    spreadsheet_data = download_spreadsheet_data(spreadsheet_id, data_range, sheet)
    week_day = get_todays_week_day()
    todays_pubs = get_todays_unposted_publications(spreadsheet_data, week_day)
    if todays_pubs:
        post_pubs(todays_pubs, spreadsheet_id, sheet)

def authorize_spreadsheets_api():
    # Code snippet from: https://developers.google.com/sheets/api/quickstart/python
    # If modifying these scopes, delete the file token.pickle.
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    return sheet

def download_spreadsheet_data(spreadsheet_id, data_range, sheet):
    value_render_option = 'FORMULA'
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=data_range, 
                                valueRenderOption=value_render_option
                                ).execute()
    data = result.get('values', [])
    return data

def get_todays_week_day():
    week_days = [
        'понедельник',
        'вторник',
        'среда',
        'четверг',
        'пятница',
        'суббота',
        'воскресенье',        
    ]
    today = datetime.datetime.today()
    week_day = week_days[today.weekday()]
    return week_day

def get_todays_unposted_publications(spreadsheet_data, week_day):
    todays_pubs = []
    first_line_data_number = 3
    for line_number, pub_info in enumerate(spreadsheet_data, first_line_data_number):
        pub_day = pub_info[3]
        was_posted = pub_info[7]
        if week_day == pub_day.lower() and was_posted.lower() == 'нет':
            todays_pubs.append([*pub_info, line_number])
    return todays_pubs

def post_pubs(todays_pubs, spreadsheet_id, sheet):
    now_time = datetime.datetime.now().hour
    for post_vk, post_tg, post_fb, pub_day, pub_time, pub_text, pub_image, was_posted, line_number in todays_pubs:
        if now_time != pub_time:
            continue
        drive = pass_auth_gdrive()
        txt_file_name, img_file_name = download_pub_txt_and_img(pub_text, pub_image, drive)
        text = None
        if txt_file_name:
            with open(txt_file_name, 'r', encoding='utf-8') as txt_file:
                text = txt_file.read()
        
        try:
            if post_vk.lower() == 'да': post_sm.post_vkontakte(img_file_name, text)
            if post_tg.lower() == 'да': post_sm.post_telegram(img_file_name, text)
            if post_fb.lower() == 'да': post_sm.post_facebook(img_file_name, text)
        finally:
            if img_file_name: os.remove(img_file_name)
            if txt_file_name: os.remove(txt_file_name)
            update_pub_status(spreadsheet_id, line_number, sheet)

def pass_auth_gdrive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth() # Creates local webserver and auto handles authentication.
    drive = GoogleDrive(gauth)
    return drive

def download_pub_txt_and_img(pub_text, pub_image, drive):
    text_id = get_gdrive_file_id(pub_text)
    if text_id:
        txt_file_name = download_txt_from_gdrive(text_id, drive)
    else:
        txt_file_name = None
    img_id = get_gdrive_file_id(pub_image)
    if img_id:
        img_file_name = download_img_from_gdrive(img_id, drive)
    else:
        img_file_name = None
    return txt_file_name, img_file_name

def get_gdrive_file_id(text):
    urls = URLExtract().find_urls(text)
    if urls:
        parsed = urlparse(urls[0])
        file_id = parsed.query[3:]
        return file_id

def download_txt_from_gdrive(text_id, drive):
    file_txt = drive.CreateFile({'id': text_id})
    txt_name = file_txt['title']
    file_name = f'{txt_name}.txt'
    file_txt.GetContentFile( file_name, mimetype='text/plain')
    return file_name

def download_img_from_gdrive(image_id, drive):
    file_img = drive.CreateFile({'id': image_id})
    file_img.FetchMetadata(fields='title,downloadUrl')
    image_name = file_img['title']
    file_img.GetContentFile(image_name)
    return image_name

def update_pub_status(spreadsheet_id, line_number, sheet):
    cell_litera = 'H'
    cell_name = f'{cell_litera}{line_number}'
    value_input_option = 'RAW'
    body = {
        'values': [['да']]
    }
    result = sheet.values().update(spreadsheetId=spreadsheet_id, 
        valueInputOption=value_input_option, range=cell_name, 
        body=body).execute()
    return

if __name__ == '__main__':
    main()