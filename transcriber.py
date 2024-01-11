import whisper


audio_model = whisper.load_model("large-v2")
audio_data = b''.join(data_queue.queue)
audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available())
text = result['text'].strip()