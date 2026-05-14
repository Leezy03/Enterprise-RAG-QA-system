"""
认证路由
提供用户登录和获取用户信息接口
"""
from flask import Blueprint, request, g
from models.user import User
from utils.auth import md5_encrypt, generate_token, login_required
from utils.response import success, error

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录接口
    请求参数: username, password
    返回: token和用户信息
    """
    data = request.get_json()
    if not data:
        return error('请提供登录信息')

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return error('用户名和密码不能为空')

    # 查找用户
    user = User.query.filter_by(username=username).first()
    if not user:
        return error('用户名或密码错误')

    # 验证密码（MD5加密后比对）
    if user.password != md5_encrypt(password):
        return error('用户名或密码错误')

    # 检查用户状态
    if user.status != 1:
        return error('账号已被禁用，请联系管理员')

    # 生成Token
    token = generate_token(user.id, user.role)

    return success({
        'token': token,
        'user': user.to_dict()
    }, '登录成功')


@auth_bp.route('/info', methods=['GET'])
@login_required
def get_user_info():
    """
    获取当前登录用户信息
    需要携带有效Token
    """
    user = User.query.get(g.user_id)
    if not user:
        return error('用户不存在', 404)

    return success(user.to_dict())
