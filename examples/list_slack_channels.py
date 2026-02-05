# coding=utf-8
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set token from .env
slack_token = os.environ.get("SLACK_BOT_TOKEN")
if not slack_token:
    print("Error: SLACK_BOT_TOKEN environment variable not set")
    exit(1)

try:
    client = WebClient(token=slack_token)
    
    print("Fetching channels...")
    
    # List channels
    response = client.conversations_list(types="public_channel,private_channel")
    
    print("\n=== Available Channels ===")
    for channel in response['channels']:
        print(f"Name: #{channel['name']}")
        print(f"ID: {channel['id']}")
        print(f"Type: {'Private' if channel.get('is_private') else 'Public'}")
        print("---")
    
except SlackApiError as e:
    print(f"❌ Error: {e.response['error']}")
    print(f"Details: {e.response}")
