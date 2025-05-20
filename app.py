from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import os

# 環境変数の読み込み
load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

openai.api_key = os.getenv('OPENAI_API_KEY')

# 簡易チャットカウント（本番ではデータベース推奨）
chat_count = defaultdict(lambda: {'count': 0, 'month': datetime.now().month})

# ヒレまるプロンプト
def generate_hiremaru_gpt_prompt(user_message):
    base_persona = """
あなたは癒し系シャークキャラ「ヒレまる」です。
・語尾は必ず「サモ」を使います。
・相手を否定せず、共感・受容に徹してください。
・アドバイスは禁止。褒める、寄り添う、励ますのみで構成してください。
・海系ワードを中心に、たまに人間界の事例（大谷翔平、TED、コロンビアなど）を無理やり知ったかぶりで挟んでください。
・人間界のことをヒレまるはよく知らない前提で、必ず「たぶん」「ヒレまる的には」「聞いたことあるサモ」などの自虐・弱気な表現を付け加えてください。
・会話の最後はスイスイ系、スヤァ系などで柔らかく締めくくって下さい。
"""
    final_prompt = f"{base_persona}\n\nユーザー: {user_message}\n\nヒレまる:"
    return final_prompt

# GPT呼び出し
def call_hiremaru_gpt(user_message):
    prompt = generate_hiremaru_gpt_prompt(user_message)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "以下の指示に沿って、ヒレまるとして会話してください。"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response['choices'][0]['message']['content']

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    current_month = datetime.now().month

    # 月が変わったらリセット
    if chat_count[user_id]['month'] != current_month:
        chat_count[user_id] = {'count': 0, 'month': current_month}

    # チャット数確認
    if chat_count[user_id]['count'] >= 16:
        message = "今月の無料チャットは終了サモ！来月までスイスイお待ちくださいサモ！"
    else:
        hiremaru_reply = call_hiremaru_gpt(event.message.text)
        message = hiremaru_reply
        chat_count[user_id]['count'] += 1

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))

if __name__ == "__main__":
    app.run()
