import functools
import json

from flask import render_template, make_response, request
from flask_login import login_required, current_user
from flask_socketio import emit, disconnect, join_room, leave_room

from app import app, socketio, socketio_namespace
from sync import Room, User, Manage


manage = Manage()


@app.route('/create-room', methods=['POST'])
@login_required
def _create_room():
    post_data = request.get_json()
    tab_id = str(post_data.get('tabId', ''))
    room_number = str(post_data.get('roomNumber', ''))
    room_url = str(post_data.get('roomUrl', ''))

    # 判断room url
    if not room_url:
        msg = 'room url (%s) invalid' % room_url
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    # 判断tab id是否为有效值
    if not tab_id.isnumeric():
        msg = 'tab id (%s) invalid' % tab_id
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    # 判断房间号是否为空值
    if room_number == '' or room_number == 'None':
        msg = 'room number(%s) cannot be empty' % room_number
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    # 判断用户是否已经进入房间
    if current_user.email in manage.user_to_room:
        cur_room_number = manage.user_to_room[current_user.email].room_number
        msg = '%s already in room(%s)' % (current_user.nickname, cur_room_number)
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    # 判断此次期望创建的房间是否已存在
    if room_number in manage.rooms:
        msg = 'room(%s) already exists' % room_number
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    room = manage.create_room(room_number, room_url)
    user = User(current_user.email, current_user.nickname, tab_id)
    room.add_user(user)
    manage.create_user_to_room(user.email, room)

    msg = 'room(%s) create success' % room_number
    app.logger.info(msg)
    room_info = room.get_room_info()
    return make_response({'code': 0, 'msg': msg, 'data': {'room': room_info}})


@app.route('/join-room', methods=['POST'])
@login_required
def _join_room():
    post_data = request.get_json()
    room_number = str(post_data.get('roomNumber', None))
    tab_id = str(post_data.get('tabId', ''))

    # 判断tab id是否为有效值
    if not tab_id.isnumeric():
        msg = 'tab id (%s) invalid' % tab_id
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    # 判断是否已经进入房间
    if current_user.email in manage.user_to_room:
        cur_room_number = manage.user_to_room[current_user.email].room_number
        msg = '%s already in room(%s)' % (current_user.nickname, cur_room_number)
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    # 判断期望进入的房间是否存在
    if room_number not in manage.rooms:
        msg = 'room(%s) does not exist' % room_number
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    room = manage.get_room(room_number)
    user = User(current_user.email, current_user.nickname, tab_id)
    room.add_user(user)
    manage.create_user_to_room(user.email, room)

    room_info = room.get_room_info()
    msg = '%s join room(%s)' % (user.nickname, room_number)
    app.logger.info(msg)
    return make_response({'code': 0, 'msg': msg, 'data': {'room': room_info}})


@app.route('/leave-room', methods=['POST'])
@login_required
def _leave_room():
    post_data = request.get_json()
    room_number = str(post_data.get('roomNumber', None))

    if room_number not in manage.rooms:
        msg = 'room(%s) does not exist' % room_number
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    room = manage.get_room(room_number)

    if current_user.email not in room.users:
        msg = '%s not in room(%s)' % (current_user.email, room_number)
        app.logger.info(msg)
        return make_response({'code': 1, 'msg': msg, 'data': {}})

    room.delete_user(current_user.email)
    manage.delete_user_to_room(current_user.email)

    if len(room.users) == 0:
        manage.delete_room(room_number)
        app.logger.info('room(%s) had been delete' % room_number)

    msg = '%s leave room(%s)' % (current_user.nickname, room_number)
    app.logger.info(msg)
    return make_response({'code': 0, 'msg': msg, 'data': {}})


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            app.logger.info('socket authenticated fail')
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped


@socketio.on('connect', namespace=socketio_namespace)
@authenticated_only
def connected():
    nickname = current_user.nickname
    email = current_user.email
    room = manage.get_room_by_email(email)
    if room:
        join_room(room.room_number)
        room.set_user_socketio(email, True)
        room.set_user_video_state(email, 'init')
    app.logger.info('%s socket connected...' % nickname)


@socketio.on('disconnect', namespace=socketio_namespace)
@authenticated_only
def disconnect():
    nickname = current_user.nickname
    email = current_user.email
    room = manage.get_room_by_email(email)
    if room:
        leave_room(room.room_number)
        room.set_user_socketio(email, False)
        room.set_user_video_state(email, 'close')
        room.set_user_video_progress(email, 0)
    app.logger.info('%s socket disconnected...' % nickname)


@socketio.on('update-user-info', namespace=socketio_namespace)
@authenticated_only
def update_user_info(data):
    app.logger.info('socket update_user_info: %s' % json.dumps(data))

    email = current_user.email
    room = manage.get_room_by_email(email)
    current_state = data.get('currentState')
    current_progress = data.get('currentProgress')
    current_socketio = data.get('currentSocketio')

    if room:
        if current_progress:
            room.set_user_video_progress(email, current_progress)
        if current_state:
            room.set_user_video_state(email, current_state)
        if current_socketio:
            room.set_user_socketio(email, current_socketio)
        app.logger.info('%s update-user-info update room success!' % email)


@socketio.on('sync-event', namespace=socketio_namespace)
@authenticated_only
def sync_event(data):
    email = current_user.email
    room = manage.get_room_by_email(email)
    action = data.get('action', '')

    app.logger.info('%s sync event: %s' % (email, json.dumps(data)))

    if action == 'init new sync state':
        time = data.get('time')
        room.init_new_sync_state()
        room.emit_pause_and_jump_order(time)

    elif action == 'update sync state':
        state = data.get('state')
        room.update_sync_state(email, state)





