# top_shorts.py
import os
import datetime
import isodate
from googleapiclient.discovery import build

import yt_dlp


# Replace with your own values or import from your config module
YOUTUBE_API_KEY = 'AIzaSyBnomFda1JY0e-XSwqC78ZDtk0pHubpo_s'
CHANNEL_ID = 'UC5L50fy_SW5By2lOeJbZ9cQ'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# Define the time period (e.g., last 7 days)
def get_time_range(days=15):
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days)
    return start_date.isoformat("T") + "Z", end_date.isoformat("T") + "Z"

def get_channel_videos(channel_id, published_after, published_before):
    video_ids = []
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)
    nextPageToken = None
    while True:
        search_response = youtube.search().list(
            channelId=channel_id,
            part="id",
            order="date",
            type="video",
            publishedAfter=published_after,
            publishedBefore=published_before,
            maxResults=50,
            pageToken=nextPageToken
        ).execute()
        for item in search_response.get("items", []):
            video_ids.append(item["id"]["videoId"])
        nextPageToken = search_response.get("nextPageToken")
        if not nextPageToken:
            break
    return video_ids

def get_video_details(video_ids):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)
    details = []
    for i in range(0, len(video_ids), 50):
        response = youtube.videos().list(
            id=",".join(video_ids[i:i+50]),
            part="snippet,contentDetails,statistics"
        ).execute()
        details.extend(response.get("items", []))
    return details

def is_short_video(duration_str):
    duration = isodate.parse_duration(duration_str)
    return duration.total_seconds() < 60

def download_video(video_url, output_dir):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'merge_output_format': 'mp4',  # Merge the streams into an MP4 file
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        # Remove any postprocessors that extract audio.
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

def download_top_shorts(output_dir, num_top=5, days=15):
    published_after, published_before = get_time_range(days)
    video_ids = get_channel_videos(CHANNEL_ID, published_after, published_before)
    videos = get_video_details(video_ids)
    # Filter for shorts
    short_videos = [video for video in videos if is_short_video(video["contentDetails"]["duration"])]
    # Convert view counts to integers and sort
    for video in short_videos:
        video["viewCount"] = int(video["statistics"].get("viewCount", 0))
    short_videos_sorted = sorted(short_videos, key=lambda v: v["viewCount"], reverse=False)
    top_shorts = short_videos_sorted[:num_top]
    
    print("Top 5 performing shorts:")
    for idx, video in enumerate(top_shorts, start=1):
        title = video["snippet"]["title"]
        views = video["viewCount"]
        video_id = video["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"{idx}. {title} - {views} views ({video_url})")
        download_video(video_url, output_dir)



def get_downloaded_shorts(download_folder="C:/Users/15613/Videos/TopShorts"):
    """
    Returns a list of downloaded shorts (video file paths) from the specified folder.
    The list is sorted by modification time in ascending order (oldest first).
    """
    # List all .mp4 files in the download folder
    file_paths = [os.path.join(download_folder, f) 
                  for f in os.listdir(download_folder) 
                  if f.lower().endswith(".mp4")]
    
    # Sort by modification time (oldest first) so that the least-viewed (downloaded earlier) come first.
    file_paths.sort(key=lambda path: os.path.getmtime(path))
    
    return file_paths