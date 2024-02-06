import threading
import time
import json
import socket
import pickle
from openai import OpenAI


msgs = [
    "Михаил, спасибо за вашу честность. Я понимаю, что у вас возникли определенные предубеждения по отношению к нашей продукции. Это нормально, когда люди скептически относятся к чему-то новому или к продуктам, о которых слышали смешанные отзывы. Я был бы рад поделиться с вами актуальной информацией о наших пылесосах и тех инновациях, которые мы внедрили в модель Kirby 9000. Это поможет вам сформировать свое мнение на основе фактов. Может быть, есть конкретные моменты или вопросы, которые вызывают у вас сомнения? Это позволит мне дать более развернутый и точный ответ.",
    "Михаил, я понимаю, что у вас уже есть пылесос, и это важно. Однако, как специалист в этой области, я хотел бы отметить, что наш новый Kirby 9000 предлагает некоторые уникальные функции и технологии, которые могут не только упростить уборку, но и существенно улучшить качество воздуха в вашем доме. Это особенно актуально в наше время, когда важность чистого воздуха и гигиены в доме повышается. Возможно, вы бы хотели узнать о некоторых ключевых особенностях нашего продукта, которые могут предложить вам нечто большее, чем ваш текущий пылесос? Например, способность уничтожать вирусы и аллергены может быть особенно полезной для вашего дома.",
    "Михаил, это отлично, что у вас нет аллергии. Здоровье и комфорт в доме действительно важны. Наш пылесос Kirby 9000 не только помогает людям с аллергией, но и обеспечивает более глубокую и эффективную уборку благодаря передовым технологиям. Например, он оснащен системой фильтрации последнего поколения, которая позволяет улавливать даже мельчайшие частицы пыли и грязи, что обычные пылесосы не всегда могут сделать. Могу я спросить, какие задачи уборки у вас наиболее часто возникают дома? Возможно, наш продукт имеет конкретные функции, которые могут существенно упростить эти процессы для вас.",
    "Михаил, благодарю за эту информацию. Понимаю, что уход за паркетом требует особого подхода, чтобы сохранить его красоту и продлить срок службы. Наш пылесос Kirby 9000 оснащен специальными насадками для ухода за паркетом, которые бережно удаляют пыль и грязь, не царапая поверхность. Кроме того, он обладает системой регулировки мощности всасывания, что позволяет эффективно очищать паркет, не повреждая его. Если вы разрешите, я могу показать вам, как Kirby 9000 работает на паркете прямо у вас дома, чтобы вы могли увидеть результат и оценить удобство использования лично. Как вам такая идея?",
    "Ручные пылесосы, вроде Kirby 9000, удобнее и мобильнее обычных благодаря их компактности и отсутствию проводов. Они также мощнее и эффективнее в уборке, собирая больше пыли и грязи, и оснащены специальными насадками для разных поверхностей."
        ]


class ChatGPTWorker(threading.Thread):
    def __init__(self, session_id, messages, socket, llm, mic, send_msg, loop):
        super().__init__()
        self.session_id = session_id
        self.messages = messages
        self.socket = socket
        self.llm = llm
        self.mic = mic
        self.send_msg = send_msg
        self._stop_event = threading.Event()
        self.loop = loop
    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        print(f"Starting worker for client {self.session_id}")
        try:
            if not self.stopped():
                completion = self.llm.chat.completions.create(
                    model="gpt-3.5-turbo-1106",
                    messages=self.messages,
                    stream=True
                )
                if self.mic == 'feedback':
                    print('>>>>>>>>>>Feedback:')
                    ans = ''
                    for chunk in completion:
                        if chunk.choices[0].delta.content:
                            ans += chunk.choices[0].delta.content
                            print('feedback: ', ans, self.messages)
                            self.send_msg(msg_type='feedback', msg_content={'response': ans}, session_id=self.session_id, loop=self.loop)

                    return
                if self.mic:
                    print('User hint form ChatGPT: ')
                else:
                    print('Interviewer hint from ChatGPT: ')
                ans = ''
                l = 0
                for m in self.messages:
                    if m["role"] == "user":
                        l += 1
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        ans += chunk.choices[0].delta.content
                        print(ans, self.messages)
                        self.send_msg(msg_type='copilot',
                                      msg_content={'session_id': self.session_id, 'response': ans, 'len': l},
                                      session_id=self.session_id,
                                      loop=self.loop)
        except Exception as e:
            print(e)
        finally:
            print(f"Worker for client {self.session_id} stopped")

class Copilot:
    def __init__(self, send_msg, new_worker, loop, host='127.0.0.1', port=6011, OPENAI_API_KEY = "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"):
        self.mic_history = []
        self.tab_history = []
        self.gpt_messages = []
        self.history = []
        self.lock = threading.Lock()
        self.host = host
        self.port = port
        self.send_msg = send_msg
        self.new_worker = new_worker
        self.llm = OpenAI(api_key=OPENAI_API_KEY)
        self.stop_event = None
        self.s = None
        self.loop = loop
        self.uber_lock = threading.Lock()


    def update(self, session_id, data, is_mic):
        if data == "":
            return
        print(">>>>>>>>>>>>>>>>" + data, is_mic)
        if is_mic:
            self.mic_history.append(data)
            self.history.append(['mic', data])
            # print("Mic:>>>>>>>>>>>" + data)
            self.send_msg(msg_type="mic_transcript",
                          msg_content={'session_id': session_id, 'response': data, 'len': len(self.mic_history)},
                          session_id=session_id,
                          loop=self.loop)
            print("send_msg finished")
        else:
            prompt_base = """
Веди себя как опытный менеджер по продажам с 20-летним стажем в KIRBY - американской компании с представительствами по всему миру. Твоя задача - анализировать реплики клиента и предлагать конструктивные ответы, которые преодолевают возражения и продвинуть сделку. 
При отсутствии возражений - предлагай стратегию дальнейшего развития диалога, направленную на установление контакта, выявление потребностей и мотивацию клиента. 
Фокусируйся на построении доверия, вникании в ситуацию клиента, предложении взаимовыгодных решений. Избегай навязчивости и излишнего давления. 
В ответе формулируй конкретное высказывание для менеджера применительно к текущему моменту диалога с клиентом. Учитывай контекст и эмоциональный окрас беседы. Цель одна - "заполучить клиента". Каждый твой ответ - лишь ответ как человека - без ненужной информации или вводных слов модели перед настоящим ответом.
            """
            self.tab_history.append(data)
            self.history.append(['tab', data])
            self.send_msg(msg_type="tab_transcript",
                          msg_content = {'session_id': session_id, 'response': data, 'len': len(self.tab_history)},
                          session_id=session_id,
                          loop=self.loop)
            messages = [
                {"role": "system",
                 "content": prompt_base},
            ]
            for i, msg in enumerate(self.history):
                if msg[0] == 'tab':
                    messages.append({"role": "user", "content": msg[1]})
                else:
                    messages.append({"role": "assistant", "content": msg[1]})
            # self.new_worker(ChatGPTWorker(session_id, messages, socket, self.llm, is_mic, self.send_msg, self.loop),
            #                 session_id)


    def send(self, data=None):
        with self.uber_lock:
            data = pickle.dumps(data)
            self.s.sendall(data)
            time.sleep(0.03)

    def receiver(self):
        try:
            while True: # постоянно, пока не стопнули
                data = bytearray()  # Используем bytearray для накопления данных
                while True:
                    chunk = self.s.recv(1024)  # приняли чанк
                    print("data recvd", data)
                    data.extend(chunk)
                    if (len(chunk) < 1024) and (
                            len(chunk) > 0):  # если пакет пуст или неполный, то это последний или некорректный чанк
                        break

                if len(data) > 0:
                    try:
                        data = pickle.loads(data)  # расшифровываем данные
                        session_id = data["session_id"]
                        is_mic = data["is_mic"]
                        data = data["data"]
                    except:
                        print("error to unpack")
                    else:
                        self.update(session_id, data, is_mic)
                    # threading.Thread(target=self._process_input_data, args=(data,)).start()
                else:
                    print("nothing")
        except OSError as e:
            print("Error in receiving messages:", e)


    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.s:
            self.s.connect((self.host, self.port))
            print(f"Connected by {self.s}")
            self.receiver()


    def run(self):
        server = threading.Thread(target=self.start_server)
        server.start()
