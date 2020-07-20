Execute Command
$ python dl.py -u <username> -p <password> -t ./downloaded -d driver/chromedriver.exe -fi <destination_folder_id> -di <team_drive_id> -miw 90 -maw 120 course.txt

For Colab:
- Must use `cookies`
- Must use `proxy` to generate cookies and for download
- Must provide `ua` same as the place where cookies generated
```
$ python dl_colab.py ./course.txt ./downloaded -c ./cookies.txt -pr "" -ua ""
```

Troubleshotting:
`from_buffer() cannot return the address of the raw string within a bytes or unicode object`
> $ pip install pyOpenSSL

> pip install urllib3<1.25