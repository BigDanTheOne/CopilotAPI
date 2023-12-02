import pyaudio
import wave
import argparse
import grpc
from .yandex.cloud.ai.stt.v3 import stt_pb2 as stt_pb2
from .yandex.cloud.ai.stt.v3 import stt_service_pb2_grpc as stt_service_pb2_grpc
# import yandex.cloud.ai.stt.v3. as stt_pb2
# import . as stt_service_pb2_grpc
from pyAudioAnalysis import audioSegmentation as aS
import queue
from copy import copy
import threading


# Настройки потокового распознавания.
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 4096
RECORD_SECONDS = 30
WAVE_OUTPUT_FILENAME = "../audio.wav"
frames = []

audio = pyaudio.PyAudio()

recognition_queue = queue.Queue()
labeling_queue = queue.Queue()

waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
waveFile.setnchannels(CHANNELS)
waveFile.setsampwidth(audio.get_sample_size(FORMAT))
waveFile.setframerate(RATE)

def gen(audio_chunks, isRecoding):
   recognize_options = stt_pb2.StreamingOptions(
      recognition_model=stt_pb2.RecognitionModelOptions(
         audio_format=stt_pb2.AudioFormatOptions(
            raw_audio=stt_pb2.RawAudio(
               audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
               sample_rate_hertz=8000,
               audio_channel_count=1
            )
         ),
         text_normalization=stt_pb2.TextNormalizationOptions(
            text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
            profanity_filter=True,
            literature_text=False
         ),
         language_restriction=stt_pb2.LanguageRestrictionOptions(
            restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
            language_code=['ru-RU']
         ),
         audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME,

      ),
   )


   yield stt_pb2.StreamingRequest(session_options=recognize_options)

   # stream = audio.open(format=FORMAT, channels=CHANNELS,
   #             rate=RATE, input=True,
   #             frames_per_buffer=CHUNK)
   print("recording")

   while isRecoding:
      if len(audio_chunks):
         data = audio_chunks.get()
         print("Recognizing data: ", data)
         yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))
         frames.append(data)
   print("finished")

   # stream.stop_stream()
   # stream.close()
   audio.terminate()


   waveFile.close()

def run(audio_chunks, isRecoding, secret = "t1.9euelZqJzpiUl5ySx4ycyJWJkYvHje3rnpWals3Hyp3NlJKek5mMnJbNy5Tl8_dFbVJU-e9HXnAX_t3z9wUcUFT570decBf-zef1656VmovPysyVxsyXjJqSz8uPkc6W7_zF656VmovPysyVxsyXjJqSz8uPkc6W.QaoBEHMwHmfjz44jxTbbUXYfV_gBjtroPKQP3JQZaWDee8oaOTW47V63ZdF9QetGb3sbe9brNi_LRvLJYNSoBQ"):
   cred = grpc.ssl_channel_credentials()
   channel = grpc.secure_channel('stt.api.cloud.yandex.net:443', cred)
   stub = stt_service_pb2_grpc.RecognizerStub(channel)
   it = stub.RecognizeStreaming(gen(audio_chunks, isRecoding), metadata=(
      ('authorization', f'Bearer {secret}'),
      ('x-folder-id', 'b1gdp45prmdkt1e1gjso'),
   ))

   try:
      for r in it:
         event_type, alternatives = r.WhichOneof('Event'), None
         if event_type == 'partial' and len(r. partial.alternatives) > 0:
            alternatives = [a.text for a in r.partial.alternatives]
         if event_type == 'final':
            alternatives = [a.text for a in r.final.alternatives]
         if event_type == 'final_refinement':
            alternatives = [a.text for a in r.final_refinement.normalized_text.alternatives]
            waveFile.writeframes(b''.join(frames))
         print(f'type={event_type}, alternatives={alternatives}')
   except grpc._channel._Rendezvous as err:
      print(f'Error code {err._state.code}, message: {err._state.details}')
      raise err

if __name__ == '__main__':
   run()
