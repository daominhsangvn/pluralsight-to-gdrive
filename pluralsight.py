import requests
import json
import sys
import re
import os
import re
import shutil
import time
import mimetypes
import random
import traceback
from slugify import slugify
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from googleapiclient.http import MediaFileUpload                    # pylint: disable=import-error
from colorama import Fore, Back, Style

class PluralSight(object):

    def __init__(
        self,
        options,
        downloaded_history_file_path,
        drive_api,
        pool,
        download_path=os.environ.get('FILE_PATH', './PluralSight'),
    ):
        self.downloaded_history_file_path = downloaded_history_file_path
        self.download_path = download_path
        self.username = options.username
        self.password = options.password
        self.cookies = options.cookies
        self.driver_path = options.driver
        self.min_wait = options.min_wait
        self.max_wait = options.max_wait
        self.retry_delay = 30
        self.drive_api = drive_api
        self.team_drive_folder_id = options.team_drive_folder_id
        self.team_drive_id = options.team_drive_id
        self.pool = pool
        self.driver_options = Options()
        if options.headless:
            self.driver_options.add_argument("--headless")
            self.driver_options.add_argument("--no-sandbox")
            self.driver_options.add_argument('--disable-dev-shm-usage')
            self.driver_options.add_argument("--window-size=1400,600")
            self.driver_options.add_argument("--disable-gpu")
            self.driver_options.add_argument("--enable-javascript")
            self.driver_options.add_argument(
                '--user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"')
            # self.driver_options.add_argument('--user-data-dir=chrome-data')

        self.driver = webdriver.Chrome(
            executable_path=self.driver_path, chrome_options=self.driver_options)
        self.pythonversion = 3 if sys.version_info >= (3, 0) else 2
        self.login()

    def is_downloaded(self, slug):
        downloaded_history_file = open(
            self.downloaded_history_file_path, "r")
        downloaded_list = downloaded_history_file.readlines()
        downloaded_history_file.close()
        return slug + '\n' in downloaded_list

    def update_downloaded(self, slug):
        downloaded_history_file = open(
            self.downloaded_history_file_path, "a")
        downloaded_history_file.write(slug + '\n')
        downloaded_history_file.close()

    def download_course_by_url(self, url, target_folder):
        m = re.match('https://app.pluralsight.com/library/courses/(.*)', url)
        assert m, 'Failed to parse course slug from URL'
        self.download_course(m.group(1), target_folder, url)
        self.print_success_text("[*] Finished")
        print("")

    def login(self):
        self.print_warning_text('[*] Logging in...')
        self.driver.get("https://app.pluralsight.com/id/")
        self._set_input_by_id('Username', self.username)
        self._set_input_by_id('Password', self.password)
        self._click_button_by_ID('login')
        time.sleep(2)

    def sanitize_title(self, title):
        return re.sub(r'[^\x00-\x7F]+',' ', title.replace('/', '_').replace(':', '_').replace('\\', '-').replace('*', '-').replace('<', '-').replace('>', '-').replace('|', '-').replace('?', '-').replace('"', '_'))

    def download_video(self, file_path, course):
        try:
            video_download_script = (
                'var video_link_try = 0;'
                'var video_link_get_done = arguments[0];'
                'function getLink(){'
                'var xmlhttp = new XMLHttpRequest();'
                'xmlhttp.onload = function (e) {'
                'if(xmlhttp.status != 200 && video_link_try < 2) {'
                'video_link_try+=1;'
                'setTimeout(function(){'
                'getLink();'
                '}, 3000);'
                '}'
                'else {'
                'video_link_get_done(xmlhttp.response);'
                '}'
                '};'
                'xmlhttp.open("POST", "https://app.pluralsight.com/video/clips/v3/viewclip");'
                'xmlhttp.setRequestHeader("Content-Type", "application/json;charset=UTF-8");'
                'xmlhttp.send(JSON.stringify({"clipId":"' + course['clipId'] +
                '","mediaType":"mp4","quality":"1280x720","online":true,"boundedContext":"course","versionId":""}));'
                '}'
                'getLink();')
            video_link_response_text = self.driver.execute_async_script(
                video_download_script)
            video_link_response = json.loads(video_link_response_text)
            print('video_link_response_text ' + video_link_response_text)
            video_download_link = list(
                filter(lambda v: v['cdn'] == 'cachefly', video_link_response['urls']))[0]['url']
            print('video_download_link ' + video_download_link)
            video_request = requests.get(video_download_link, stream=True)
            video_total_length = video_request.headers.get(
                'content-length')
            print('video_total_length ' + str(video_total_length))
            with open(file_path, 'wb') as f:
                if not video_total_length:
                    print(video_request.content)
                    f.write(video_request.content)
                    self.print_success_text(
                        "[+] Video downloaded: \"" + self.sanitize_title(course['title']) + '.mp4"')
                else:
                    video_dl = 0
                    video_total_length = int(video_total_length)
                    for video_data in video_request.iter_content(chunk_size=4096):
                        video_dl += len(video_data)
                        f.write(video_data)
                        video_done = int(
                            10 * video_dl / video_total_length)
                        sys.stdout.write('\r[*] Downloading Video: [%s%s] %d%%' %
                                         ('=' * video_done, ' ' * (10 - video_done), int(100 * video_dl / video_total_length)))
                        sys.stdout.flush()
                    print('')
                    self.print_success_text(
                        "[+] Video downloaded: \"" + self.sanitize_title(course['title']) + '.mp4"')
        except Exception as e:
            print(e)
            print(traceback.print_exc())
            self.print_danger_text(
                "Failed to download video, retry 5 in seconds.")
            time.sleep(self.retry_delay)
            self.download_video(file_path, course)

    def download_subtitle(self, file_path, course):
        try:
            self.print_warning_text('[*] Downloading Subtitle...')
            page_content = self.driver.find_element_by_xpath(
                "//body").get_attribute('outerHTML')
            subtitles = re.findall(
                r'<track.*srclang="en".*src="(.*?)">', page_content)
            subtitle_url = 'https://app.pluralsight.com' + subtitles[0]
            subtitle_request = requests.get(subtitle_url)
            filename, file_extension = os.path.splitext(file_path)
            subtitle_vtt_path = filename + '.vtt'
            with open(subtitle_vtt_path, 'wb') as f:
                f.write(subtitle_request.content)
                self.print_success_text(
                    "[+] Subtitle downloaded: \"" + self.sanitize_title(course['title']) + '.vtt"')

            # Convert Subtitle to srt
            self.print_warning_text('[*] Converting Subtitle...')
            subtitle_srt_path = file_path
            with open(subtitle_vtt_path, 'r') as subtitle_file:
                subtitle_data = subtitle_file.read()
                subtitle_data = re.sub(r"WEBVTT\n", "", subtitle_data)
                subtitle_data = re.sub(
                    r"X-TIMESTAMP-MAP.*\n", "", subtitle_data)
                subtitle_data = re.sub(
                    r"(\d\d):(\d\d):(\d\d)\.(\d+)", r"\1:\2:\3,\4", subtitle_data)
                sub_lines = re.findall(r"00.*", subtitle_data)
                li = 1
                for l in sub_lines:
                    subtitle_data = subtitle_data.replace(
                        l, str(li) + "\n" + l)
                    li = li + 1
                sf = open(subtitle_srt_path, "w")
                sf.write(subtitle_data)
                sf.close()
            os.remove(subtitle_vtt_path)
            self.print_success_text(
                "[+] Subtitle converted: \"" + self.sanitize_title(course['title']) + '.srt"')
        except Exception as e:
            print(e)
            print(traceback.print_exc())
            self.print_danger_text(
                "Failed to download subtitle, retry 5 in seconds.")
            time.sleep(self.retry_delay)
            self.download_subtitle(file_path, course)

    def download_exercise_file(self, file_path, course_data):
        try:
            exercise_download_script = (
                'var exercise_get_done = arguments[0];'
                'var xmlhttp = new XMLHttpRequest();'
                'xmlhttp.onload = function (e) {'
                'exercise_get_done(xmlhttp.response);'
                '};'
                'xmlhttp.open("GET", "https://app.pluralsight.com/learner/user/courses/' +
                course_data['id'] + '/exercise-files-url");'
                'xmlhttp.setRequestHeader("Content-Type", "application/json;charset=UTF-8");'
                'xmlhttp.send();'
            )
            exercise_link_response = json.loads(
                self.driver.execute_async_script(exercise_download_script))
            exercise_request_url = exercise_link_response['exerciseFilesUrl']
            if exercise_request_url is not None:
                exercise_request = requests.get(
                    exercise_request_url, stream=True)
                exercise_files_total_length = exercise_request.headers.get(
                    'content-length')
                exercise_output_path = file_path
                with open(exercise_output_path, 'wb') as f:
                    if not exercise_files_total_length:
                        f.write(exercise_request.content)
                        self.print_success_text(
                            "[+] Exercise files downloaded: \"" + slugify(course_data['title']) + '.zip"')
                    else:
                        exercise_dl = 0
                        exercise_files_total_length = int(
                            exercise_files_total_length)
                        for excersie_data in exercise_request.iter_content(chunk_size=4096):
                            exercise_dl += len(excersie_data)
                            f.write(excersie_data)
                            exercise_done = int(
                                10 * exercise_dl / exercise_files_total_length)
                            sys.stdout.write('\r[*] Downloading Exercise Files: [%s%s] %d%%' %
                                             ('=' * exercise_done, ' ' * (10 - exercise_done), int(100 * exercise_dl / exercise_files_total_length)))
                            sys.stdout.flush()
                        print('')
                        self.print_success_text(
                            "[+] Exercise files downloaded: \"" + slugify(course_data['title']) + '.zip"')
        except Exception as e:
            print(e)
            print(traceback.print_exc())
            self.print_danger_text(
                "Failed to download exercise file, retry 5 in seconds.")
            time.sleep(self.retry_delay)
            self.download_exercise_file(file_path, course_data)

    #def download_learning_check(self):
        # Download Learning Check
        # self.driver.get('https://app.pluralsight.com/score/learning-check/' + slug)
        ##
        # next_btn_visi = False
        ##
        # try:
        # wait for the player to be presented
        # next_btn_elm = WebDriverWait(self.driver, 10).until(
        # EC.presence_of_element_located((By.XPATH, '//main[@id="ps-main"]//button[contains(@class, "nextQuestionButton")]'))
        # )
        # next_btn_visi = True
        # except NoSuchElementException:
        # next_btn_visi = False
        ##
        # if next_btn_visi:
        # next_btn_elm.click()
        ##
        # learning_found = False
        # try:
        # wait for the player to be presented
        # learning_container = WebDriverWait(self.driver, 30).until(
        # EC.presence_of_element_located((By.XPATH, '//main[@id="ps-main"]//div[contains(@class, "learningCheckQuestionContainer")]'))
        # )
        # learning_found = True
        # except NoSuchElementException:
        # learning_found = False
        # if learning_found:
        # is_last_question = False
        # while not is_last_question:
        # WebDriverWait(self.driver, 30).until(
        # EC.presence_of_element_located((By.XPATH, '//main[@id="ps-main"]//div[contains(@class, "learningCheckQuestionContainer")]'))
        # )
        # Scrape question content
        # question = self.driver.find_element_by_xpath('//main[@id="ps-main"]//div[contains(@class, "learningCheckQuestionContainer")]//div[contains(@class, "textStem")]').text
        # Scrape answers content
        # answers = list(map(lambda a: a.text, self.driver.find_elements_by_xpath('//main[@id="ps-main"]//div[contains(@class, "learningCheckQuestionContainer")]//ul[contains(@class, "unansweredChoices")]/li')))
        # click to random awnser to trigger validation and collect correct anwser
        # self.driver.find_element_by_xpath('//main[@id="ps-main"]//div[contains(@class, "learningCheckQuestionContainer")]//ul[contains(@class, "unansweredChoices")]/li['+str(random.randint(1, len(answers)))+']').click()
        # Wait for the answer container appears
        # answered_container = WebDriverWait(self.driver, 30).until(
        # EC.presence_of_element_located((By.XPATH, '//main[@id="ps-main"]//div[contains(@class, "learningCheckQuestionAnsweredContainer")]//ul[contains(@class, "answeredChoices")]'))
        # )
        # Find correct answer
        # correct_answer_target = self.driver.find_element_by_xpath('//main[@id="ps-main"]//div[contains(@class, "learningCheckQuestionAnsweredContainer")]//ul[contains(@class, "answeredChoices")]/li/p[contains(text(), "Correct")]/..')
        # all_answer = self.driver.find_elements_by_xpath('//main[@id="ps-main"]//div[contains(@class, "learningCheckQuestionAnsweredContainer")]//ul[contains(@class, "answeredChoices")]/li')
        # correct_answer_index = all_answer.index(correct_answer_target)
        # print('Correct answer ' + str(correct_answer_index))
        # time.sleep(random.randint(3, 5))
        ##
        # Next question
        # self._click_button_by_XPATH('//main[@id="ps-main"]//button[contains(@class, "nextQuestionButton")]')

    def download_course(self, slug, target_folder, url):
        data = self.fetch_course_data(slug)
        #course_id = data['courseId']
        #couse_title = data['title'].strip()
        title = data['title']
        title = title.replace(":", "_")
        title = title.replace("|", "-")
        title = title.replace("/", "-")
        title = title.replace("\"", "-")
        title = title.strip()

        base_path = os.path.abspath(os.path.join(
            self.download_path, title)).rstrip('/')
        # target_path = '{target_folder}/{title}'.format(
        #    target_folder=target_folder, title=title)

        self.print_info_text('[+] Start Download Course: ' + title)

        is_course_downloaded = self.is_downloaded(slug)
        if is_course_downloaded:
            self.print_info_text('[+] Downloaded Already! Skip')
            return

        # Clean up
        if os.path.exists(base_path):
            shutil.rmtree(base_path, ignore_errors=True)

        # https://www.c-sharpcorner.com/article/how-to-search-google-drive-files-progamatically/
        search_results = self.drive_api.files().list(q="name='"+title+"' and '"+self.team_drive_folder_id+"' in parents",
                                                     pageSize=1,
                                                     corpora="teamDrive",
                                                     includeItemsFromAllDrives=True,
                                                     supportsAllDrives=True,
                                                     driveId=self.team_drive_id).execute()
        # Remove previous uploads in drive
        if len(search_results['files']) > 0:
            self.drive_api.files().delete(fileId=search_results['files'][0]['id'],
                                          supportsAllDrives=True).execute()

        chapters_length = str(len(data['modules']))
        self.print_info_text('[*] Total Chapters: ' + chapters_length)
        print('')

        c_i = 0
        for m in data['modules']:
            c_i = c_i + 1
            chapter_title = m['title'].strip()
            self.print_info_text(
                '[+] Chapter ' + str(c_i) + ' of ' + chapters_length + ': ' + chapter_title)
            chapter_path = base_path + '/' + \
                str(c_i) + ' - ' + self.sanitize_title(chapter_title)
            if not os.path.exists(chapter_path):
                os.makedirs(chapter_path)
            cl_i = 0
            clips_length = str(len(m['clips']))
            for c in m['clips']:
                cl_i = cl_i + 1
                lession_title = c['title'].strip()
                self.print_warning_text(
                    '[+] Download Lession ' + str(cl_i) + ' of ' + clips_length + ': ' + lession_title)
                lession_path = chapter_path + '/' + \
                    str(cl_i) + ' - ' + self.sanitize_title(lession_title)

                # Open the player
                self.driver.get('https://app.pluralsight.com' + c['playerUrl'])
                video_not_found = True
                try:
                    # wait for the player to be presented
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//div[@class="player-wrapper"]//video'))
                    )
                    video_not_found = False
                except Exception as e:
                    print(e)
                    print(traceback.print_exc())
                    video_not_found = True

                if video_not_found:
                    self.print_danger_text(
                        "[+] You may need to upgrade your plan to be able to access this course!")
                    return

                # Wait a bit before making the request or will get 429
                time.sleep(self.retry_delay)

                self.download_video(lession_path + '.mp4', c)

                self.download_subtitle(lession_path + '.srt', c)

                # Delay next video
                sleep_time = random.randint(self.min_wait, self.max_wait)
                self.print_info_text(
                    "[+] Wait %d seconds to next download to prevent banning." % (sleep_time))
                time.sleep(sleep_time)
                print('')
            print('')

        self.download_exercise_file(os.path.join(
            base_path, slugify(data['title'])) + '.zip', data)

        # self.download_learning_check()

        # create folder in drive first
        new_folder_id = self.gdrive_create_folder(
            self.team_drive_folder_id, title)

        self.upload_files(base_path, new_folder_id, slug, True)

        # Clean up
        if os.path.exists(base_path):
            shutil.rmtree(base_path, ignore_errors=True)

        self.update_downloaded(slug)

    def gdrive_create_folder(self, parent_id, folder_name):
        try:
            self.print_warning_text(
                '[*] (GDrive) Creating Folder: \"' + folder_name + '"')
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            create_folder_response = self.drive_api.files().create(body=file_metadata,
                                                                   fields='id', supportsTeamDrives=True).execute()
            return create_folder_response.get('id')
        except Exception as e:
            print(e)
            print(traceback.print_exc())
            self.print_danger_text(
                "Failed to create GDrive folder, retry 5 in seconds.")
            time.sleep(5)
            self.gdrive_create_folder(parent_id, folder_name)

    def gdrive_upload_file(self, parent_id, file_name, file_path):
        try:
            file_metadata = {'name': file_name, 'parents': [parent_id]}
            file_ext = os.path.splitext(file_path)
            file_mime_type = 'text/srt'
            if file_ext != 'srt':
                file_mime_type = mimetypes.guess_type(file_path)[0]
            media = MediaFileUpload(
                file_path, mimetype=file_mime_type, chunksize=1024*1024, resumable=True)
            # self.drive_api.files().create(body=file_metadata,
            #                                    media_body=media,
            #                                    fields='id', supportsTeamDrives=True).execute()
            upload_file_request = self.drive_api.files().create(body=file_metadata,
                                                                media_body=media,
                                                                fields='id', supportsTeamDrives=True)
            response = None
            while response is None:
                status, response = upload_file_request.next_chunk()
                progress = 100
                if status:
                    progress = int(status.progress() * 100)

                sys.stdout.write('\r[*] (GDrive) Uploading \"' +
                                 file_name + '" [%d%%]' % (progress))
                sys.stdout.flush()
            print('')
        except Exception as e:
            print(e)
            print(traceback.print_exc())
            self.print_danger_text(
                "Failed to upload file, retry 5 in seconds.")
            time.sleep(5)
            self.gdrive_upload_file(parent_id, file_name, file_path)

    def upload_files(self, directory, drive_folder_id, slug, root):
        if root:
            self.print_info_text("[+] Start uploading to GDrive")
        for file1 in os.listdir(directory):
            file_folder_path = os.path.join(directory, file1)
            if os.path.isfile(file_folder_path):
                self.gdrive_upload_file(
                    drive_folder_id, file1, file_folder_path)
            else:
                new_folder_id = self.gdrive_create_folder(
                    drive_folder_id, file1)
                self.upload_files(file_folder_path, new_folder_id, slug, False)
        if root:
            self.print_info_text("[+] Upload done!")
            # root request (first call)
            return (slug, directory)

    def fetch_course_data(self, slug):
        course_data_url = 'https://app.pluralsight.com/learner/content/courses/{}'.format(
            slug)
        self.driver.get(course_data_url)
        bd_el = self.driver.find_element_by_tag_name('body')
        return json.loads(bd_el.text)

    def _click_button_by_XPATH(self, button_XPATH):
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.XPATH, button_XPATH))).click()

    def _click_button_by_ID(self, button_ID):
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, button_ID))).click()

    def _set_input_by_id(self, input_box_id, input_value):
        input_box = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, input_box_id))
        )
        self.clear_text_box(input_box)
        input_box.send_keys(input_value)

    def _set_input_by_XPATH(self, input_box_XPATH, input_value):
        input_box = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.XPATH, input_box_XPATH))
        )
        self.clear_text_box(input_box)
        input_box.send_keys(input_value)

    def _click_by_link_text(self, text):
        WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable((By.LINK_TEXT, text))
        ).click()

    def set_select(self, select_ID, value):
        box = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, select_ID)))

        option = Select(box)
        option.select_by_value(value)

    def set_select_by_class(self, class_name, value):
        box = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, class_name)))

        option = Select(box)
        option.select_by_value(value)

    def clear_text_box(self, elem):
        time.sleep(2)
        while elem.get_attribute('value') != '':
            elem.send_keys(Keys.BACKSPACE)

    def print_danger_text(self, text):
        print(Fore.RED + text + Style.RESET_ALL)

    def print_warning_text(self, text):
        print(Fore.YELLOW + text + Style.RESET_ALL)

    def print_success_text(self, text):
        print(Fore.GREEN + text + Style.RESET_ALL)

    def print_info_text(self, text):
        print(Fore.CYAN + text + Style.RESET_ALL)
