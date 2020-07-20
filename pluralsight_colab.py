import requests, json, sys, re, os, re, shutil, subprocess, types, time, traceback, random
from pyppeteer import launch
from pyppeteer.launcher import Launcher
from pyppeteer_stealth import stealth
import asyncio
from http.cookiejar import MozillaCookieJar

from colorama import Fore, Back, Style


class PluralSightColab(object):
    def __init__(
            self,
            options,
            downloaded_history_file_path,
            download_path=os.environ.get('FILE_PATH', './PluralSight'),
    ):
        self._session = requests.Session()
        self._session.headers.update(
            {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'})
        self.downloaded_history_file_path = downloaded_history_file_path
        self.download_path = download_path
        self.min_wait = options.min_wait
        self.max_wait = options.max_wait
        self.username = options.username
        self.password = options.password
        self.cookies = options.cookies
        self.user_agent = options.user_agent if options.user_agent != None else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36"
        self.proxy = options.proxy
        self.executablePath = options.executablePath
        self.retry_delay = 30
        self.pythonversion = 3 if sys.version_info >= (3, 0) else 2

    def is_unicode_string(self, string):
        if (self.pythonversion == 3 and isinstance(string, str)) or (
                self.pythonversion == 2 and isinstance(string, unicode)):
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

    async def handle_request(self, request):
      print('('+request.method+') ' + request.url)
      response_data = dict()
      if request.url == 'https://app.pluralsight.com/web-analytics/api/v1/dvs/page':
        response_data['status'] = 401
        response_data['body'] = 'Unauthorized'
        response_data['contentType'] = 'text/plain; charset=utf-8'
        return await request.respond(response_data)
      elif request.url == 'https://s2.pluralsight.com/typography/726153/0017815A7428471DD.css':
        response_data['body'] = ''
        response_data['contentType'] = 'text/css'
        return await request.respond(response_data)
      elif request.url == 'https://s2.pluralsight.com/typography/726153/0017815A7428471DD.css':
        response_data['body'] = '{"status":200,"requestId":"eaecba18cb974dcb8188b0f64d0e08b7","client":"pluralsight","id":{"tntId":"eb4e367e3aa040b6b25dc408964155a8.38_0","marketingCloudVisitorId":"26863548497945868433394706043348480494"},"edgeHost":"mboxedge38.tt.omtrdc.net","prefetch":{},"execute":{"pageLoad":{"options":[{"content":[{"type":"setHtml","selector":"#right > DIV.banner:eq(0)","cssSelector":"#right > DIV:nth-of-type(1)","content":"<div class=\"marketing-banner\">\n\t<div class=\"marketing-banner-text\">\n\t\t<div class=\"marketing-banner-text-wrapper\">\n\t\t<div class=\"marketing-banner-title\">\n\t\t\t<div class=\"main-title\"><img alt=\"Stay home. Skill up.\" src=\"https://www.pluralsight.com/content/dam/pluralsight2/target/login/skill-up.png\"></div>\n\t\t\t<div class=\"image-bottom\"><img class=\"image-for-large\" alt=\"Illustration of working at home\" src=\"https://www.pluralsight.com/content/dam/pluralsight2/target/login/free-april-main.png\"><img class=\"image-for-small\" alt=\"Illustration of working at home 2\" src=\"https://www.pluralsight.com/content/dam/pluralsight2/target/login/free-april-single.png\"></div>\n\t\t</div>\n\t</div>\n</div>\n\n<style>\n#right {position: relative;}\n.banner {\n  background-image: unset;\n  background-color: black;\n  background-position: center center;\n  position: absolute;\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n}\n .banner .marketing-banner {\n    width: 100%;\n    padding: 30px 0;\n    position: absolute;\n    left: 50%;\n    top: 50%;\n    transform: translate(-50%, -50%);\n    text-align: center;\n    display: flex;\n  }\n  \n  .banner .marketing-banner-text {\n    display: flex;\n    flex-direction: column;\n    margin-bottom: 0;\n  }\n .banner .marketing-banner .main-title {line-height: 1; margin-bottom:80px;}\n .banner .marketing-banner .main-title img {width: 80%;}\n .banner .marketing-banner .sub-title img {width: 40%;}\n .banner .marketing-banner .image-bottom {position: relative;}\n\n  .banner .marketing-banner-text-wrapper {\n        margin-top: auto;\n   }\n.banner .psds-button--gradient{\n    background: linear-gradient(103.33deg, #EC0090 0%, #F15A29 100%);\n    border: 1px solid transparent;\n    width: 200px;\n    font-weight: 700;\n    font-size: 14px;\n    border-radius: 2px;\n    padding: 15px 30px;\n    height: unset;\n    text-transform: uppercase;\n    letter-spacing: 1px;\n    outline: none;\n    transition: box-shadow .3s ease-in-out;\n    margin-top: 50px;\n    margin-left: auto;\n    margin-right: auto;\n    color: #fff;\n     display: block;\n     z-index: 1;\n  }\n  .banner .psds-button--gradient:hover, \n  .banner .psds-button--gradient:focus {\n    border: 1px solid transparent;\n    box-shadow: unset;\n    background: linear-gradient(103.33deg, #EC0090 0%, #F15A29 100%);\n    color: white;\n  }\n \n  @media only screen and (max-width: 1366px) {\n        .banner .psds-button--gradient {margin-bottom: 100px;}\n        .image-for-small {display: block; margin-left: auto; margin-right: auto;}\n        .image-for-large {display: none;}\n  }\n  @media only screen and (min-width: 1200px) {\n        .banner .marketing-banner {padding: 0;}\n        .banner .marketing-banner .image-bottom {margin-top: -50px;}\n        .banner .psds-button--gradient {margin-bottom: 0;}\n        .image-for-small {display: none;}\n        .image-for-large {display: block; width: 100%;}\n  }\n</style>"}],"type":"actions","responseTokens":{"activity.id":"339721","experience.id":"1","experience.name":"Variation 1","activity.name":"Login | Free April","profile.prospect_var":"customer"}}]}}}'
        response_data['contentType'] = 'application/json;charset=UTF-8'
        return await request.respond(response_data)
      elif request.url == 'https://api.segment.io/v1/p':
        response_data['body'] = '''{
          "success": true
        }'''
        response_data['contentType'] = 'application/json;charset=UTF-8'
        return await request.respond(response_data)
      elif request.url == 'https://cdn.wootric.com/wootric-sdk.js':
        r = requests.get(request.url, allow_redirects=True)
        response_data['body'] = r.content
        response_data['contentType'] = 'application/javascript'
        return await request.respond(response_data)
      elif request.url == 'https://edge.fullstory.com/s/fs.js':
        r = requests.get(request.url, allow_redirects=True)
        response_data['body'] = r.content
        response_data['contentType'] = 'application/javascript'
        return await request.respond(response_data)
      elif request.url == 'https://ssl.widgets.webengage.com/js/webengage-min-v-6.0.js':
        r = requests.get(request.url, allow_redirects=True)
        response_data['body'] = r.content
        response_data['contentType'] = 'application/javascript'
        return await request.respond(response_data)
      elif request.url == 'https://fast.appcues.com/30489.js':
        r = requests.get(request.url, allow_redirects=True)
        response_data['body'] = r.content
        response_data['contentType'] = 'application/javascript'
        return await request.respond(response_data)
      return await request.continue_()

    async def login(self):
        try:
            self.print_warning_text('[*] Logging in...')
            if self.cookies != None and os.path.isfile(self.cookies):
                self.print_warning_text('[*] Using cookies...')
                cj = MozillaCookieJar(self.cookies)
                cj.load(ignore_expires=True, ignore_discard=True)
                self._session = requests.Session()
                self._session.cookies = cj
                self._session.headers.update({'user-agent': self.user_agent})
                if self.proxy != None:
                    self.print_warning_text('[*] Using proxy ' + self.proxy)
                    proxies = {'http': self.proxy}
                    self._session.proxies.update(proxies)
                ip_response = self._session.get("http://httpbin.org/ip")
                self.print_info_text("[+] Session IP")
                print(ip_response.content)
                self.print_success_text('[+] Login successful!')
                return True
            else:
                args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-infobars',
                    '--window-position=0,0',
                    '--ignore-certifcate-errors',
                    '--ignore-certifcate-errors-spki-list',
                    '--user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3312.0 Safari/537.36"'
                ]
                launch_options = dict()
                launch_options['headless'] = True
                launch_options['args'] = args
                launch_options['ignoreHTTPSErrors'] = True
                launch_options['userDataDir'] = './temp'
                if self.executablePath:
                    launch_options['executablePath'] = self.executablePath
                #print(' '.join(Launcher().cmd))
                browser = await launch(launch_options)
                context = await browser.createIncognitoBrowserContext()
                page = await context.newPage()
                await stealth(page)
                await page.setJavaScriptEnabled(True)
                #await page.setRequestInterception(True)
                await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36')
                await page.setViewport({'width': 1600, 'height': 900})
                #page.on('request', lambda req: asyncio.ensure_future(self.handle_request(req)))
                #page.on('response', lambda res: print('('+str(res.status)+') ' + res.url))
                #page.on('requestfailed', lambda res: print('('+str(res.status)+') ' + res.url))
                await page.goto('https://app.pluralsight.com/id?')
                await page.waitFor('#Username')
                await page.type('#Username', self.username)
                await page.type('#Password', self.password)
                await page.click('#login')
                await page.waitForNavigation()
                page_content = await page.evaluate('''() => {return document.body.innerHTML}''')
                if 'Please complete the security check to access the site' in page_content:
                    print(page_content)
                    return False
                cookies = await page.cookies()
                cd = dict()
                for c in cookies:
                    cd[c['name']] = c['value']
                requests.utils.add_dict_to_cookiejar(self._session.cookies, cd)
                self.print_success_text('[+] Login successful!')
                return True
        except Exception as e:
            print(e)
            print(traceback.print_exc())
            self.print_danger_text('[+] Login Failed!')
            return False

    async def download_course_by_url(self, url, target_folder):
        m = re.match('https://app.pluralsight.com/library/courses/(.*)', url)
        assert m, 'Failed to parse course slug from URL'
        await self.download_course(m.group(1), target_folder, url)
        self.print_success_text("[*] Finished")
        print("")

    def sanitize_title(self, title):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', ' ', title).replace('/', '-').replace(':', '_').replace(
            '\\', '-').replace('*', '-').replace('<', '-').replace('>', '-').replace('|', '-').replace('?',
                                                                                                       '-').replace('"',
                                                                                                                    '_')

    def download_video(self, file_path, course):
        try:
            video_data = {"clipId": course['id'], "mediaType": "mp4", "quality": "1280x720",
                          "online": True, "boundedContext": "course", "versionId": ""}
            lession_clip_data = self._session.post('https://app.pluralsight.com/video/clips/v3/viewclip',
                                                   data=json.dumps(
                                                       video_data),
                                                   headers={'Content-type': 'application/json', 'Accept': 'text/plain'})
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
                                         ('=' * video_done, ' ' * (10 - video_done),
                                          int(100 * video_dl / video_total_length)))
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
            subtitle_url = 'https://app.pluralsight.com/transcript/api/v1/caption/webvtt/' + course['id'] + '/' + \
                           course['version'] + '/en/'
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
            response = self._session.get(
                'https://app.pluralsight.com/learner/user/courses/' + course_id + '/exercise-files-url',
                headers={'Content-type': 'application/json', 'Accept': 'text/plain'})
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
                                             ('=' * exercise_done, ' ' * (10 - exercise_done),
                                              int(100 * exercise_dl / exercise_files_total_length)))
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

    async def download_course(self, slug, target_folder, url):
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

                if (should_skip):
                    self.print_danger_text(
                        "[*] Cannot download video, your account may be banned or your subscription has expired.")
                    return  # break the function

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
