# import pyaudio
# import wave
#
# # Constants for the audio properties
# FORMAT = pyaudio.paInt16  # Audio format (16-bit PCM)
# CHANNELS = 2              # Number of audio channels (1 for mono, 2 for stereo)
# RATE = 44100              # Sampling rate
# CHUNK = 1024              # Number of frames per buffer
# RECORD_SECONDS = 5        # Duration of recording
# WAVE_OUTPUT_FILENAME = "output.wav"
#
# # Initialize PyAudio
# p = pyaudio.PyAudio()
#
# # Open stream for recording
# stream = p.open(format=FORMAT,
#                 channels=CHANNELS,
#                 rate=RATE,
#                 input=True,
#                 frames_per_buffer=CHUNK)
#
# print("Recording...")
#
# frames = []
#
# # Record audio in chunks for the specified duration
# for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
#     data = stream.read(CHUNK)
#     frames.append(data)
#
# print("Finished recording.")
#
# # Stop and close the stream
# stream.stop_stream()
# stream.close()
#
# # Terminate the PortAudio interface
# p.terminate()
#
# # Save the recorded data as a WAV file
# wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
# wf.setnchannels(CHANNELS)
# wf.setsampwidth(p.get_sample_size(FORMAT))
# wf.setframerate(RATE)
# wf.writeframes(b''.join(frames))
# wf.close()


import pyaudio

p = pyaudio.PyAudio()

info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
        print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

p.terminate()
