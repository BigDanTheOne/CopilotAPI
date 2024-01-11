import threading
import speechmatics
from httpx import HTTPStatusError
from openai import OpenAI
import asyncio


OPENAI_API_KEY = "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"
TOKEN = "GRNjgYZN3N5Exo3rNY8lJsL77e9Ep39S"
client = OpenAI(api_key=OPENAI_API_KEY)


class AsyncStreamWrapper:
    def __init__(self, generator):
        self.generator = generator
        self.queue = asyncio.Queue()

    async def read(self, size=-1):
        try:
            # Try to get the next chunk from the generator
            chunk = next(self.generator)
            await self.queue.put(chunk)
            return await self.queue.get()
        except StopIteration:
            # No more data to read
            return b''

class Copilot:
    def __init__(self):
        self.api_key = TOKEN
        self.language = 'ru'
        self.connection_url = "wss://eu2.rt.speechmatics.com/v2"
        self.socketio = None
        self.user_id = None
        self.mic_history = []
        self.tab_history = []
        self.history = []
        self.cid_uid_map = None


    def set_userid(self, user_id):
        self.user_id = user_id


    def run(self, audio_chunk_generator, mic, socketio, cid_uid_map):
        self.cid_uid_map = cid_uid_map
        self.socketio = socketio
        try:
            # Create a transcription client
            ws = speechmatics.client.WebsocketClient(
                speechmatics.models.ConnectionSettings(
                    url=self.connection_url,
                    auth_token=self.api_key,
                )
            )

            # Register event handlers
            ws.add_event_handler(
                event_name=speechmatics.models.ServerMessageType.AddPartialTranscript,
                event_handler=lambda msg: self.handle_transcript(msg, mic, is_partial=True)
            )

            ws.add_event_handler(
                event_name=speechmatics.models.ServerMessageType.AddTranscript,
                event_handler=lambda msg: self.handle_transcript(msg, mic, is_partial=False)
            )

            # Transcription configuration
            conf = speechmatics.models.TranscriptionConfig(
                language=self.language,
                enable_partials=True,
                max_delay=3,
            )

            settings = speechmatics.models.AudioSettings()

            # Run transcription synchronously
            audio_stream = self.generate_audio_stream(audio_chunk_generator, mic)
            ws.run_synchronously(audio_stream, conf, settings)

        except KeyboardInterrupt:
            print("\nTranscription stopped.")
        except HTTPStatusError as e:
            if e.response.status_code == 401:
                print('Invalid API key - Check your API_KEY!')
            else:
                raise e


    def generate_audio_stream(self, audio_chunk_generator, mic):
        gen = audio_chunk_generator(mic)
        wrapper = AsyncStreamWrapper(gen)
        return wrapper


    # def generate_audio_stream(self, audio_chunk_generator, mic):
    #     for chunk in audio_chunk_generator(mic):
    #         yield chunk


    def handle_transcript(self, msg, mic, is_partial):
        transcript = msg['metadata']['transcript']
        destination = "mic_transcript" if mic else "tab_transcript"
        history = self.mic_history if mic else self.tab_history
        history.append(transcript)
        # self.socketio.emit(destination,
        #                    {'user_id': self.user_id, 'response': transcript, 'len': len(history)},
        #                    room=self.cid_uid_map[self.user_id])
        if not is_partial:
            print(transcript)
            # self.process_completion(transcript, mic)


    # def process_completion(self, transcript, mic):
    #     messages = self.generate_chat_messages(transcript, mic)
    #     threading.Thread(target=self.chatgpt_worker,
    #                      args=(messages, mic)).start()
    #
    #
    # def generate_chat_messages(self, transcript, mic):
    #     # Generate the chat messages for GPT-3 based on the current history
    #     # Implement the logic here based on your requirements
    #     return messages
    #
    #
    # def chatgpt_worker(self, messages, mic):
    #     # Implement the logic to interact with OpenAI's GPT-3
    #     pass
