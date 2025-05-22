#!/usr/bin/python

import argparse
import http.client
import httplib2
import os
import random
import time
import config
import schedule
import google.oauth2.credentials
import google_auth_oauthlib.flow
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from glob import glob
from ProcessComboTextFile import parse_videodata
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlencode
from datetime import datetime


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
  http.client.IncompleteRead, http.client.ImproperConnectionState,
  http.client.CannotSendRequest, http.client.CannotSendHeader,
  http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = config.CLIENT_SECRETS_FILE
CREDENTIALS_FILE = config.CREDENTIALS_FILE


# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

VALID_PRIVACY_STATUSES = ('public', 'private', 'unlisted')

def YoutubeArgs():
  parser = argparse.ArgumentParser(add_help=True)
  parser.add_argument("--file", help='Video file to upload')
  parser.add_argument("--title", help='Video title', default='Test Title')
  parser.add_argument("--description", help='Video description',
    default='Test Description')
  parser.add_argument("--category", default='20',
    help='Numeric video category. ' +
      'See https://developers.google.com/youtube/v3/docs/videoCategories/list')
  parser.add_argument("--keywords", help='Video keywords, comma separated',
    default='')
  parser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
    default='public', help='Video privacy status.')
  args = parser.parse_args()
  return args


# Authorize the request and store authorization credentials.
def get_authenticated_service():
    creds = None

    # Check if credentials file exists and load if valid
    if os.path.exists(CREDENTIALS_FILE):
        if os.stat(CREDENTIALS_FILE).st_size == 0:
            print("Credentials file is empty.")
        else:
            try:
                print("Loading credentials from file...")
                with open(CREDENTIALS_FILE, 'r') as token:
                    creds_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
            except json.decoder.JSONDecodeError as e:
                print("Error decoding credentials file. Treating as no credentials available:", e)
                creds = None

    # If credentials are not available or invalid, handle refresh or re-auth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
                print("Credentials refreshed successfully.")
            except Exception as e:
                print("Failed to refresh credentials:", e)
                creds = None
                try:
                    os.remove(CREDENTIALS_FILE)
                    print("Corrupted credentials file removed.")
                except Exception as cleanup_err:
                    print("Failed to remove corrupted credentials file:", cleanup_err)

        # If still no valid creds, force re-authentication
        if not creds or not creds.valid:
            print("No valid credentials found. Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                SCOPES
            )
            # Ensure refresh_token is issued
            creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
            print("OAuth flow complete. Credentials obtained.")

            # Save credentials
            with open(CREDENTIALS_FILE, 'w') as token:
                token.write(creds.to_json())
                print("Credentials saved to file.")

    # Debug info
    print("Token expired:", creds.expired)
    print("Refresh token present:", creds.refresh_token is not None)

    print("Authenticated service is ready.")
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)



def initialize_upload(youtube, options):
  tags = None
  if options.keywords:
    tags = options.keywords.split(',')

  body=dict(
    snippet=dict(
      title=options.title,
      description=options.description,
      tags=tags,
      categoryId=options.category
    ),
    status=dict(
      privacyStatus=options.privacyStatus
    )
  )

  # Call the API's videos.insert method to create and upload the video.
  insert_request = youtube.videos().insert(
    part=','.join(body.keys()),
    body=body,
    # The chunksize parameter specifies the size of each chunk of data, in
    # bytes, that will be uploaded at a time. Set a higher value for
    # reliable connections as fewer chunks lead to faster uploads. Set a lower
    # value for better recovery on less reliable connections.
    #
    # Setting 'chunksize' equal to -1 in the code below means that the entire
    # file will be uploaded in a single HTTP request. (If the upload fails,
    # it will still be retried where it left off.) This is usually a best
    # practice, but if you're using Python older than 2.6 or if you're
    # running on App Engine, you should set the chunksize to something like
    # 1024 * 1024 (1 megabyte).
    media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
  )

  return resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(request):
  response = None
  error = None
  retry = 0
  while response is None:
    try:
      print('Uploading file...')
      status, response = request.next_chunk()
      if response is not None:
        if 'id' in response:
          print('Video id "%s" was successfully uploaded.' % response['id'])
          return response['id']
        else:
          exit('The upload failed with an unexpected response: %s' % response)
    except(HttpError) as e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = 'A retriable HTTP error %d occurred:\n%s' % (e.resp.status,
                                                             e.content)
      else:
        raise
    except(RETRIABLE_EXCEPTIONS) as e:
      error = 'A retriable error occurred: %s' % e

    if error is not None:
      print(error)
      retry += 1
      if retry > MAX_RETRIES:
        exit('No longer attempting to retry.')

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      print ('Sleeping %f seconds and then retrying...' % sleep_seconds)
      time.sleep(sleep_seconds)

def scheduled_upload_video(youtube, videodata_file_path, posted_vid_list, args):
  with open (posted_vid_list) as f:
    posted_vids = [line.rstrip('\n') for line in f]

  print("Posted vid list retrieved")
  videodata_list = parse_videodata(videodata_file_path)
  print("Video data list retrieved")

  video_uploaded = False # Flag to track if a video was uploaded

  try:
    for vid in videodata_list:
      if vid['File Path'] in posted_vids or vid['File Path'] == None or vid['Title'] == None or vid['Descripition'] == None:
        continue # Skip already posted or incomplete videos

      if not os.path.exists(vid['File Path']):
        print(f"Skipping {vid['File Path']} - file does not exist.")
        continue

      print("Unposted video found, proceeding to post")
      
      args.file = vid['File Path']
      args.title = vid['Title']
      args.description = vid['Descripition'] + '\n' + config.YOUTUBE_HASHTAGS 
      args.keywords = config.YOUTUBE_TAGS

      print("Arguements for upload retrieved")

      try:
        # Upload and retrieve video ID
        video_id = initialize_upload(youtube, args)
        vid["VideoId"] = video_id

        # Set ThumbnailSet to False if a valid thumbnail exists
        if "Thumbnail" in vid and os.path.exists(vid["Thumbnail"]):
          vid["ThumbnailSet"] = False

        # Save updated video metadata to file
        with open(videodata_file_path, "w", encoding="utf-8") as f:
          json.dump(videodata_list, f, indent=4)


      except (HttpError) as e:
        print('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))
        print(vid+' failed to upload')
        break

      

      if vid['File Path'] not in posted_vids:
        #After posting video, add video to list to avoid posting same video twice
        with open(posted_vid_list, "a") as f:
          f.write(vid['File Path'] + "\n")
        print(vid['File Path'] + ' successfully uploaded')
      
      video_uploaded = True
      break

    # If no videos were uploaded, print a message
    if not video_uploaded:
      print("All available videos have been posted.") 

    return video_uploaded
      
  except Exception as e:
    if "invalid_grant" in str(e):
      raise
    print (str(e))

def set_thumbnails(youtube, videodata_path):
    
    with open(videodata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = False

    for vid in data:
        if not vid.get("Thumbnail") or not os.path.exists(vid["Thumbnail"]):
            continue
        if vid.get("ThumbnailSet") == True:
            continue
        if "VideoId" not in vid:
            print(f"Skipping {vid['File Path']}: No video ID found.")
            continue

        try:
            request = youtube.thumbnails().set(
                videoId=vid["VideoId"],
                media_body=vid["Thumbnail"]
            )
            response = request.execute()
            print(f"Thumbnail set for video {vid['VideoId']}")
            vid["ThumbnailSet"] = True
            updated = True
        except Exception as e:
            print(f"Failed to set thumbnail for {vid['File Path']}: {e}")

    if updated:
        with open(videodata_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
 
