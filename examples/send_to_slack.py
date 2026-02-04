# coding=utf-8
import os
import sys
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def main():
    # Get file path and channel ID from command line
    if len(sys.argv) < 3:
        print("Usage: python send_to_slack.py <wav_file_path> <channel_id>")
        sys.exit(1)
    
    wav_file_path = sys.argv[1]
    channel_id = sys.argv[2]
    
    # Check if file exists
    if not os.path.exists(wav_file_path):
        print(f"Error: File not found: {wav_file_path}")
        sys.exit(1)
    
    # Get Slack token from environment
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        print("Error: SLACK_BOT_TOKEN environment variable not set")
        sys.exit(1)
    
    try:
        client = WebClient(token=slack_token)
        
        print(f"Uploading {wav_file_path} to channel {channel_id}...")
        
        # Upload file
        response = client.files_upload_v2(
            channel=channel_id,
            file=wav_file_path,
            title=os.path.basename(wav_file_path),
            initial_comment="🎤 한국어 TTS 음성 파일입니다\n\n텍스트:\n\"나는 내가 빛나는 별인 줄 알았어요\n한 번도 의심한 적 없었죠\n몰랐어요, 난 내가 벌레라는 것을\n그래도 괜찮아, 난 눈부시니까\""
        )
        
        print("✅ File uploaded successfully!")
        
    except SlackApiError as e:
        print(f"❌ Error uploading file: {e.response['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
