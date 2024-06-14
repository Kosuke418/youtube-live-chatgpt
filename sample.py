import time
import requests
import json
import os
import openai
import pyaudio  # wavファイルを再生する
import wave
from concurrent.futures import ProcessPoolExecutor
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

WAVE_OUTPUT_FILENAME = "sample.wav"  # 音声を保存するファイル名
WAVE_RENAME_FILENAME = "sample_rename.wav"


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


def get_chat(chat_id, pageToken, log_file):
    '''
    https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list
    '''
    url = 'https://www.googleapis.com/youtube/v3/liveChat/messages'
    params = {'key': YT_API_KEY, 'liveChatId': chat_id,
              'part': 'id,snippet,authorDetails'}
    if type(pageToken) == str:
        params['pageToken'] = pageToken

    data = requests.get(url, params=params).json()

    try:
        for item in data['items']:
            channelId = item['snippet']['authorChannelId']
            msg = item['snippet']['displayMessage']
            usr = item['authorDetails']['displayName']
            # supChat   = item['snippet']['superChatDetails']
            # supStic   = item['snippet']['superStickerDetails']
            # log_text = '[by {}  https://www.youtube.com/channel/{}]\n  {}'.format(
            #     usr, channelId, msg)
            log_text = '{}'.format(msg)
            with open(log_file, 'a') as f:
                print(log_text, file=f)
                print(log_text)
        print('start : ', data['items'][0]['snippet']['publishedAt'])
        print('end   : ', data['items'][-1]['snippet']['publishedAt'])

    except:
        pass

    return data['nextPageToken']


def make_chat_file(yt_url):
    slp_time = 10  # sec
    iter_times = 90  # 回
    take_time = slp_time / 60 * iter_times
    print('{}分後　終了予定'.format(take_time))
    print('work on {}'.format(yt_url))

    log_file = yt_url.replace('https://www.youtube.com/watch?v=', '') + '.txt'
    with open(log_file, 'a') as f:
        print('{} のチャット欄を記録します。'.format(yt_url), file=f)
    chat_id = get_chat_id(yt_url)

    nextPageToken = None
    for ii in range(iter_times):
        # for jj in [0]:
        try:
            print('\n')
            nextPageToken = get_chat(chat_id, nextPageToken, log_file)
            time.sleep(slp_time)
        except:
            break


def make_audio_file(yt_url):
    while True:
        # 音声ファイルが消される前ならスキップ
        print(241)
        is_file = os.path.isfile(WAVE_OUTPUT_FILENAME)
        if is_file:
            print(534)
            time.sleep(2)
            continue

        print(523)
        log_file = yt_url.replace(
            'https://www.youtube.com/watch?v=', '') + '.txt'
        try:
            with open(log_file) as f:
                chat_list = f.readlines()
        except FileNotFoundError:  # ファイルが存在しなかった場合
            time.sleep(2)
            continue
        messages.append(
            {"role": "user", "content": chat_list[1]})

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
        print(654)
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(voice_data)
        wf.close()
        print(75)
        # 読み込んだチャットを削除
        with open(log_file, "w") as f:
            f.write("".join(chat_list[1:]))


def play_audio_file():
    while True:
        is_file = os.path.isfile(WAVE_OUTPUT_FILENAME)
        is_rename_file = os.path.isfile(WAVE_RENAME_FILENAME)
        print(9087)
        if is_file and not is_rename_file:
            os.rename(WAVE_OUTPUT_FILENAME, WAVE_RENAME_FILENAME)
            print(222)
        else:
            time.sleep(5)
            continue
        print(os.path.isfile(WAVE_RENAME_FILENAME))
        try:
            wf = wave.open(WAVE_RENAME_FILENAME, "r")
        except FileNotFoundError:  # ファイルが存在しなかった場合
            time.sleep(5)
            continue
        print(42)

        # PyAudioのインスタンスを生成
        p = pyaudio.PyAudio()

        # ストリームを開く
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
        chunk = 1024
        data = wf.readframes(chunk)

        while len(data) > 0:
            stream.write(data)
            data = wf.readframes(chunk)

        # ストリームを閉じる
        stream.stop_stream()
        stream.close()

        # PyAudio のインスタンスを終了する
        p.terminate()
        wf.close()

        os.remove(WAVE_RENAME_FILENAME)


if __name__ == '__main__':
    # yt_url = input('Input YouTube URL > ')
    yt_url = "RxPWj-NEbPs"
    with ProcessPoolExecutor(max_workers=3) as executor:
        # executor.submit(make_chat_file, yt_url)
        executor.submit(make_audio_file, yt_url)
        executor.submit(play_audio_file)
