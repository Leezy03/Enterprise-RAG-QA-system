"""
JWT认证工具
提供Token生成、验证以及登录权限装饰器
"""
import jwt
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, current_app


def md5_encrypt(text):
    """
    MD5加密
    :param text: 原始字符串
    :return: MD5加密后的字符串
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def generate_token(user_id, role):
    """
    生成JWT Token
    :param user_id: 用户ID
    :param role: 用户角色
    :return: Token字符串
    """
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(seconds=current_app.config['JWT_EXPIRATION'])
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token


def verify_token(token):
    """
    验证JWT Token
    :param token: Token字符串
    :return: 解码后的payload或None
    """
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    """
    登录验证装饰器
    要求请求头中携带有效的Authorization Token
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if token.startswith('Bearer '):
            token = token[7:]

        if not token:
            from utils.response import error
            return error('请先登录', 401)

        payload = verify_token(token)
        if not payload:
            from utils.response import error
            return error('登录已过期，请重新登录', 401)

        # 将用户信息存入g对象，供后续使用
        g.user_id = payload['user_id']
        g.role = payload['role']
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """
    管理员权限装饰器
    要求用户已登录且角色为admin
    """
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if g.role != 'admin':
            from utils.response import error
            return error('权限不足，需要管理员权限', 403)
        return f(*args, **kwargs)

    return decorated
