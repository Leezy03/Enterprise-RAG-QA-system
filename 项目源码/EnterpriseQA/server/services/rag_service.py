"""
RAG问答核心服务
基于LangChain构建检索增强生成（RAG）问答链
使用Ollama的qwen3:4b作为大语言模型
"""
from flask import current_app
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from models import db
from models.document import Document
from services.vector_service import VectorService


# RAG系统提示词模板
SYSTEM_PROMPT = """你是一个企业内部知识库RAG问答助手。请根据以下提供的参考资料和必要的对话历史回答用户问题。

要求：
1. 优先依据参考资料回答，不要编造参考资料中不存在的信息
2. 如果参考资料不足以回答，请明确说明“知识库中未找到足够依据”
3. 回答要准确、简洁、专业
4. 使用中文回答
5. 不要在回答正文中添加来源编号、引用标记或花括号标记，参考来源会由前端单独展示

对话历史：
{history}

参考资料：
{context}
"""

# 用户提问模板
USER_PROMPT = "{question}"

# 多轮问题改写模板
QUERY_REWRITE_PROMPT = """请根据对话历史，将用户最新问题改写为一个适合知识库检索的独立问题。

要求：
1. 只输出改写后的问题，不要解释
2. 如果最新问题本身已经完整，直接原样输出
3. 不要引入对话历史中不存在的新信息

对话历史：
{history}

最新问题：
{question}
"""


class RAGService:
    """RAG问答服务类"""

    def __init__(self):
        """初始化LLM模型和向量服务"""
        self.llm = ChatOllama(
            model=current_app.config['OLLAMA_LLM_MODEL'],
            base_url=current_app.config['OLLAMA_BASE_URL'],
            temperature=0.3,
            timeout=3600
        )
        self.vector_service = VectorService()

    def _to_int(self, value):
        """安全转换整数，用于兼容Chroma返回的metadata类型。"""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _clean_preview(self, text, limit=300):
        """生成适合前端展示的来源片段摘要。"""
        preview = ' '.join((text or '').split())
        if len(preview) <= limit:
            return preview
        return preview[:limit].rstrip() + '...'

    def _score_from_metadata(self, metadata):
        """按可信优先级提取最终展示分数。"""
        for field in ('rerank_score', 'hybrid_score', 'bm25_score', 'relevance_score', 'vector_score'):
            score = metadata.get(field)
            if isinstance(score, (int, float)):
                return score
        return None

    def _format_chunk_label(self, metadata):
        """把chunk索引转成用户可读的片段编号。"""
        chunk_index = self._to_int(metadata.get('chunk_index'))
        if chunk_index is None:
            return '片段未知'
        return f'片段{chunk_index + 1}'

    def _build_source_location(self, metadata):
        """根据文件类型metadata生成统一的来源位置描述。"""
        parts = []
        file_type = metadata.get('file_type')

        page_number = self._to_int(metadata.get('page_number'))
        if file_type == 'pdf' and page_number:
            parts.append(f'第{page_number}页')

        header_path = metadata.get('header_path')
        if header_path:
            parts.append(str(header_path))

        section_title = metadata.get('section_title')
        section_index = self._to_int(metadata.get('section_index'))
        if section_title:
            parts.append(f'章节：{section_title}')
        elif file_type == 'docx' and section_index:
            parts.append(f'第{section_index}节')

        paragraph_start = self._to_int(metadata.get('paragraph_start'))
        paragraph_end = self._to_int(metadata.get('paragraph_end'))
        if paragraph_start and paragraph_end:
            if paragraph_start == paragraph_end:
                parts.append(f'第{paragraph_start}段')
            else:
                parts.append(f'第{paragraph_start}-{paragraph_end}段')

        char_start = self._to_int(metadata.get('char_start'))
        char_end = self._to_int(metadata.get('char_end'))
        if char_start is not None and char_end is not None:
            parts.append(f'字符{char_start}-{char_end}')

        if not parts:
            parts.append(self._format_chunk_label(metadata))

        return ' / '.join(parts)

    def _build_source_label(self, source_id, file_name, metadata):
        """生成前端可直接展示的来源标签。"""
        location = self._build_source_location(metadata)
        chunk_label = self._format_chunk_label(metadata)
        if location and location != chunk_label:
            return f'{source_id}｜《{file_name}》｜{location}｜{chunk_label}'
        return f'{source_id}｜《{file_name}》｜{chunk_label}'

    def _format_docs(self, docs):
        """
        将检索到的文档格式化为上下文文本
        :param docs: 检索到的文档列表
        :return: 格式化后的文本
        """
        formatted = []
        for i, doc in enumerate(docs, 1):
            metadata = doc.metadata or {}
            source = metadata.get('file_name') or metadata.get('stored_file_name') or '未知来源'
            source_id = f'来源{i}'
            source_label = self._build_source_label(source_id, source, metadata)
            formatted.append(f"[{source_label}]\n{doc.page_content}")
        return '\n\n'.join(formatted)

    def _format_history(self, history):
        """
        将会话历史格式化为简短上下文
        :param history: 历史问答列表
        :return: 格式化后的历史文本
        """
        if not history:
            return '无'

        lines = []
        for item in history:
            question = item.get('question', '').strip()
            answer = item.get('answer', '').strip()
            if not question or not answer:
                continue
            lines.append(f"用户：{question}\n助手：{answer[:300]}")

        return '\n\n'.join(lines) if lines else '无'

    def _rewrite_question(self, question, history):
        """
        使用最近对话历史把省略指代类问题改写为独立检索问题
        :param question: 用户最新问题
        :param history: 历史问答列表
        :return: 适合向量检索的问题
        """
        if not history:
            return question

        history_text = self._format_history(history)
        prompt = ChatPromptTemplate.from_template(QUERY_REWRITE_PROMPT)
        rewrite_chain = prompt | self.llm | StrOutputParser()

        try:
            rewritten = rewrite_chain.invoke({
                'history': history_text,
                'question': question
            }).strip()
            return rewritten or question
        except Exception as e:
            current_app.logger.warning(f'多轮问题改写失败，使用原始问题检索: {e}')
            return question

    def _extract_source_docs(self, docs):
        """
        提取参考文档来源信息
        :param docs: 检索到的文档列表
        :return: 来源信息列表
        """
        doc_ids = set()
        for doc in docs:
            doc_id = (doc.metadata or {}).get('doc_id')
            if doc_id is not None:
                try:
                    doc_ids.add(int(doc_id))
                except (TypeError, ValueError):
                    pass

        document_names = {}
        if doc_ids:
            try:
                document_names = {
                    item.id: item.file_name
                    for item in Document.query.filter(Document.id.in_(doc_ids)).all()
                }
            except Exception as e:
                db.session.rollback()
                current_app.logger.warning(f'查询文档名称失败，使用向量库metadata中的文件名: {e}')

        sources = []
        seen = set()
        for doc in docs:
            metadata = doc.metadata or {}
            raw_doc_id = metadata.get('doc_id')
            doc_id = None
            if raw_doc_id is not None:
                try:
                    doc_id = int(raw_doc_id)
                except (TypeError, ValueError):
                    pass

            file_name = (
                document_names.get(doc_id)
                or metadata.get('file_name')
                or metadata.get('stored_file_name')
                or '未知文档'
            )
            chunk_index = metadata.get('chunk_index')
            key = (doc_id, file_name, chunk_index)
            if key not in seen:
                seen.add(key)
                source_id = f'来源{len(sources) + 1}'
                source_location = self._build_source_location(metadata)
                source_label = self._build_source_label(source_id, file_name, metadata)
                content_preview = self._clean_preview(doc.page_content)
                sources.append({
                    'source_id': source_id,
                    'source_label': source_label,
                    'source_location': source_location,
                    'file_name': file_name,
                    'doc_id': raw_doc_id,
                    'chunk_index': chunk_index,
                    'file_type': metadata.get('file_type'),
                    'source_doc_index': metadata.get('source_doc_index'),
                    'page_number': metadata.get('page_number'),
                    'header_path': metadata.get('header_path'),
                    'section_title': metadata.get('section_title'),
                    'section_index': metadata.get('section_index'),
                    'paragraph_start': metadata.get('paragraph_start'),
                    'paragraph_end': metadata.get('paragraph_end'),
                    'char_start': metadata.get('char_start'),
                    'char_end': metadata.get('char_end'),
                    'chunk_strategy': metadata.get('chunk_strategy'),
                    'chunk_size': metadata.get('chunk_size'),
                    'chunk_overlap': metadata.get('chunk_overlap'),
                    'score': self._score_from_metadata(metadata),
                    'relevance_score': metadata.get('relevance_score'),
                    'vector_score': metadata.get('vector_score'),
                    'vector_rank': metadata.get('vector_rank'),
                    'keyword_score': metadata.get('keyword_score'),
                    'keyword_search_score': metadata.get('keyword_search_score'),
                    'keyword_rank': metadata.get('keyword_rank'),
                    'keyword_backend': metadata.get('keyword_backend'),
                    'bm25_score': metadata.get('bm25_score'),
                    'bm25_score_raw': metadata.get('bm25_score_raw'),
                    'bm25_query_terms': metadata.get('bm25_query_terms'),
                    'bm25_matched_terms': metadata.get('bm25_matched_terms'),
                    'bm25_matched_keywords': metadata.get('bm25_matched_keywords'),
                    'rerank_score': metadata.get('rerank_score'),
                    'rerank_backend': metadata.get('rerank_backend'),
                    'rerank_enabled': metadata.get('rerank_enabled'),
                    'hybrid_score': metadata.get('hybrid_score'),
                    'hybrid_enabled': metadata.get('hybrid_enabled'),
                    'retrieval_method': metadata.get('retrieval_method'),
                    'retrieval_sources': metadata.get('retrieval_sources'),
                    'content_preview': content_preview,
                    'content': content_preview
                })
        return sources

    def _prepare_rag_context(self, question, kb_id, history=None, use_rerank=None):
        """
        准备RAG回答所需的历史、检索问题、上下文片段和来源信息
        :param question: 用户问题
        :param kb_id: 知识库ID
        :param history: 最近几轮对话历史
        :param use_rerank: 是否启用重排
        :return: 上下文字典
        """
        history = history or []
        history_text = self._format_history(history)

        # 对多轮追问做独立问题改写，提升向量检索命中率
        retrieval_query = self._rewrite_question(question, history)

        # 先做向量召回，再按配置执行重排
        docs = self.vector_service.search(kb_id, retrieval_query, use_rerank=use_rerank)
        source_docs = self._extract_source_docs(docs)

        return {
            'docs': docs,
            'history_text': history_text,
            'retrieval_query': retrieval_query,
            'source_docs': source_docs
        }

    def _build_rag_chain(self, docs, history_text):
        """
        构建RAG生成链
        :param docs: 检索到的上下文片段
        :param history_text: 格式化后的对话历史
        :return: LangChain Runnable
        """
        prompt = ChatPromptTemplate.from_messages([
            ('system', SYSTEM_PROMPT),
            ('human', USER_PROMPT)
        ])

        return (
            {
                'context': lambda x: self._format_docs(docs),
                'history': lambda x: history_text,
                'question': RunnablePassthrough()
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def ask(self, question, kb_id, history=None):
        """
        RAG问答主方法
        流程: 多轮问题改写 -> 向量检索 -> 构建上下文 -> LLM生成回答
        :param question: 用户问题
        :param kb_id: 知识库ID
        :param history: 最近几轮对话历史
        :return: (回答文本, 参考来源列表, 实际检索问题)
        """
        context = self._prepare_rag_context(question, kb_id, history=history)
        docs = context['docs']
        retrieval_query = context['retrieval_query']

        if not docs:
            return '抱歉，在知识库中未找到与您问题相关的内容，请尝试换个方式提问。', [], retrieval_query

        # 执行问答
        rag_chain = self._build_rag_chain(docs, context['history_text'])
        answer = rag_chain.invoke(question)

        return answer, context['source_docs'], retrieval_query

    def stream_answer(self, question, kb_id, history=None):
        """
        RAG问答流式生成
        :param question: 用户问题
        :param kb_id: 知识库ID
        :param history: 最近几轮对话历史
        :return: (文本流, 参考来源列表, 实际检索问题)
        """
        context = self._prepare_rag_context(question, kb_id, history=history)
        docs = context['docs']

        if not docs:
            fallback = '抱歉，在知识库中未找到与您问题相关的内容，请尝试换个方式提问。'
            return iter([fallback]), [], context['retrieval_query']

        rag_chain = self._build_rag_chain(docs, context['history_text'])
        return rag_chain.stream(question), context['source_docs'], context['retrieval_query']

    def retrieve_for_eval(self, question, kb_id, top_k=None, use_rerank=True):
        """
        供评测脚本使用的检索接口，避免触发LLM生成
        :param question: 评测问题
        :param kb_id: 知识库ID
        :param top_k: 返回数量
        :param use_rerank: 是否启用重排
        :return: 检索片段列表
        """
        return self.vector_service.search(
            kb_id,
            question,
            top_k=top_k,
            use_rerank=use_rerank
        )
