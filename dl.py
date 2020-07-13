import sys, os, argparse
from pluralsight import PluralSight
import pickle
import os.path
from os import chdir, listdir, stat
from googleapiclient.discovery import build                 # pylint: disable=import-error
from google_auth_oauthlib.flow import InstalledAppFlow      # pylint: disable=import-error
from google.auth.transport.requests import Request          # pylint: disable=import-error
import multiprocessing as mp

SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service

def main():
    parser = argparse.ArgumentParser(
        description='A cross-platform python based utility to download courses from PluralSight for personal offline use.', conflict_handler="resolve")
    parser.add_argument(
        'course', help="PluralSight course url or file containing list of courses.", type=str)

    authentication = parser.add_argument_group("Authentication")
    authentication.add_argument(
        '-c', '--cookies',
        dest='cookies',
        type=str,
        help="Cookies to authenticate with.", metavar='')
    authentication.add_argument(
        '-u', '--username',
        dest='username',
        type=str,
        help="Username to authenticate with.", metavar='')
    authentication.add_argument(
        '-p', '--password',
        dest='password',
        type=str,
        help="Password to authenticate with.", metavar='')

    other = parser.add_argument_group("Others")
    other.add_argument(
        '-t', '--target',
        dest='target_folder',
        type=str,
        help="Destination folder", metavar='')
    other.add_argument(
        '-d', '--driver',
        dest='driver',
        default="driver/chromedriver.exe",
        type=str,
        help="Chrome driver execution file", metavar='')
    other.add_argument(
        '-s', '--headless',
        dest='headless',
        default=False,
        type=bool,
        help="Headless mode", metavar='')

    gdrive = parser.add_argument_group("GDrive")
    gdrive.add_argument(
        '-fi', '--folder-id',
        dest='team_drive_folder_id',
        type=str,
        help="Folder Id in Team Drive where the files will be uploaded to", metavar='')
    gdrive.add_argument(
        '-di', '--drive-id',
        dest='team_drive_id',
        type=str,
        help="Team Drive Id", metavar='')

    options = parser.parse_args()

    drive = authenticate()

    #result = drive.teamdrives().list(q="name='Fr33C0ur3s' and mimeType='application/vnd.google-apps.folder'", pageSize=10).execute()
    #result = drive.files().list(q="name='Angular Fundamentals' and '1IE8hnv6GO4cRtIoo3UVYlYlsn-Gaw0uz' in parents",
    #                            pageSize=1, corpora="teamDrive",
    #                            includeItemsFromAllDrives=True, supportsAllDrives=True,
    #                            driveId="0AO9IUAFfuvC0Uk9PVA").execute()

    #print(result)
    #result = drive.teamdrives().get(teamDriveId=target_drive_folder['id']).execute()

    #print(result)

    #return
    
    if not os.path.exists(options.target_folder):
        os.makedirs(options.target_folder)

    downloaded_history_file_name = "downloaded.txt"
    downloaded_history_file_path = "{target_folder}/{file_name}".format(target_folder=options.target_folder, file_name=downloaded_history_file_name)
    if not os.path.exists(downloaded_history_file_path):
        downloaded_history_file = open(downloaded_history_file_path, "w") 
        downloaded_history_file.write("")
        downloaded_history_file.close()
    
    #course_url = options.course
    if os.path.isfile(options.course):
        f_in = open(options.course)
        course_urls = [line for line in (l.strip() for l in f_in) if line]
        f_in.close()

    pool = mp.Pool(mp.cpu_count())

    print("[+] Found " + str(len(course_urls)) + " COURSES\n")
    dl = PluralSight(options, downloaded_history_file_path, drive, pool)
    
    for co in course_urls:
        dl.download_course_by_url(co, options.target_folder)

    # Close the pool and terminate workers
    pool.close()
    
    print("")
    print("[+] DONE !")
    print("")

if __name__ == "__main__":
    main()
