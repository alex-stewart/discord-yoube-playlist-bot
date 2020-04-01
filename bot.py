import os
import re
from urllib.parse import urlparse, parse_qs

import discord
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

youtube_playlist_id = os.environ['YOUTUBE_PLAYLIST']
bot_token = os.environ['DISCORD_TOKEN']
discord_channel = int(os.environ['DISCORD_CHANNEL'])
discordClient = discord.Client()

scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

api_service_name = "youtube"
api_version = "v3"
client_secrets_file = "secret.json"

# Get credentials and create an API client
flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
credentials = flow.run_console()
youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)


def playlist_contains_video(playlist_id, video_id):
    page_token = None
    first_page = True
    while page_token is not None or first_page:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=playlist_id,
            pageToken=page_token
        )
        response = request.execute()

        for playlist_item in response.get('items'):
            if playlist_item.get('contentDetails').get('videoId') == video_id:
                return True

        response = request.execute()
        page_token = response.get('nextPageToken')
        first_page = False

    return False


def add_video_to_playlist(playlist_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "position": 0,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    response = request.execute()
    print(response)


def add_videos_to_playlist(video_ids):
    for video_id in video_ids:
        if video_id is not None:
            if not playlist_contains_video(youtube_playlist_id, video_id):
                add_video_to_playlist(youtube_playlist_id, video_id)


def video_ids_in_message(message):
    video_ids = set()
    matches = re.findall(
        '(http:|https:)?(//)?(www\.)?(youtube.com|youtu.be)/(watch|embed)?(\?v=|/)?([^"&?\/\s]{11})?',
        message.content)
    for match in matches:
        video_ids.add(match[6])
    return video_ids


@discordClient.event
async def on_ready():
    print('Logged into Discord as {0.user}'.format(discordClient))
    channel = discordClient.get_channel(discord_channel)
    messages = await channel.history(limit=200).flatten()
    video_ids = set()
    for message in messages:
        video_ids = video_ids.union(video_ids_in_message(message))

    add_videos_to_playlist(video_ids)


@discordClient.event
async def on_message(message):
    if message.channel.id == discord_channel:
        video_ids = video_ids_in_message(message)
        add_videos_to_playlist(video_ids)


discordClient.run(bot_token)
