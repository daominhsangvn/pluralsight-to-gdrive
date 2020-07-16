import requests, json, sys, re, os, re, shutil, subprocess, types, time, traceback, random
from http.cookiejar import MozillaCookieJar
from slugify import slugify

from colorama import Fore, Back, Style

class PluralSightColab(object):
    def __init__(
        self,
        options,
        downloaded_history_file_path,
        download_path=os.environ.get('FILE_PATH', './PluralSight'),
    ):
        cj = MozillaCookieJar(options.cookies)
        cj.load(ignore_expires=True, ignore_discard=True)
        self._session = requests.Session()
        self._session.cookies = cj
        self._session.headers.update(
            {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'})
        self.downloaded_history_file_path = downloaded_history_file_path
        self.download_path = download_path
        self.min_wait = options.min_wait
        self.max_wait = options.max_wait
        self.retry_delay = 30
        self.pythonversion = 3 if sys.version_info >= (3, 0) else 2

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

    def sanitize_title(self, title):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', ' ', title).replace('/', '-').replace(':', '_').replace('\\', '-').replace('*', '-').replace('<', '-').replace('>', '-').replace('|', '-').replace('?', '-').replace('"', '_')

    def download_video(self, file_path, course):
        try:
            video_data = {"clipId": course['id'], "mediaType": "mp4", "quality": "1280x720",
                          "online": True, "boundedContext": "course", "versionId": ""}
            lession_clip_data = self._session.post('https://app.pluralsight.com/video/clips/v3/viewclip', data=json.dumps(
                video_data), headers={'Content-type': 'application/json', 'Accept': 'text/plain'})
            video_link_response = lession_clip_data.json()
            try:
                video_download_link = list(
                    filter(lambda v: v['cdn'] == 'cachefly', video_link_response['urls']))[0]['url']
            except Exception as e:
                # Failed to parse video url then stop the course
                return True
            video_request = requests.get(video_download_link, stream=True)
            video_total_length = video_request.headers.get(
                'content-length')
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
            return False
        except Exception as e:
            print(e)
            print(traceback.print_exc())
            self.print_danger_text(
                "Failed to download video, retry 5 in seconds.")
            time.sleep(self.retry_delay)
            return self.download_video(file_path, course)

    def download_subtitle(self, file_path, course):
        try:
            print('[*] Downloading Subtitle...')
            subtitle_url = 'https://app.pluralsight.com/transcript/api/v1/caption/webvtt/'+course['id']+'/'+course['version']+'/en/'
            subtitle_request = requests.get(subtitle_url)
            filename, file_extension = os.path.splitext(file_path)
            subtitle_vtt_path = filename + '.vtt'
            with open(subtitle_vtt_path, 'wb') as f:
                f.write(subtitle_request.content)
                self.print_success_text(
                    "[+] Subtitle downloaded: \"" + self.sanitize_title(course['title']) + '.vtt"')

            # Convert Subtitle to srt
            print('[*] Converting Subtitle...')
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

    def download_exercise_file(self, file_path, course_id):
        try:
            response = self._session.get('https://app.pluralsight.com/learner/user/courses/' + course_id + '/exercise-files-url', headers={'Content-type': 'application/json', 'Accept': 'text/plain'})
            exercise_request_url = response.json()['exerciseFilesUrl']
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
                            "[+] Exercise files downloaded: \"" + course_id + '.zip"')
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
                            "[+] Exercise files downloaded: \"" + course_id + '.zip"')
        except Exception as e:
            print(e)
            print(traceback.print_exc())
            self.print_danger_text(
                "Failed to download exercise file, retry 5 in seconds.")
            time.sleep(self.retry_delay)
            self.download_exercise_file(file_path, course_id)

    def download_course(self, slug, target_folder, url):
        data = self.fetch_course_data(slug)

        title = data['title']
        title = title.replace(":", "_")
        title = title.replace("|", "-")
        title = title.replace("/", "-")
        title = title.replace("\"", "-")
        title = title.strip()

        base_path = os.path.abspath(os.path.join(
            self.download_path, title)).rstrip('/')
        target_path = '{target_folder}/{title}'.format(
            target_folder=target_folder, title=title)

        self.print_info_text('[+] Start Download Course: ' + title)

        is_course_downloaded = self.is_downloaded(slug)
        if is_course_downloaded:
            print('[*] Downloaded Already! Skip')
            return

        # Clean up
        if os.path.exists(base_path):
            shutil.rmtree(base_path, ignore_errors=True)

        player = self._session.get('https://app.pluralsight.com' + data['modules'][0]['clips'][0]['playerUrl'])
        scripts = re.findall(r'<script.*?>(.*?)<\/script>', player.text)
        scripts = list(filter(lambda e: 'tableOfContents' in e, scripts))
        tableOfContents = json.loads(scripts[0])
        modules = tableOfContents['props']['pageProps']['tableOfContents']['modules']
        should_skip = False
        chapters_length = str(len(modules))
        self.print_info_text('[*] Total Chapters: ' + chapters_length)
        print('')

        c_i = 0
        for m in modules:
            c_i = c_i + 1
            chapter_title = m['title'].strip()
            self.print_info_text(
                '[+] Chapter ' + str(c_i) + ' of ' + chapters_length + ': ' + chapter_title)
            chapter_path = base_path + '/' + \
                str(c_i) + ' - ' + self.sanitize_title(chapter_title)
            if not os.path.exists(chapter_path):
                os.makedirs(chapter_path)
            cl_i = 0
            clips_length = str(len(m['contentItems']))
            for c in m['contentItems']:
                cl_i = cl_i + 1
                lession_title = c['title'].strip()
                self.print_warning_text(
                    '[+] Download Lession ' + str(cl_i) + ' of ' + clips_length + ': ' + lession_title)
                lession_path = chapter_path + '/' + \
                    str(cl_i) + ' - ' + self.sanitize_title(lession_title)

                # Download Video
                should_skip = self.download_video(lession_path + '.mp4', c)

                if(should_skip):
                    self.print_danger_text("[*] Cannot download video, your account may be banned or your subscription has expired.")
                    return # break the function

                # Download Subtitles
                self.download_subtitle(lession_path + '.srt', c)

                # Download Learning Check
                # TODO NEXT    

                # Delay next video
                sleep_time = random.randint(self.min_wait, self.max_wait)
                self.print_info_text(
                    "[+] Wait %d seconds to next download to prevent banning." % (sleep_time))
                time.sleep(sleep_time)
                print('')
            print('')
        
        self.download_exercise_file(os.path.join(base_path, slug + '.zip'), slug)

        # move files to target folder
        if os.path.exists(target_path):
           shutil.rmtree(target_path)
        print("[*] Moving files from " + base_path + " to " + target_folder)
        shutil.move(base_path, target_folder)
        self.update_downloaded(slug)

    def fetch_course_data(self, slug):
        course_data_url = 'https://app.pluralsight.com/learner/content/courses/{}'.format(
            slug)
        response = self._session.get(course_data_url)
        return json.loads(response.text)

    def print_danger_text(self, text):
        print(Fore.RED + text + Style.RESET_ALL)

    def print_warning_text(self, text):
        print(Fore.YELLOW + text + Style.RESET_ALL)

    def print_success_text(self, text):
        print(Fore.GREEN + text + Style.RESET_ALL)

    def print_info_text(self, text):
        print(Fore.CYAN + text + Style.RESET_ALL)
