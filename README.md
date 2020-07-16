Execute Command
$ python dl.py -u <username> -p <password> -t ./downloaded -d driver/chromedriver.exe -fi <destination_folder_id> -di <team_drive_id> -miw 90 -maw 120 course.txt

Troubleshotting:
`from_buffer() cannot return the address of the raw string within a bytes or unicode object`
> $ pip install pyOpenSSL