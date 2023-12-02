from flask import Flask
from flask_socketio import SocketIO, emit
from pydub import AudioSegment
import os
from flask_cors import CORS
from output.test import run
import threading
from queue import Queue
import time

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


AUDIO_DIR = 'recorded_audio'
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# Global variable to store audio data
audio_chunks = Queue()
isRecoding = True


@socketio.on('audio_data')
def handle_audio_data(data):
    global audio_chunks
    audio_chunks.put(data)
    print("Data received:", data)


@app.route('/save-audio', methods=['POST'])
def save_audio():
    global audio_chunks
    global isRecoding
    isRecoding = False

    if not audio_chunks:
        return 'No audio data to save', 400

    # combined_audio = b''.join(audio_chunks) #TODO: make work dor Queue
    #
    # file_path = 'output_audio.webm'
    # with open(file_path, 'wb') as audio_file:
    #     audio_file.write(combined_audio)

    # audio_chunks.clear()

    return 'Audio saved successfully', 200

def aaaaa(a):
    print("starting")
    socketio.run(a)
t1 = threading.Thread(target=run, args=(audio_chunks, isRecoding), daemon=True)
t2 = threading.Thread(target=aaaaa, args=(app,), daemon=True)
t2.start()
time.sleep(1000)
t1.start()
t1.join()
t2.join()
