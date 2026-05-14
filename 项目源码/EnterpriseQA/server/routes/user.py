"""
用户管理路由
提供用户的增删改查接口（仅管理员可用）
"""
from flask import Blueprint, request
from models import db
from models.user import User
from utils.auth import admin_required, md5_encrypt
from utils.response import success, error, page_response

# 创建用户管理蓝图
user_bp = Blueprint('user', __name__)


@user_bp.route('/list', methods=['GET'])
@admin_required
def get_list():
    """
    获取用户列表（分页，仅管理员）
    查询参数: page, page_size, keyword
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    keyword = request.args.get('keyword', '').strip()

    query = User.query
    if keyword:
        query = query.filter(
            db.or_(
                User.username.like(f'%{keyword}%'),
                User.nickname.like(f'%{keyword}%')
            )
        )

    query = query.order_by(User.create_time.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@user_bp.route('', methods=['POST'])
@admin_required
def create():
    """
    新增用户（仅管理员）
    请求参数: username, password, nickname, role
    """
    data = request.get_json()
    if not data:
        return error('请提供用户信息')

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    nickname = data.get('nickname', '').strip()
    role = data.get('role', 'user')

    if not username or not password:
        return error('用户名和密码不能为空')

    # 检查用户名是否已存在
    existing = User.query.filter_by(username=username).first()
    if existing:
        return error('用户名已存在')

    user = User(
        username=username,
        password=md5_encrypt(password),
        nickname=nickname or username,
        role=role
    )
    db.session.add(user)
    db.session.commit()

    return success(user.to_dict(), '创建成功')


@user_bp.route('/<int:user_id>', methods=['PUT'])
@admin_required
def update(user_id):
    """
    编辑用户信息（仅管理员）
    路径参数: user_id
    请求参数: nickname, role, status, password(可选)
    """
    user = User.query.get(user_id)
    if not user:
        return error('用户不存在', 404)

    data = request.get_json()
    if data.get('nickname'):
        user.nickname = data['nickname']
    if data.get('role'):
        user.role = data['role']
    if 'status' in data:
        user.status = data['status']
    if data.get('password'):
        user.password = md5_encrypt(data['password'])

    db.session.commit()
    return success(user.to_dict(), '更新成功')
