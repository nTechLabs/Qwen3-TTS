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
    
    # Read the corresponding text file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_dir = os.path.join(project_root, "input_txt")
    
    # Get the base filename without extension (keep timestamp)
    wav_basename = os.path.splitext(os.path.basename(wav_file_path))[0]
    txt_file_path = os.path.join(input_dir, f"{wav_basename}.txt")
    
    # Read the text content
    if os.path.exists(txt_file_path):
        with open(txt_file_path, "r", encoding="utf-8") as f:
            text_content = f.read().strip()
        initial_comment = f"🎤 한국어 TTS 음성 파일입니다\n\n텍스트:\n\"{text_content}\""
    else:
        initial_comment = f"🎤 한국어 TTS 음성 파일입니다\n\n파일: {wav_basename}.wav"
    
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
            initial_comment=initial_comment
        )
        
        print("✅ File uploaded successfully!")
        
    except SlackApiError as e:
        print(f"❌ Error uploading file: {e.response['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
