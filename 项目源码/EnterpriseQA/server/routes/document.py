"""
文档路由
提供文档上传、列表查询和删除接口
"""
import os
import uuid
from flask import Blueprint, request, g, current_app
from models import db
from models.document import Document
from models.knowledge_base import KnowledgeBase
from utils.auth import login_required, admin_required
from utils.response import success, error, page_response

# 创建文档蓝图
doc_bp = Blueprint('document', __name__)


def allowed_file(filename):
    """检查文件扩展名是否允许上传"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def refresh_kb_doc_count(kb_id):
    """刷新知识库中已向量化文档数量"""
    kb = KnowledgeBase.query.get(kb_id)
    if kb:
        kb.doc_count = Document.query.filter_by(kb_id=kb_id, status='vectorized').count()
    return kb


def vectorize_existing_document(doc):
    """
    对已存在的文档记录执行向量化。
    该函数用于上传后首次向量化，也用于重新向量化。
    """
    from services.vector_service import VectorService

    vector_service = VectorService()
    chunk_count = vector_service.process_document(
        doc.id,
        doc.file_path,
        doc.file_type,
        doc.kb_id,
        original_file_name=doc.file_name
    )

    doc.status = 'vectorized'
    doc.chunk_count = chunk_count
    refresh_kb_doc_count(doc.kb_id)
    db.session.commit()
    return chunk_count


@doc_bp.route('/list', methods=['GET'])
@login_required
def get_list():
    """
    获取文档列表（分页）
    查询参数: page, page_size, kb_id
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    kb_id = request.args.get('kb_id', type=int)

    query = Document.query
    if kb_id:
        query = query.filter_by(kb_id=kb_id)

    query = query.order_by(Document.create_time.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@doc_bp.route('/upload', methods=['POST'])
@admin_required
def upload():
    """
    上传文档并进行向量化处理（仅管理员）
    表单参数: file（文件）, kb_id（知识库ID）
    """
    if 'file' not in request.files:
        return error('请选择要上传的文件')

    file = request.files['file']
    kb_id = request.form.get('kb_id', type=int)

    if not kb_id:
        return error('请选择知识库')

    if file.filename == '':
        return error('请选择要上传的文件')

    if not allowed_file(file.filename):
        return error(f"不支持的文件类型，仅支持: {', '.join(current_app.config['ALLOWED_EXTENSIONS'])}")

    # 验证知识库是否存在
    kb = KnowledgeBase.query.get(kb_id)
    if not kb:
        return error('知识库不存在')

    # 生成唯一文件名并保存
    file_ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{file_ext}"
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
    file.save(file_path)

    # 获取文件大小
    file_size = os.path.getsize(file_path)

    # 创建文档记录
    doc = Document(
        kb_id=kb_id,
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file_ext,
        creator_id=g.user_id
    )
    db.session.add(doc)
    db.session.commit()

    # 进行文档向量化处理
    try:
        from services.vector_service import OllamaServiceError
        vectorize_existing_document(doc)
    except OllamaServiceError as e:
        doc.status = 'failed'
        db.session.commit()
        return error(str(e))
    except ConnectionError:
        doc.status = 'failed'
        db.session.commit()
        return error('无法连接Ollama服务，请确认Ollama已启动并可访问')
    except Exception as e:
        doc.status = 'failed'
        db.session.commit()
        err_msg = str(e)
        if 'status code' in err_msg:
            return error(f'Ollama服务处理异常，请检查Ollama运行状态和系统资源: {err_msg}')
        return error(f'文档向量化失败: {err_msg}')

    return success(doc.to_dict(), '上传成功')


@doc_bp.route('/<int:doc_id>/revectorize', methods=['POST'])
@admin_required
def revectorize(doc_id):
    """
    重新向量化文档。
    适用于调整chunk策略、source tracking、embedding模型后，对已有文件重新入库。
    """
    doc = Document.query.get(doc_id)
    if not doc:
        return error('文档不存在', 404)

    kb = KnowledgeBase.query.get(doc.kb_id)
    if not kb:
        return error('知识库不存在', 404)

    if not os.path.exists(doc.file_path):
        doc.status = 'failed'
        db.session.commit()
        return error('原始文件不存在，无法重新向量化')

    try:
        from services.vector_service import VectorService, OllamaServiceError

        doc.status = 'uploading'
        db.session.commit()

        vector_service = VectorService()
        vector_service.delete_document(doc.id, doc.kb_id)
        chunk_count = vectorize_existing_document(doc)

        return success({
            **doc.to_dict(),
            'chunk_count': chunk_count
        }, '重新向量化成功')
    except OllamaServiceError as e:
        doc.status = 'failed'
        db.session.commit()
        return error(str(e))
    except ConnectionError:
        doc.status = 'failed'
        db.session.commit()
        return error('无法连接Ollama服务，请确认Ollama已启动并可访问')
    except Exception as e:
        doc.status = 'failed'
        refresh_kb_doc_count(doc.kb_id)
        db.session.commit()
        err_msg = str(e)
        if 'status code' in err_msg:
            return error(f'Ollama服务处理异常，请检查Ollama运行状态和系统资源: {err_msg}')
        return error(f'重新向量化失败: {err_msg}')


@doc_bp.route('/<int:doc_id>', methods=['DELETE'])
@admin_required
def delete(doc_id):
    """
    删除文档（仅管理员）
    同时删除对应的向量数据和物理文件
    """
    doc = Document.query.get(doc_id)
    if not doc:
        return error('文档不存在', 404)

    kb_id = doc.kb_id

    # 删除向量数据
    try:
        from services.vector_service import VectorService
        vector_service = VectorService()
        vector_service.delete_document(doc.id, kb_id)
    except Exception:
        pass

    # 删除物理文件
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # 删除数据库记录
    db.session.delete(doc)

    # 更新知识库文档计数
    refresh_kb_doc_count(kb_id)

    db.session.commit()
    return success(message='删除成功')
