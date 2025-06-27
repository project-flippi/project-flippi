import datetime
print(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo)
print(datetime.datetime.now())