import sys, os, argparse
from pluralsight_colab import PluralSightColab
import pickle
import os.path
from os import chdir, listdir, stat

def main():
    parser = argparse.ArgumentParser(
        description='A cross-platform python based utility to download courses from PluralSight for personal offline use.', conflict_handler="resolve")
    parser.add_argument(
        'username', help="Pluralsight username", type=str)
    parser.add_argument(
        'password', help="Pluralsight password", type=str)
    parser.add_argument(
        'course', help="Course file path", type=str)
    parser.add_argument(
        'target_folder', help="Output folder", type=str)

    other = parser.add_argument_group("Others")
    other.add_argument(
        '-miw', '--min-wait',
        dest='min_wait',
        default=60,
        type=int,
        help="Min wait between download (Seconds)", metavar='')
    other.add_argument(
        '-maw', '--max-wait',
        dest='max_wait',
        default=120,
        type=int,
        help="Max wait between download (Seconds)", metavar='')
    other.add_argument(
        '-e', '--executable-path',
        dest='executablePath',
        default=None,
        type=int,
        help="Executable Path", metavar='')

    options = parser.parse_args()

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

    print("[+] Found " + str(len(course_urls)) + " COURSES")
    dl = PluralSightColab(options, downloaded_history_file_path)

    login_success = dl.login()

    if login_success:
        for co in course_urls:
            dl.download_course_by_url(co, options.target_folder)

    print("")
    print("[+] DONE !")
    print("")

if __name__ == "__main__":
    main()
