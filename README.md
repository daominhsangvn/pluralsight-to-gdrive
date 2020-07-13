Execute Command
$ python dl.py -u <username> -p <password> -t ./downloaded -d driver/chromedriver.exe -fi <folder_id> -di <team_drive_id> course.txt

Troubleshotting:
`from_buffer() cannot return the address of the raw string within a bytes or unicode object`
> $ pip install pyOpenSSL