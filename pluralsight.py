import requests, json, sys, re, os, re, shutil, time
from slugify import slugify
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from colorama import Fore, Back, Style
#import magic
#mime = magic.Magic(mime=True)

class PluralSight(object):

    def __init__(
        self,
        options,
        downloaded_history_file_path,
        drive_api,
        download_path=os.environ.get('FILE_PATH', './PluralSight'),
    ):
        self.downloaded_history_file_path = downloaded_history_file_path
        self.download_path = download_path
        self.username = options.username
        self.password = options.password
        self.cookies = options.cookies
        self.driver_path = options.driver
        self.drive_api = drive_api
        self.driver_options = Options()
        if options.headless:
            self.driver_options.add_argument("--headless")
            self.driver_options.add_argument("--no-sandbox")
            self.driver_options.add_argument('--disable-dev-shm-usage')
            self.driver_options.add_argument("--window-size=1400,600")
            self.driver_options.add_argument("--disable-gpu")
            self.driver_options.add_argument("--enable-javascript")
            self.driver_options.add_argument('--user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"')
            #self.driver_options.add_argument('--user-data-dir=chrome-data')
        
        self.driver = webdriver.Chrome(executable_path=self.driver_path, chrome_options=self.driver_options)
        self.pythonversion = 3 if sys.version_info >= (3, 0) else 2
        self.login()

    def is_unicode_string(self, string):
        if (self.pythonversion == 3 and isinstance(string, str)) or (self.pythonversion == 2 and isinstance(string, unicode)):
            return True

        else:
            return False

    def is_downloaded(self, slug):
        downloaded_history_file = open(self.downloaded_history_file_path, "r") 
        downloaded_list = downloaded_history_file.readlines()
        downloaded_history_file.close()
        return slug + '\n' in downloaded_list

    def update_downloaded(self, slug):
        downloaded_history_file = open(self.downloaded_history_file_path, "a") 
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
        print('Login Source ' + self.driver.page_source)
        self._set_input_by_id('Username', self.username)
        self._set_input_by_id('Password', self.password)
        self._click_button_by_ID('login')
        time.sleep(2)

    def sanitize_title(self, title):
        return title.replace('/','_').replace(':','_').replace('\\','-').replace('*','-').replace('<','-').replace('>','-').replace('|','-').replace('?','-')

    def download_course(self, slug, target_folder, url):
        is_course_downloaded = self.is_downloaded(slug)
        if is_course_downloaded:
            print('[*] Downloaded Already! Skip')
            return

        data = self.fetch_course_data(slug)

        title = data['title']
        title = title.replace(":", "_")
        title = title.replace("|", "-")
        title = title.replace("/", "-")

        base_path = os.path.abspath(os.path.join(self.download_path, title)).rstrip('/')
        target_path = '{target_folder}/{title}'.format(target_folder=target_folder, title=title)

        self.print_info_text('[+] Start Download Course: ' + title)

        # Clean up
        if os.path.exists(base_path):
            shutil.rmtree(base_path)

        chapters_length = str(len(data['modules']))
        self.print_info_text('[*] Total Chapters: ' + chapters_length)
        print('')

        c_i = 0
        for m in data['modules']:
            c_i = c_i + 1
            self.print_info_text('[*] Chapter ' + str(c_i) + ' of ' + chapters_length +': '+ m['title'])
            chapter_path = base_path + '/' + str(c_i) + ' - ' + self.sanitize_title(m['title'])
            if not os.path.exists(chapter_path):
                os.makedirs(chapter_path)
            cl_i = 0
            clips_length = str(len(m['clips']))
            for c in m['clips']:
                cl_i = cl_i + 1
                self.print_warning_text('[*] Downloading Lession ' + str(cl_i) + ' of ' + clips_length + ': ' + c['title'])
                lession_path = chapter_path + '/' + str(cl_i) + ' - ' + self.sanitize_title(c['title'])
                #if not os.path.exists(lession_path):
                #    os.makedirs(lession_path)
                self.driver.get('https://app.pluralsight.com' + c['playerUrl'])
                video_not_found = True
                try:
                    # wait for the player to be presented
                    player_box = WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.XPATH, '//div[@class="player-wrapper"]//video'))
                    )
                    video_not_found = False
                except NoSuchElementException:
                    video_not_found = True
                    
                if video_not_found:
                    self.print_danger_text("[+] You may need to upgrade your plan to be able to access this course")
                    return;

                # Download Subtitles
                self.print_warning_text('[*] Downloading Subtitle...')
                page_content = self.driver.find_element_by_xpath("//body").get_attribute('outerHTML')
                subtitles = re.findall(r'<track.*srclang="en".*src="(.*?)">', page_content)
                subtitle_url = 'https://app.pluralsight.com' + subtitles[0]
                subtitle_request = requests.get(subtitle_url)
                with open(lession_path + '.vtt', 'wb') as f:
                    f.write(subtitle_request.content)
                    self.print_success_text("Downloaded to: " + lession_path + '.vtt')

                # Download Video
                self.print_warning_text('[*] Downloading Video...')
                video_download_script = (
                    'var video_link_get_done = arguments[0];'
                    'var xmlhttp = new XMLHttpRequest();'
                    'xmlhttp.onload = function (e) {'
                    'video_link_get_done(xmlhttp.response);'
                    '};'
                    'xmlhttp.open("POST", "https://app.pluralsight.com/video/clips/v3/viewclip");'
                    'xmlhttp.setRequestHeader("Content-Type", "application/json;charset=UTF-8");'
                    'xmlhttp.send(JSON.stringify({"clipId":"'+ c['clipId'] +'","mediaType":"mp4","quality":"1280x720","online":true,"boundedContext":"course","versionId":""}));'
                    )
                video_link_response = json.loads(self.driver.execute_async_script(video_download_script))
                video_download_link = list(filter(lambda v: v['cdn'] == 'cachefly', video_link_response['urls']))[0]['url']
                video_request = requests.get(video_download_link)
                with open(lession_path + '.mp4', 'wb') as f:
                    f.write(video_request.content)
                    self.print_success_text("Downloaded to: " + lession_path + '.mp4')

                # Download Exercise files by using XHRequest
                # https://app.pluralsight.com/learner/user/courses<course_id>/exercise-files-url
                # >> {exerciseFilesUrl: ''}

                # Download Learning Check

            print('')
                
        # Upload files to drive
        target_drive_folder_id = '1IE8hnv6GO4cRtIoo3UVYlYlsn-Gaw0uz'
        #self.upload_files(base_path, target_drive_folder_id)
            

        # move files to target folder
        #if os.path.exists(target_path):
        #    shutil.rmtree(target_path)
        #print("[*] Moving files from " + base_path + " to " + target_folder)
        #shutil.move(base_path, target_folder)
        #self.update_downloaded(slug)

    #def upload_files(self, directory, drive_folder_id):
    #    for file1 in listdir(base_path):
    #        file_folder_path = os.path.join(base_path, file1)
    #        if os.path.isfile(file_folder_path):
    #            # upload file to drive
    #            self.print_warning_text('[*] Uploading ' + file_folder_path)
    #            file_metadata = {'name': file1, 'parents': [drive_folder_id]}
    #            media = MediaFileUpload(file_folder_path, mimetype=mime.from_file(file_folder_path))
    #            file = self.drive_api.files().create(body=file_metadata,
    #                                                media_body=media,
    #                                                fields='id').execute()
    #        else:
    #            # create folder in drive, get new folderId and loop upload in the folder
    #            self.print_warning_text('[*] Creating Folder ' + file_folder_path)
    #            file_metadata = {
    #                'name': file1,
    #                'mimeType': 'application/vnd.google-apps.folder'
    #            }
    #            file = self.drive_api.files().create(body=file_metadata,
    #                                                fields='id').execute()
    #            new_folder_id = file.get('id')
    #            self.upload_files(file_folder_path, new_folder_id)
        

    def fetch_course_data(self, slug):
        course_data_url = 'https://app.pluralsight.com/learner/content/courses/{}'.format(slug)
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
