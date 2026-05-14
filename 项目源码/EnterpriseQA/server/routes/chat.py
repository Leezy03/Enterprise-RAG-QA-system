"""
问答对话路由
提供RAG问答和对话历史查询接口
"""
import uuid
import json
from flask import Blueprint, Response, request, g, current_app, stream_with_context
from models import db
from models.chat_history import ChatHistory
from models.knowledge_base import KnowledgeBase
from utils.auth import login_required
from utils.response import success, error, page_response

# 创建问答蓝图
chat_bp = Blueprint('chat', __name__)


def _sse(event, data):
    """
    格式化Server-Sent Events消息
    :param event: 事件名
    :param data: JSON可序列化数据
    :return: SSE文本
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f'event: {event}\ndata: {payload}\n\n'


def _load_recent_history(session_id, kb_id):
    """
    读取当前用户在同一会话中的最近几轮问答，用于多轮RAG问题改写
    :param session_id: 会话ID
    :param kb_id: 知识库ID
    :return: 历史问答列表
    """
    history_turns = current_app.config.get('RAG_HISTORY_TURNS', 3)
    if history_turns <= 0:
        return []

    records = (
        ChatHistory.query
        .filter_by(user_id=g.user_id, session_id=session_id, kb_id=kb_id)
        .order_by(ChatHistory.create_time.desc())
        .limit(history_turns)
        .all()
    )
    records.reverse()

    return [
        {
            'question': item.question,
            'answer': item.answer
        }
        for item in records
    ]


@chat_bp.route('/ask', methods=['POST'])
@login_required
def ask():
    """
    RAG知识库问答接口
    请求参数: question(问题), kb_id(知识库ID), session_id(会话ID，可选)
    返回: AI回答和参考来源
    """
    data = request.get_json()
    if not data:
        return error('请提供问题信息')

    question = data.get('question', '').strip()
    kb_id = data.get('kb_id')
    session_id = data.get('session_id', str(uuid.uuid4().hex[:16]))

    if not question:
        return error('问题不能为空')
    if not kb_id:
        return error('请选择知识库')

    # 验证知识库是否存在
    kb = KnowledgeBase.query.get(kb_id)
    if not kb or kb.status != 1:
        return error('知识库不存在或已禁用')

    # 调用RAG服务进行问答
    try:
        from services.rag_service import RAGService
        rag_service = RAGService()
        history = _load_recent_history(session_id, kb_id)
        answer, source_docs, retrieval_query = rag_service.ask(question, kb_id, history=history)
    except Exception as e:
        return error(f'问答服务异常: {str(e)}')

    # 保存对话记录
    chat = ChatHistory(
        user_id=g.user_id,
        kb_id=kb_id,
        session_id=session_id,
        question=question,
        answer=answer,
        source_docs=json.dumps(source_docs, ensure_ascii=False)
    )
    db.session.add(chat)
    db.session.commit()

    return success({
        'answer': answer,
        'source_docs': source_docs,
        'retrieval_query': retrieval_query,
        'session_id': session_id,
        'chat_id': chat.id
    })


@chat_bp.route('/ask_stream', methods=['POST'])
@login_required
def ask_stream():
    """
    RAG知识库问答流式接口
    通过SSE分段返回LLM生成内容，完成后返回来源和会话信息
    """
    data = request.get_json()
    if not data:
        return error('请提供问题信息')

    question = data.get('question', '').strip()
    kb_id = data.get('kb_id')
    session_id = data.get('session_id', str(uuid.uuid4().hex[:16]))

    if not question:
        return error('问题不能为空')
    if not kb_id:
        return error('请选择知识库')

    kb = KnowledgeBase.query.get(kb_id)
    if not kb or kb.status != 1:
        return error('知识库不存在或已禁用')

    user_id = g.user_id
    history = _load_recent_history(session_id, kb_id)

    @stream_with_context
    def generate():
        full_answer = ''
        source_docs = []
        retrieval_query = question

        try:
            from services.rag_service import RAGService
            rag_service = RAGService()
            answer_stream, source_docs, retrieval_query = rag_service.stream_answer(
                question,
                kb_id,
                history=history
            )

            yield _sse('meta', {
                'session_id': session_id,
                'retrieval_query': retrieval_query
            })

            for chunk in answer_stream:
                text = str(chunk or '')
                if not text:
                    continue
                full_answer += text
                yield _sse('chunk', {'content': text})

            chat = ChatHistory(
                user_id=user_id,
                kb_id=kb_id,
                session_id=session_id,
                question=question,
                answer=full_answer,
                source_docs=json.dumps(source_docs, ensure_ascii=False)
            )
            db.session.add(chat)
            db.session.commit()

            yield _sse('done', {
                'answer': full_answer,
                'source_docs': source_docs,
                'retrieval_query': retrieval_query,
                'session_id': session_id,
                'chat_id': chat.id
            })
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('流式问答服务异常')
            yield _sse('error', {'message': f'问答服务异常: {str(e)}'})

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@chat_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """
    获取对话历史列表（分页）
    查询参数: page, page_size, kb_id(可选)
    普通用户只能查看自己的记录，管理员可查看所有
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    kb_id = request.args.get('kb_id', type=int)

    query = ChatHistory.query

    # 普通用户只能查看自己的对话记录
    if g.role != 'admin':
        query = query.filter_by(user_id=g.user_id)

    if kb_id:
        query = query.filter_by(kb_id=kb_id)

    query = query.order_by(ChatHistory.create_time.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    items = [item.to_dict() for item in pagination.items]
    return page_response(items, pagination.total, page, page_size)


@chat_bp.route('/session/<session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """
    获取指定会话的所有对话记录
    路径参数: session_id(会话ID)
    """
    query = ChatHistory.query.filter_by(session_id=session_id)

    # 普通用户只能查看自己的对话
    if g.role != 'admin':
        query = query.filter_by(user_id=g.user_id)

    chats = query.order_by(ChatHistory.create_time.asc()).all()
    return success([chat.to_dict() for chat in chats])
