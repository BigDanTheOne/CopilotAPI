import threading
import time
import grpc
from .yandex.cloud.ai.stt.v3 import stt_pb2
from .yandex.cloud.ai.stt.v3 import stt_service_pb2_grpc
import json
from openai import OpenAI

OPENAI_API_KEY = "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"

client = OpenAI(api_key=OPENAI_API_KEY)

prompt = """
Веди себя как кандидат который проходит интервью на позицию Product Owner. Описание позиции:
Product owner DMP (Рекламная платформа)
SberAds - новая команда в экосистеме Сбера, которая разрабатывает современную рекламную платформу для монетизации поверхностей Экосистемы и внешних клиентов. Новая платформа должна объединить в себе технологические решения AdTech и возможности больших данных экосистемы.
Один из ключевых продуктов SberAds - DMP (Data Management Platform). Эта платформа соединяет в себе знания о поведении пользователей в интернете и знания о пользователях банка, превращая это в тысячи признаков для сотен миллионов клиентов.
Готовый профиль DMP предоставляет в виде фичи таргетинга в два рекламных продукта - медийная и perfomance реклама.

Мы ищем Product Owner, который возглавит эту команду.

Обязанности:
Создание и запуск на рынок SberAds.Аудитории, это позволит рекламодателям самостоятельно создать сегменты и использовать их при открутке рекламы;
Отмасштабировать платформу DMP с десятка до сотни тысяч регулярно обновляемых сегментов;
Развитие таргетирования в перфоманс и медийной рекламе;
Руководство мультифункциональной командой: de, da, ds, go, js;
Создание и превращение в жизнь стратегии развития профиля пользователя SberAds;
Общение с внутренними и внешними клиентами.
Требования
Опыт лидирования команды разработки от 3х лет;
Опыт работы над продуктом/технологией основанных на анализе данных;
Готовность принимать решения и брать на себя ответственность;
Будет плюсом:
Опыт работы в DMP/CDP/CRM - like решениях;
Опыт работы в рекламе;
Я буду задавать тебе вопросы и хочу, чтобы ты на них отвечал. В ответах будь максимально конкретен, например называй конкретные наименований фреймворков или технологий, которыми ты будешь пользоваться. 
Ответ выдай в таком виде:
## Заголовок 1
- подпункт 1
- подпункт 2
...
## Заголовок 2
- подпункт 1
...
"""

recognize_options = stt_pb2.StreamingOptions(
    recognition_model=stt_pb2.RecognitionModelOptions(
        audio_format=stt_pb2.AudioFormatOptions(
            # container_audio=stt_pb2.ContainerAudio(
            #     container_audio_type=stt_pb2.ContainerAudio.OGG_OPUS
            # ),
            raw_audio=stt_pb2.RawAudio(
                audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                sample_rate_hertz=8000,
                audio_channel_count=1
            ),
        ),
        text_normalization=stt_pb2.TextNormalizationOptions(
            text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_DISABLED,
            profanity_filter=True,
            literature_text=False
        ),
        language_restriction=stt_pb2.LanguageRestrictionOptions(
            restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
            language_code=['ru-RU']
        ),
        audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME
    )
)


class Copilot:

    def __init__(self, iam_token, yandex_folder_id='b1gdp45prmdkt1e1gjso'):
        self.iam_token = iam_token
        # Установите соединение с сервером.
        cred = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel('stt.api.cloud.yandex.net:443', cred)
        self.stub = stt_service_pb2_grpc.RecognizerStub(channel)
        self.yandex_folder_id = yandex_folder_id
        self.user_id = '4e6a4022-796c-42d2-91fa-b8184778a4ca'
        self.mic_history = []
        self.tab_history = []
        self.history = []

    def set_userid(self, user_id):
        self.user_id = user_id


    def run(self, gen, mic, socketio, cid_uid_map):

        def chatgpt_worker(messages, user_id, cid_uid_map, socketio, client, mic):
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=messages,
                stream=True
            )
            if mic:
                print('User hint form ChatGPT: ')
            else:
                print('Interviewer hint from ChatGPT: ')
            ans = ''
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    ans += chunk.choices[0].delta.content
                socketio.emit('copilot',
                              {'user_id': user_id, 'response': ans, 'len': len(messages) - 1},
                              room=cid_uid_map[user_id])

        start = time.time()
        print(self.iam_token)
        metadata = [
            ('authorization', f'Bearer {self.iam_token}'),
            ('x-folder-id', self.yandex_folder_id)
        ]
        it = self.stub.RecognizeStreaming(gen(mic), metadata=metadata)
        for r in it:
            event_type, alternatives = r.WhichOneof('Event'), None
            if event_type == 'partial' and len(r.partial.alternatives) > 0:
                alternatives = [a.text for a in r.partial.alternatives]
                destination = "mic_transcript"
                length = len(self.mic_history)
                if mic:
                    print(f'Partial message from the user: {alternatives[0]}')
                else:
                    print(f'Partial message from the interviewer: {alternatives[0]}')
                    destination = "tab_transcript"
                    length = len(self.tab_history)
                socketio.emit(destination, {'user_id': self.user_id, 'response': alternatives[0], 'len': length + 1},
                              room=cid_uid_map[self.user_id])
            if event_type == 'final':
                alternatives = [a.text for a in r.final.alternatives]
                if alternatives[0] == '':
                    continue
                destination = "mic_transcript"
                if mic:
                    print(f'Final message from the user: {alternatives[0]}')
                    length = len(self.mic_history)
                else:
                    print(f'Final message from the interviewer: {alternatives[0]}')
                    destination = "tab_transcript"

                    length = len(self.tab_history)
                socketio.emit(destination, {'user_id': self.user_id, 'response': alternatives[0], 'len': length + 1},
                              room=cid_uid_map[self.user_id])
                messages = []
                if mic:
                    self.mic_history.append(alternatives[0])
                    self.history.append(['mic', alternatives[0]])
                    # messages = [
                    #     {"role": "system",
                    #      "content": "Выступать в роли репетитора на собеседовании. Критикуйте мои ответы, которые я вам дам."},
                    # ]
                    # for i, msg in enumerate(self.history):
                    #     if msg[0] == 'mic':
                    #         messages.append({"role": "user", "content": msg[1]})
                    #     else:
                    #         if i == 0:
                    #             messages.append({"role": "user", "content": 'Здравствуйте.'})
                    #         messages.append({"role": "assistant", "content": msg[1]})
                else:
                    self.tab_history.append(alternatives[0])
                    self.history.append(['tab', alternatives[0]])
                    messages = [
                        {"role": "system",
                         "content": prompt},
                    ]
                    for i, msg in enumerate(self.history):
                        if msg[0] == 'tab':
                            messages.append({"role": "user", "content": msg[1]})
                        else:
                            if i == 0:
                                messages.append({"role": "user", "content": 'Здравствуйте.'})
                            messages.append({"role": "assistant", "content": msg[1]})

                    print(messages)
                    threading.Thread(target=chatgpt_worker,
                                     args=(messages, self.user_id, cid_uid_map, socketio, client, mic)).start()

                if time.time() - start > 4 * 60:
                    print('rebooting...')
                    self.run(gen, mic, socketio, cid_uid_map)
