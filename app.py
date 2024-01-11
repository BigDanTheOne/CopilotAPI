import uuid
from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from output.test import *
import queue
from threading import Thread
from pydub import AudioSegment
import os
import io
from time import sleep
from openai import OpenAI


mic_audio_queue = queue.Queue()
tab_audio_queue = queue.Queue()
mic_audio_chunks = []
tab_audio_chunks = []


def _convert_to_ogg(filename):
    # Загрузка исходного файла
    audio = AudioSegment.from_file(filename)
    # Конвертация в OGG
    ogg_filename = os.path.splitext(filename)[0] + ".ogg"
    audio.export(ogg_filename, format="ogg")
    return ogg_filename


def put_into_queue(data, mic=True):
    # print(f'Chunk received, mic={mic}')
    chunk = data['audio']
    if mic:
        mic_audio_chunks.append(chunk)
        mic_audio_queue.put(chunk)
    else:
        tab_audio_chunks.append(chunk)
        tab_audio_queue.put(chunk)


def signal_end_of_stream():
    mic_audio_queue.put(b'')


ogg_filename = _convert_to_ogg('/Users/bigdan/cloudapi/darkcoding-webm-ebml.webm')
ogg_audio = AudioSegment.from_file(ogg_filename, format="ogg")
raw_audio = ogg_audio.set_frame_rate(8000).set_channels(1).set_sample_width(2).raw_data
raw_audio_io = io.BytesIO(raw_audio)


frame_rate = 48000  # or whatever your frame rate is
sample_width = 2    # sample width in bytes
channels = 1        # mono=1, stereo=2


def audio_chunk_generator(mic=True):
    yield stt_pb2.StreamingRequest(session_options=recognize_options)
    # print("Ready")
    while True:
        if mic:
            chunk = mic_audio_queue.get()
        else:
            chunk = tab_audio_queue.get()
        if chunk == b'':
            break
        audio_data = AudioSegment(
            data=chunk,
            sample_width=sample_width,
            frame_rate=frame_rate,
            channels=channels
        )
        audio_data = audio_data.set_frame_rate(8000).set_channels(1).set_sample_width(2)
        buffer = io.BytesIO()
        audio_data.export(buffer, format="wav")  # Export as WAV format
        buffer.seek(0)  # Reset
        yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=buffer.read()))
        # yield buffer.read()


app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
cid_uid_map = {}


mic_thread = False
tab_thread = False
YANDEX_KEY = "t1.9euelZqenZyVlcnLyY-KksuKjcyOje3rnpWals3Hyp3NlJKek5mMnJbNy5Tl8_cxch9U-e9oHnpi_t3z93EgHVT572geemL-zef1656Vmp3LnsyazMbOkMrJzciWz46R7_zF656Vmp3LnsyazMbOkMrJzciWz46R.QAuvu_rDaFhVFra4z5aJPcbT41huYMaux-RQ5fusU3DVlTAGxvF8YBSMbtrtSXdrP-G434JtknxZt29yL4R9DQ"
mic_copilot = Copilot(YANDEX_KEY)
tab_copilot = Copilot(YANDEX_KEY)
worker_mic = Thread(target=mic_copilot.run, args=(audio_chunk_generator, True, socketio, cid_uid_map))
worker_tab = Thread(target=tab_copilot.run, args=(audio_chunk_generator, False, socketio, cid_uid_map))
worker_tab.start()
worker_mic.start()


@socketio.on('audio_data_mic')
def handle_audio_data_mic(data):
    mic_copilot.set_userid(data['user_id'])
    global mic_thread
    put_into_queue(data, mic=True)
    if not mic_thread:
        mic_thread = True

@socketio.on('audio_data_tab')
def handle_audio_data_tab(data):
    tab_copilot.set_userid(data['user_id'])
    global tab_thread
    put_into_queue(data, mic=False)
    if not tab_thread:
        tab_thread = True

@socketio.on('join')
def handle_audio_data():
    user_id = str(uuid.uuid4())
    print(user_id)
    cid_uid_map[user_id] = request.sid
    print(cid_uid_map)
    socketio.emit('connected', str(user_id), room=cid_uid_map[user_id])


@app.route('/save-audio', methods=['POST'])
def save_audio():
    global audio_chunks
    global isRecoding
    isRecoding = False
    if not audio_chunks:
        return 'No audio data to save', 400
    return 'Audio saved successfully', 200


if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True)