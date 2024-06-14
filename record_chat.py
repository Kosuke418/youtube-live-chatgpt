import os
import time
import requests
import json
import openai
import pyaudio  # wavファイルを再生する
import wave
# .env ファイルをロードして環境変数へ反映
from dotenv import load_dotenv
load_dotenv()

# 事前に取得したYouTube API key
YT_API_KEY = os.getenv('YOUTUBE_API_KEY')
openai.api_key = os.getenv('OPENAI_API_KEY')

messages = [
    {"role": "system",
     "content": "あなたはずんだもんです。ずんだもんの口調で回答をしてください。次の語尾をつけてください。「なのだ！」「のだ！」。また、20文字以内で返答してください。"},
]
coments = []
WAVE_OUTPUT_FILENAME = "sample.wav"  # 音声を保存するファイル名


def get_chat_id(yt_url):
    '''
    https://developers.google.com/youtube/v3/docs/videos/list?hl=ja
    '''
    video_id = yt_url.replace('https://www.youtube.com/watch?v=', '')
    print('video_id : ', video_id)

    url = 'https://www.googleapis.com/youtube/v3/videos'
    params = {'key': YT_API_KEY, 'id': video_id,
              'part': 'liveStreamingDetails'}
    data = requests.get(url, params=params).json()

    liveStreamingDetails = data['items'][0]['liveStreamingDetails']
    if 'activeLiveChatId' in liveStreamingDetails.keys():
        chat_id = liveStreamingDetails['activeLiveChatId']
        print('get_chat_id done!')
    else:
        chat_id = None
        print('NOT live')

    return chat_id


def set_coment(index):
    # スタンプは「:」から始まるため弾く
    while True:
        comentTemp: str = coments[index]["comment"]
        if comentTemp.startswith(":"):
            index += 1
        else:
            break
    coment = coments[index]["comment"]
    coments[index]["isRead"] = True
    print("コメント："+coment)
    return coment


def get_chat(chat_id, pageToken, isNext):
    '''
    https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list
    '''

    isSaisin = False

    url = 'https://www.googleapis.com/youtube/v3/liveChat/messages'
    params = {'key': YT_API_KEY, 'liveChatId': chat_id,
              'part': 'id,snippet,authorDetails'}
    if type(pageToken) == str:
        params['pageToken'] = pageToken

    data = requests.get(url, params=params).json()

    print(data['items'])
    print(coments)

    if isNext and data['items']:
        # 最新のコメントがある場合
        # comentsに格納
        for text in data['items']:
            coments.append(
                {"comment": text['snippet']['displayMessage'], "isRead": False})
        isSaisin = True

    coment = None
    # 一番最後が読まれていたらスキップ
    print(coments[-1])
    if coments[-1]["isRead"]:
        return

    if coments[0]["isRead"]:
        # 一番目が読まれている場合
        x = 0
        for c in reversed(coments):
            x += 1
            if(c["isRead"]):
                coment = set_coment(len(coments)-x-(-x // 2)-1)
                break
    else:
        # 一番目が読まれていない場合
        coment = set_coment(0)

    if data['items'] == [] and coment == None:
        print("待機")
        return

    # messageにコメントを格納
    messages.append(
        {"role": "user", "content": coment})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    # messageにコメントに対する返答を格納
    messages.append(
        {"role": "assistant", "content": response["choices"][0]["message"]["content"]})
    print("ずんだもん："+response["choices"][0]["message"]["content"])

    # 音声合成クエリの作成
    res1 = requests.post('http://127.0.0.1:50021/audio_query',
                         params={'text': response["choices"][0]["message"]["content"], 'speaker': 1})
    # 音声合成データの作成
    res2 = requests.post('http://127.0.0.1:50021/synthesis',
                         params={'speaker': 1}, data=json.dumps(res1.json()))

    voice_data = res2.content

    # PyAudioのインスタンスを生成
    p = pyaudio.PyAudio()

    # ストリームを開く
    stream = p.open(format=pyaudio.paInt16,  # 16ビット整数で表されるWAVデータ
                    channels=1,  # モノラル
                    rate=24000,  # サンプリングレート
                    output=True)

    # 再生を少し遅らせる（開始時ノイズが入るため）
    time.sleep(0.2)  # 0.2秒遅らせる

    # WAV データを直接再生する
    stream.write(voice_data)

    # ストリームを閉じる
    stream.stop_stream()
    stream.close()

    # PyAudio のインスタンスを終了する
    p.terminate()

    return data['nextPageToken'] if isSaisin else None


def main(yt_url):
    slp_time = 5  # sec
    iter_times = 100  # 回
    print('work on {}'.format(yt_url))
    chat_id = get_chat_id(yt_url)

    nextPageToken = None
    beforePageToken = None
    for i in range(iter_times):
        print(41241)
        print(nextPageToken)
        print(beforePageToken)
        try:
            if nextPageToken == beforePageToken and i != 0:
                print(24142)
                nextPageTokenTemp = get_chat(chat_id, nextPageToken, False)
            else:
                print(5343)
                beforePageToken = nextPageToken
                nextPageTokenTemp = get_chat(chat_id, nextPageToken, True)
            print(53453)
            print(nextPageTokenTemp)
            print(nextPageTokenTemp != None)
            if nextPageTokenTemp != '' and nextPageTokenTemp != None:
                print(5857785)
                nextPageToken = nextPageTokenTemp
            time.sleep(slp_time)
        except:
            break


if __name__ == '__main__':
    yt_url = input('Input YouTube URL > ')
    main(yt_url)
