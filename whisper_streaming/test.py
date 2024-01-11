import io
import queue
from .whisper_online import *
import numpy as np
import soundfile as sf
src_lan = "en"  # source language
tgt_lan = "en"  # target language  -- same as source for ASR, "en" if translate task is used

# set options:
# asr.set_translate_task()  # it will translate from lan into English
# asr.use_vad()  # set using VAD
audio_path = "/Users/bigdan/cloudapi/darkcoding-webm-ebml.webm"


asr = FasterWhisperASR(src_lan, "large-v2")  # loads and wraps Whisper model
tokenizer = create_tokenizer(tgt_lan)  # sentence segmenter for the target language
online = OnlineASRProcessor(asr, tokenizer)  # create processing object

def output_transcript(o, now=None):
	start = 0
	# output format in stdout is like:
	# 4186.3606 0 1720 Takhle to je
	# - the first three words are:
	#    - emission time from beginning of processing, in milliseconds
	#    - beg and end timestamp of the text segment, as estimated by Whisper model. The timestamps are not accurate, but they're useful anyway
	# - the next words: segment transcript
	if now is None:
		now = time.time() - start
	if o[0] is not None:
		print("%1.4f %1.0f %1.0f %s" % (now * 1000, o[0] * 1000, o[1] * 1000, o[2]), flush=True)
		print("%1.4f %1.0f %1.0f %s" % (now * 1000, o[0] * 1000, o[1] * 1000, o[2]), flush=True)
	else:
		print(o, flush=True)


# load the audio into the LRU cache before we start the timer
# a = load_audio_chunk(audio_path, 0, 1)
#
# # warm up the ASR, because the very first transcribe takes much more time than the other
# asr.transcribe(a)




def run_transcript(gen):
	beg = 0
	end = 0
	min_chunk = 1
	start = time.time()
	i = 0
	print("ready to transcript")
	for chunk in gen:
		# a = np.frombuffer(chunk, dtype=np.float32)
		now = time.time() - start
		# if now < end + min_chunk:
		# 	time.sleep(min_chunk + end - now)
		data, samplerate = sf.read(chunk, dtype='float32')
		a = load_audio_chunk(data, samplerate, 0, 1)
		# beg = end
		print('chunk loaded, inserting')
		online.insert_audio_chunk(a)

		try:
			o = online.process_iter()
		except AssertionError:
			print("assertion error")
			pass
		else:
			output_transcript(o)
		# now = time.time() - start
		print(f"## last processed {end:.2f} s, now is {now:.2f}, the latency is {now - end:.2f}", flush=True)

	now = None

	o = online.finish()
	output_transcript(o, now=now)