"""
知识库路由
提供知识库的增删改查接口
"""
from flask import Blueprint, request, g
from models import db
from models.knowledge_base import KnowledgeBase
from utils.auth import login_required, admin_required
from utils.response import success, error, page_response

# 创建知识库蓝图
kb_bp = Blueprint('knowledge_base', __name__)


@kb_bp.route('/list', methods=['GET'])
@login_required
def get_list():
    """
    获取知识库列表（分页）
    查询参数: page, page_size, keyword
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    keyword = request.args.get('keyword', '').strip()

    query = KnowledgeBase.query.filter_by(status=1)

    # 关键词搜索
    if keyword:
        query = query.filter(KnowledgeBase.kb_name.like(f'%{keyword}%'))

    query = query.order_by(KnowledgeBase.create_time.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@kb_bp.route('/all', methods=['GET'])
@login_required
def get_all():
    """
    获取所有启用的知识库（不分页，用于下拉选择）
    """
    kb_list = KnowledgeBase.query.filter_by(status=1).order_by(KnowledgeBase.create_time.desc()).all()
    return success([kb.to_dict() for kb in kb_list])


@kb_bp.route('', methods=['POST'])
@admin_required
def create():
    """
    新增知识库（仅管理员）
    请求参数: kb_name, description
    """
    data = request.get_json()
    if not data or not data.get('kb_name'):
        return error('知识库名称不能为空')

    kb = KnowledgeBase(
        kb_name=data['kb_name'],
        description=data.get('description', ''),
        creator_id=g.user_id
    )
    db.session.add(kb)
    db.session.commit()

    return success(kb.to_dict(), '创建成功')


@kb_bp.route('/<int:kb_id>', methods=['PUT'])
@admin_required
def update(kb_id):
    """
    编辑知识库（仅管理员）
    路径参数: kb_id
    请求参数: kb_name, description
    """
    kb = KnowledgeBase.query.get(kb_id)
    if not kb:
        return error('知识库不存在', 404)

    data = request.get_json()
    if data.get('kb_name'):
        kb.kb_name = data['kb_name']
    if 'description' in data:
        kb.description = data['description']

    db.session.commit()
    return success(kb.to_dict(), '更新成功')


@kb_bp.route('/<int:kb_id>', methods=['DELETE'])
@admin_required
def delete(kb_id):
    """
    删除知识库（仅管理员，逻辑删除）
    路径参数: kb_id
    """
    kb = KnowledgeBase.query.get(kb_id)
    if not kb:
        return error('知识库不存在', 404)

    kb.status = 0
    db.session.commit()
    return success(message='删除成功')
