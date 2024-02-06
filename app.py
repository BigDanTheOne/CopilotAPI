import socket
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydub import AudioSegment
import asyncio
from copilot import Copilot
import socketio
from queue import Queue as Q
from fastapi.middleware.cors import CORSMiddleware
import redis
import paramiko
import time
import threading
import select

class SSHCredentias:
    ssh_host = 'lorien.atp-fivt.org'
    ssh_username = 'bohonkomi'
    ssh_password = 'ncJUftkzearUC9YxNKK1'
    local_port = 6011
    remote_port = 6011
    remote_host = 'localhost'
    ssh_pkey = None


frame_rate = 48000  # or whatever your frame rate is
sample_width = 2  # sample width in bytes
channels = 1  # mono=1, stereo=2

final_sample_rate = 16000
final_sample_width = 2
final_channels = 1

app = FastAPI(debug=True, )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
class SessionStore(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.r = redis.Redis(host='localhost', port=6379, db=0)
        for key in self.r.keys():
            print(self.r.keys())
            s_id = self.r.get(key)
            self[key] = {'session_id': s_id, 'queue': Q()}


    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if 'session_id' in value:
            self.r.set(key, value['session_id'])

    def __getitem__(self, key):
        return super().__getitem__(key)

    def __delitem__(self, key):
        super().__delitem__(key)
        self.r.delete(key)

session_store = SessionStore()

mgr = socketio.AsyncRedisManager()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*', client_manager=mgr, logger=True)
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
app.mount("/", socket_app)


def transform_audio(raw_audio):
    audio_data = AudioSegment(
        data=raw_audio,
        sample_width=sample_width,
        frame_rate=frame_rate,
        channels=channels
    )
    audio_data = audio_data.set_frame_rate(final_sample_rate).set_channels(final_channels).set_sample_width(
        final_sample_width)
    audio_data = audio_data.raw_data
    return audio_data


@sio.event
async def test_event(sid, message):
    print("Test message received:", message)
    await sio.emit('test_response', {'data': 'Hello from server!'}, to=sid)


@sio.event
async def connect(sid, environ):
    print("Client connected", sid)
    session_id = ''
    # Extract the session_id from the query parameters
    query_params = environ.get('QUERY_STRING', '')
    for param in query_params.split('&'):
        key, value = param.split('=')
        if key == 'session_id':
            session_id = value
    # print("Client's session_is: ", session_id)
    # print("Client's query: ", query_params)

    if session_id and session_id in session_store:
        while not session_store[session_id]['queue'].empty():
            msg = session_store[session_id]['queue'].get()
            await sio.emit(msg['msg_type'], msg['msg_content'], to=sid)
        print(f"Reconnected client {sid} with existing session: {session_id}")
    else:
        # New session, generate a unique session_id
        session_id = str(uuid.uuid4())  # or generate a new ID
        session_store[session_id] = {'sid': sid, 'queue': Q()}  # initialize session data
        print(f"New client {sid} connected with new session: {session_id}")

    # Store the session_id in the socket's session
    await sio.save_session(sid, {'session_id': session_id})
    await sio.emit('session_id', session_id, to=sid)


@sio.event
async def disconnect(sid):
    session = await sio.get_session(sid)
    session_id = session.get('session_id')
    del_worker(session_id)
    del session_store[session_id]
    print(f"Client {sid} disconnected. Session was: {session_id}")


@sio.event
async def new_session(sid, session_id_):
    session = await sio.get_session(sid)
    session_id = session.get('session_id')
    del session_store[session_id]
    if session_id != session_id_:
        print(f"Alarm! Gotn {session_id_}, have {session_id}")
    new_session_id = str(uuid.uuid4())
    while new_session_id in session_store:
        new_session_id = str(uuid.uuid4())
    await sio.save_session(sid, {'session_id': session_id})
    session_store[session_id] = {'sid': sid}  # initialize session data
    await sio.emit('session_id', {'session_id': new_session_id}, to=sid)
    print(f"New session with session_id {new_session_id} for sid {sid} was created")


async def send_msg_async(msg_type, msg_content, session_id):
    if session_id in session_store:
        sid = session_store[session_id].get('sid')
        if sid:
            await sio.emit(msg_type, msg_content, to=sid)
        else:
            session_store[session_id]['queue'].put({'msg_type': msg_type, 'msg_content': msg_content})
    else:
        pass  # TODO: what shell we do here?
    print("end of async sending")


def send_msg(msg_type, msg_content, session_id, loop=None):
    print("inside send_msg")
    if not loop:
        loop = asyncio.get_event_loop()
    return asyncio.run_coroutine_threadsafe(
        send_msg_async(msg_type=msg_type,
                       msg_content=msg_content,
                       session_id=session_id),
        loop
    )


def del_worker(session_id):
    # if session_id in session_store and session_store[session_id].get('worker'):
    #     session_store[session_id]['worker'].terminate()
    #     session_store[session_id]['worker'].join()
    #     del session_store[session_id]['worker']
    pass # TODO


def new_worker(worker, session_id):
    del_worker(session_id)
    session_store[session_id]['worker'] = worker
    session_store[session_id]['worker'].start()


a1, a2 = 0, 0

@sio.event
async def audio_data_tab(sid, data):
    global a2
    session = await sio.get_session(sid)
    session_id = session.get('session_id')
    audio_data = transform_audio(data["audio"])
    a2 += len(data["audio"])
    print("tab: ", a2)
    copilot.send(data={"data": audio_data, "session_id": session_id, "is_mic": False})

@sio.event
async def audio_data_mic(sid, data):
    global a1
    session = await sio.get_session(sid)
    session_id = session.get('session_id')
    audio_data = transform_audio(data["audio"])
    a1 += len(data["audio"])
    print("mic: ", a1)
    copilot.send(data={"data": audio_data, "session_id": session_id, "is_mic": True})


# def create_ssh_tunnel(username, password, host, remote_port, local_port):
#     try:
#         ssh = paramiko.SSHClient()
#         ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#         ssh.connect(host, username=username, password=password)
#         print(f"SSH connection established to {host}")
#
#         # Здесь происходит фактическое создание проброса порта
#         # ssh.get_transport().request_port_forward(host, remote_port)
#         ssh.get_transport().open_channel("forwarded-tcpip", dest_addr=(host,
#                                            remote_port), src_addr=('localhost', local_port))
#
#         print(f"Tunnel opened from localhost:{local_port} to localhost:{remote_port} through {host}")
#
#         # Бесконечный цикл для поддержания туннеля открытым
#         while True:
#             time.sleep(60)
#     except Exception as e:
#         print(f"Failed to create SSH tunnel: {e}")
#     finally:
#         ssh.close()

# def forward_port(local_port, remote_host, remote_port, ssh_host, ssh_username, ssh_password=None, ssh_pkey=None):
#     client = paramiko.SSHClient()
#     client.load_system_host_keys()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#
#     # Connect to the SSH server
#     print(f"Connecting to SSH server {ssh_host} as {ssh_username}...")
#     client.connect(hostname=ssh_host, username=ssh_username, password=ssh_password, pkey=ssh_pkey)
#     print("Connected.")
#
#     # Set up port forwarding
#     transport = client.get_transport()
#     channel = transport.open_channel("direct-tcpip", (remote_host, remote_port), ("localhost", local_port))
#
#     try:
#         while True:
#             r, w, x = select.select([channel], [], [])
#             if channel in r:
#                 try:
#                     data = channel.recv(1024)
#                     if len(data) == 0:
#                         print("\nConnection closed by remote host.")
#                         break
#                     else:
#                         print(data)
#                 except Exception as e:
#                     print(f"\nError: {e}")
#                     break
#     finally:
#         channel.close()
#         client.close()
#         print("SSH connection and port forwarding closed.")
#
#
# def handler(chan, host, port):
#     sock = socket.socket()
#     try:
#         sock.connect((host, port))
#     except Exception as e:
#         print(f"Forwarding request to {host}:{port} failed: {e}")
#         return
#     print(f"Connected! Tunnel open {host}:{port} -> {chan.origin_addr}")
#
#     while True:
#         try:
#             data = sock.recv(1024)
#             if len(data) == 0:
#                 break
#             chan.send(data)
#         except Exception as e:
#             print(f"Connection to {host}:{port} closed: {e}")
#             break
#     chan.close()
#     sock.close()
#
# def forward_tunnel(local_port, remote_host, remote_port, transport):
#     transport.request_port_forward("", local_port)
#     while True:
#         chan = transport.accept(1000)
#         if chan is None:
#             continue
#         thr = threading.Thread(target=handler, args=(chan, remote_host, remote_port))
#         thr.setDaemon(True)
#         thr.start()
#
# def ssh_port_forward(local_port, remote_host, remote_port, ssh_host, ssh_username, ssh_password, ssh_key=None):
#     client = paramiko.SSHClient()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     client.load_system_host_keys()
#
#     print(f"Connecting to SSH server {ssh_host}...")
#     client.connect(ssh_host, username=ssh_username, password=ssh_password, key_filename=ssh_key)
#     print("SSH connection established.")
#
#     transport = client.get_transport()
#     forward_thread = threading.Thread(target=forward_tunnel, args=(local_port, remote_host, remote_port, transport))
#     forward_thread.setDaemon(True)
#     forward_thread.start()
#
#     print(f"Port forwarding setup: 'localhost:{local_port}' to '{remote_host}:{remote_port}' through SSH.")
#     forward_thread.join()


if __name__ == "__main__":
    from uvicorn import Config, Server
    # threading.Thread(target=ssh_port_forward, args=(SSHCredentias.local_port, SSHCredentias.remote_host, SSHCredentias.remote_port,
    #                                             SSHCredentias.ssh_host, SSHCredentias.ssh_username, SSHCredentias.ssh_password,
    #                                             SSHCredentias.ssh_pkey)).start()
    # time.sleep(5)
    main_loop = asyncio.new_event_loop()
    copilot = Copilot(send_msg, new_worker, main_loop)
    copilot.run()

    config = Config(app=app, loop=main_loop)
    server = Server(config)
    main_loop.run_until_complete(server.serve())
    # uvicorn.run(app, host="127.0.0.1", port=8000)
