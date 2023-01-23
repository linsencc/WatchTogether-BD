# -*- coding: utf-8 -*-
import os
import sys
import logging


from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler


# logging.basicConfig(level='INFO')

# Windows系统，使用三个斜线
WIN = sys.platform.startswith('win')
prefix = 'sqlite:///' if WIN else 'sqlite:////'


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')


# chrome samesite设置，允许跨域携带cookie
# https://learn.microsoft.com/zh-cn/azure/active-directory/develop/howto-handle-samesite-cookie-changes-chrome-browser
app.config['REMEMBER_COOKIE_SAMESITE'] = "None"
app.config['REMEMBER_COOKIE_SECURE'] = True


# 允许全局跨域
cors = CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


# 数据库
db = SQLAlchemy(app)


# websocket
socketio = SocketIO(app)
socketio.init_app(app, cors_allowed_origins='*')
socketio_namespace = '/room'


# 用户登录
login_manager = LoginManager(app)
login_manager.login_view = 'sign_in'


# 加载views中逻辑函数，models中数据模型，不可删除
from views_auth import *
from views_logit import *
from views_test import *


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()
