import functools
from flask_socketio import emit
from app import socketio_namespace, app


class Singleton(object):
    def __init__(self, cls):
        self._cls = cls
        self._instance = {}

    def __call__(self):
        if self._cls not in self._instance:
            self._instance[self._cls] = self._cls()
        return self._instance[self._cls]


class User:
    def __init__(self, email: str, nickname: str, tab_id: str):
        self.email = email
        self.nickname = nickname
        self._socketio = False
        self._url = None
        self._tab_id = tab_id
        self._video_state = 'init'  # onload oncanplay onplaying onpause
        self._video_progress = 0

    @staticmethod
    def keys():
        return 'email', 'nickname', 'url', 'tab_id', 'socketio', 'video_state', 'video_progress'

    def __getitem__(self, item):
        return getattr(self, item)

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url: str):
        self._url = url

    @property
    def tab_id(self):
        return self._tab_id

    @tab_id.setter
    def tab_id(self, tab_id: str):
        self._tab_id = tab_id

    @property
    def socketio(self):
        return self._socketio

    @socketio.setter
    def socketio(self, value):
        self._socketio = value

    @property
    def video_state(self):
        return self._video_state

    @video_state.setter
    def video_state(self, state: int):
        self._video_state = state

    @property
    def video_progress(self):
        return self._video_progress

    @video_progress.setter
    def video_progress(self, progress: int):
        self._video_progress = progress


class Room:
    def __init__(self, room_number: str, room_url: str):
        self.room_number: str = room_number
        self.room_url: str = room_url
        self.video_identify: str = ''
        self.users: dict[str, User] = {}  # email -> user
        self.sync_state: [{str, int}] = []  # email -> [0, 1]

    def init_new_sync_state(self):
        app.logger.info('init_new_sync_state')
        new_state = {email: 0 for email in self.users.keys()}
        self.sync_state.append(new_state)

    def update_sync_state(self, email: str, state: int):
        app.logger.info('%s update_sync_state' % email)
        self.sync_state[-1][email] = state
        if self.is_sync_state_all_ready():
            self.emit_play_order()

    def is_sync_state_all_ready(self) -> bool:
        res = True
        for email, state in self.sync_state[-1].items():
            if state == 0:
                res = False
                break
        return res

    def emit_pause_and_jump_order(self, time: int, sync_type: str):
        emit('videoAction', {'action': 'pause', 'time': time, 'type': sync_type}, to=self.room_number,
             namespace=socketio_namespace)

    def emit_play_order(self):
        emit('videoAction', {'action': 'play'}, to=self.room_number, namespace=socketio_namespace)

    def emit_update_url_order(self, url: str):
        emit('videoAction', {'action': 'updateUrl', 'url': url}, include_self=False, to=self.room_number,
             namespace=socketio_namespace)

    def get_room_info(self):
        # 获取对象的字典表示形式
        users_data = {k: dict(v) for k, v in self.users.items()}
        room_data = {
            'room_number': self.room_number,
            'room_url': self.room_url,
            'video_identify': self.video_identify,
            'users': users_data
        }
        return room_data

    @staticmethod
    def user_info_change_notify(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            res = func(self, *args, **kwargs)
            data = self.get_room_info()
            emit('room-panel', data, namespace=socketio_namespace, to=self.room_number)
            return res

        return wrapper

    @user_info_change_notify
    def add_user(self, user: User) -> bool:
        email = user.email

        if email not in self.users:
            self.users[email] = user
            return True

        return False

    @user_info_change_notify
    def delete_user(self, email: str) -> bool:
        if email in self.users:
            del self.users[email]
            return True

        return False

    @user_info_change_notify
    def set_user_video_progress(self, email: str, video_progress: int) -> bool:
        if email in self.users:
            user = self.users[email]
            user.video_progress = video_progress
            return True

        return False

    @user_info_change_notify
    def set_user_socketio(self, email: str, socket: bool) -> bool:
        if email in self.users:
            user = self.users[email]
            user.socketio = socket
            return True

        return False

    @user_info_change_notify
    def set_user_video_state(self, email: str, video_state: int) -> bool:
        if email in self.users:
            user = self.users[email]
            user.video_state = video_state
            return True

        return False


@Singleton
class Manage:
    def __init__(self):
        self.rooms: dict[str, Room] = {}  # room number -> room
        self.user_to_room: dict[str, Room] = {}  # email -> room

    def get_room(self, room_number: str):
        if room_number in self.rooms:
            room = self.rooms[room_number]
            return room
        return None

    def create_room(self, room_number, room_url):
        if room_number not in self.rooms:
            room = Room(room_number, room_url)
            self.rooms[room_number] = room
            return room
        return None

    def delete_room(self, room_number: str) -> bool:
        if room_number in self.rooms:
            del self.rooms[room_number]
            return True
        return False

    def get_room_by_email(self, email: str):
        if email in self.user_to_room:
            return self.user_to_room[email]
        return None

    def create_user_to_room(self, email: str, room: Room) -> bool:
        if email not in self.user_to_room:
            self.user_to_room[email] = room
            return True
        return False

    def delete_user_to_room(self, email: str) -> bool:
        if email in self.user_to_room:
            del self.user_to_room[email]
            return True
        return False
