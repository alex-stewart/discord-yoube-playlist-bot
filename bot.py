import os
import re
from argparse import ArgumentParser

import discord
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# Parse arguments
parser = ArgumentParser(description='Add videos from discord channel to youtube playlist.')
parser.add_argument('bot_token', type=str, help='discord bot token')
parser.add_argument('discord_channel', type=str, help='a discord channel id')
args = parser.parse_args()

bot_token = args.bot_token
discord_channel = int(args.discord_channel)

discordClient = discord.Client()

# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Get credentials and create a YoutTube API client
flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file("secret.json", [
    "https://www.googleapis.com/auth/youtube.force-ssl"])
credentials = flow.run_console()
youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)


def new_playlist(playlist_name):
    print('creating playlist ' + playlist_name)
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
          "snippet": {
            "title": playlist_name,
            "defaultLanguage": "en"
          },
          "status": {
            "privacyStatus": "public"
          }
        }
    )
    playlist = request.execute()
    print(playlist)
    return playlist.get('id')


def get_videos_in_playlist(pl_id):
    page_token = None
    first_page = True
    videos = []
    while page_token is not None or first_page:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=pl_id,
            pageToken=page_token
        )
        response = request.execute()

        for playlist_item in response.get('items'):
            videos.append(playlist_item.get('contentDetails').get('videoId'))

        page_token = response.get('nextPageToken')
        first_page = False
    return videos


def get_videos_in_all_playlists():
    page_token = None
    first_page = True
    playlists = {}
    while page_token is not None or first_page:
        request = youtube.playlists().list(
            part="snippet,contentDetails",
            maxResults=50,
            pageToken=page_token,
            mine=True
        )
        response = request.execute()

        for playlist in response.get('items'):
            pl_id = playlist.get('id')
            playlists[pl_id] = get_videos_in_playlist(pl_id)

        page_token = response.get('nextPageToken')
        first_page = False
    return playlists


def add_video_to_playlist(pl_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": pl_id,
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
            if video_id not in all_videos:
                add_video_to_playlist(active_playlist_id, video_id)
                all_videos.append(video_id)


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


# Fetch all playlists and videos from youtube
playlist_content = get_videos_in_all_playlists()

all_videos = []
active_playlist_id = None
for playlist_id, playlist_videos in playlist_content.items():
    all_videos.extend(playlist_videos)
    if len(playlist_videos) < 5000:
        x = 1

if active_playlist_id is None:
    active_playlist_id = new_playlist('Axon Jukebox ' + str(len(playlist_content) + 1))

discordClient.run(bot_token)
