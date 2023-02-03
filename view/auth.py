import json
import time

from flask import request, make_response, render_template
from flask_login import login_user, login_required, logout_user, current_user
from app import app, db, login_manager
from models import User
from sync import Manage


manage = Manage()


# 用户加载回调函数
@login_manager.user_loader
def load_user(email: str):                # 创建用户加载回调函数，接受用户 Email 作为参数
    user = User.query.get(str(email))     # 用 Email 作为 User 模型的主键查询对应的用户
    return user


# 用户注册
@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        post_data = request.get_json()
        account = post_data.get('account', None)
        password = post_data.get('password', None)
        nickname = post_data.get('nickname', None)

        # 账号或密码为空
        if not account or not password or not nickname:
            rsp = {'code': 1, 'msg': '账号密码和昵称不能为空', 'data': {}}
            return make_response(rsp, 400)

        # 检查用户是否被注册
        user = User.query.filter_by(email=account).first()
        if user:
            rsp = {'code': 1, 'msg': '账号已被注册', 'data': {}}
            return make_response(rsp, 400)

        # 用户注册
        user = User()
        user.email = account
        user.nickname = nickname
        user.set_password(password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)

        rsp = {'code': 0, 'msg': '注册成功', 'data': {'user': {'nickname': user.nickname, 'email': user.email}}}
        return make_response(rsp, 200)

    if request.method == 'GET':
        return render_template("login.html")

    # 兜底回复
    rsp = {'code': 1, 'msg': '注册失败', 'data': {}}
    return make_response(rsp, 400)


# 用户登录
@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        post_data = request.get_json()
        account = post_data.get('account', None)
        password = post_data.get('password', None)

        # 账号或密码为空
        if not account or not password:
            rsp = {'code': 1, 'msg': '账号和密码不能为空', 'data': {}}
            return make_response(rsp, 400)

        # 从数据库获取对应用户
        user = User.query.filter_by(email=account).first()

        # 验证用户名和密码是否一致
        if user and user.validate_password(password):
            login_user(user, remember=True)
            rsp = {'code': 0, 'msg': '登录成功',  'data': {'user': {'nickname': user.nickname, 'email': user.email}}}
            app.logger.info(rsp)
            return make_response(rsp, 200)

        rsp = {'code': 1, 'msg': '登录验证失败', 'data': {}}
        return make_response(rsp, 400)

    if request.method == 'GET':
        return render_template("login.html")

        # 兜底回复
    rsp = {'code': 1, 'msg': '登录失败', 'data': {}}
    return make_response(rsp, 400)


# 用户登出
@app.route('/sign-out', methods=['GET', 'POST'])
@login_required
def sign_out():
    try:
        user_email = current_user.email
        logout_user()
        rsp = {'code': 0, 'msg': user_email + ' logout', 'data': {}}
        return make_response(rsp)
    except Exception as e:
        rsp = {'code': 1, 'msg': str(e), 'data': {}}
        return make_response(rsp)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # 用户未登录
    if not current_user.is_authenticated:
        return make_response({'code': 1, 'msg': 'user not authenticated', 'data': {}})

    room = manage.get_room_by_email(current_user.email)
    user_info = current_user.to_dict(rules=('-password_hash', '-id'))

    if room:
        user_info = dict(room.users[current_user.email])

    # 用户未加入房间
    if not room:
        return make_response({'code': 0, 'msg': 'success', 'data': {'user': user_info}})

    room_info = room.get_room_info()
    return make_response({'code': 0, 'msg': 'success', 'data': {'user': user_info, 'room': room_info}})


@app.route('/policy', methods=['GET'])
def policy():
    return render_template('policy.html')
