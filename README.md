Execute Command
$ python dl.py -u <username> -p <password> -t ./downloaded -d driver/chromedriver.exe -fi <destination_folder_id> -di <team_drive_id> -miw 90 -maw 120 course.txt

For Colab:
```
# Pre-install
!apt-get update
!apt-get install chromium-chromedriver

# then pass following argument to execute cmd
-e "/usr/lib/chromium-browser/chromium-browser"
```


Troubleshotting:
`from_buffer() cannot return the address of the raw string within a bytes or unicode object`
> $ pip install pyOpenSSL