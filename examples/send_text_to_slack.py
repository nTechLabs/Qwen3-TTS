# coding=utf-8
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set token from .env
slack_token = os.environ.get("SLACK_BOT_TOKEN")
if not slack_token:
    print("Error: SLACK_BOT_TOKEN environment variable not set")
    exit(1)

channel_id = "aibot-test"

text_content = """🎤 *이재명 음성 TTS - 블랙 옥토버 발표문*

안녕하세요, 가상자산 시장의 보이지 않는 흐름을 추적하는 '데이터 웨일즈(Data Whales)' 팀입니다. 저희는 2025년 10월, 비트코인이 사상 최고가에서 단숨에 폭락했던 '블랙 옥토버(Black October)'의 진실에 대해 발표하고자 합니다.

데이터에 따르면 2025년 10월 초, 비트코인은 125,000달러를 돌파하며 환호에 찬 최고점을 찍었습니다. 하지만 기쁨도 잠시, 트럼프 전 대통령의 대중국 100% 관세 발표 한마디에 가상자산 시장에서 단 24시간 만에 190억 달러 규모의 기록적인 청산이 발생하며 시장은 패닉에 빠졌습니다.

저희 팀은 이 폭락 뒤에 숨겨진 기이한 움직임을 포착했습니다. 관세 발표 단 2분 전, 특정 고래가 11억 달러 규모의 대규모 숏 포지션을 구축했고, 이를 통해 수 시간 만에 1억 9,300만 달러의 수익을 올린 정황이 확인되었습니다. 이는 단순한 시장 변동을 넘어 내부자 거래 의혹을 강하게 시사합니다.

흥미로운 점은 개미들이 패닉 셀을 할 때, 블랙록(IBIT)과 같은 기관들은 오히려 저점에서 매집을 이어갔다는 것입니다. 이제 비트코인은 경제 지표뿐 아니라 정치적 발언과 고래의 정보력에 의해 움직이는 지정학적 자산이 되었습니다. 오늘 저희 발표를 통해 변동성 너머의 기회를 포착하는 통찰을 얻으시기 바랍니다. 감사합니다!

📄 *Notion 페이지*: https://www.notion.so/2fea987da1af8130a0b9e42e3ed4202f
📝 *원본 파일*: `input_txt/leejam_speech.txt`

_참고: CPU 환경 제약으로 음성 파일 생성이 지연되고 있습니다. GPU 환경에서 재시도가 필요합니다._
"""

try:
    client = WebClient(token=slack_token)
    
    print(f"Posting message to channel {channel_id}...")
    
    # Post message
    response = client.chat_postMessage(
        channel=channel_id,
        text=text_content,
        mrkdwn=True
    )
    
    print("✅ Message posted successfully!")
    print(f"Timestamp: {response['ts']}")
    
except SlackApiError as e:
    print(f"❌ Error posting message: {e.response['error']}")
    print(f"Details: {e.response}")
