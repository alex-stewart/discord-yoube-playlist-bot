import os
import re
from argparse import ArgumentParser

import discord
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# Parse arguments
parser = ArgumentParser(description='Add videos from discord channel to youtube playlist.')
parser.add_argument('youtube_playlist_id', type=str, help='youtube playlist id')
parser.add_argument('bot_token', type=str, help='discord bot token')
parser.add_argument('discord_channel', type=str, help='a discord channel id')
args = parser.parse_args()

youtube_playlist_id = args.youtube_playlist_id
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


def get_videos_in_all_playlists():
    page_token = None
    first_page = True
    videos = []
    while page_token is not None or first_page:
        request = youtube.playlists().list(
            part="snippet,contentDetails",
            maxResults=50,
            pageToken=page_token,
            mine=True
        )
        response = request.execute()

        for playlist in response.get('items'):
            playlist_id = playlist.get('id')
            videos.append(get_videos_in_playlist(playlist_id))

        page_token = response.get('nextPageToken')
        first_page = False
    return videos


def get_videos_in_playlist(playlist_id):
    page_token = None
    first_page = True
    videos = []
    while page_token is not None or first_page:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=playlist_id,
            pageToken=page_token
        )
        response = request.execute()

        for playlist_item in response.get('items'):
            videos.append(playlist_item.get('contentDetails').get('videoId'))

        page_token = response.get('nextPageToken')
        first_page = False
    return videos


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
            if video_id not in playlist_content:
                playlist_content.append(video_id)
                add_video_to_playlist(youtube_playlist_id, video_id)
                playlist_content.append(video_id)


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


playlist_content = get_videos_in_all_playlists()
discordClient.run(bot_token)
