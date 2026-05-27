"""
轻量级检索结果重排服务。
融合RRF混合检索分、向量相似度、关键词覆盖和文件名命中，对初始召回片段进行二次排序。
"""
import re


class RerankService:
    """对混合召回结果进行轻量级相关性重排"""

    def __init__(self, hybrid_weight=0.4, vector_weight=0.3, keyword_weight=0.25, filename_weight=0.05):
        self.hybrid_weight = hybrid_weight
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.filename_weight = filename_weight

    def _normalize(self, text):
        """基础文本归一化"""
        return (text or '').lower().strip()

    def _extract_terms(self, text):
        """
        提取中英文混合关键词。
        中文按单字和bigram混合切分，英文/数字按词切分，避免额外依赖分词库。
        """
        text = self._normalize(text)
        terms = set(re.findall(r'[a-z0-9_]+', text))

        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        stop_chars = set('的是了和与及或在对中为个项可需应按将把')
        filtered_chars = [char for char in chinese_chars if char not in stop_chars]
        terms.update(filtered_chars)
        terms.update(
            ''.join(filtered_chars[i:i + 2])
            for i in range(len(filtered_chars) - 1)
        )

        return {term for term in terms if term}

    def _keyword_score(self, query, content):
        """计算查询词在片段中的覆盖情况"""
        query_terms = self._extract_terms(query)
        if not query_terms:
            return 0

        content_terms = self._extract_terms(content)
        overlap = query_terms & content_terms
        return len(overlap) / len(query_terms)

    def _phrase_bonus(self, query, content):
        """对完整短语或较长连续片段命中做轻微加分"""
        query = self._normalize(query)
        content = self._normalize(content)
        if not query or not content:
            return 0
        if query in content:
            return 1

        compact_query = re.sub(r'\s+', '', query)
        compact_content = re.sub(r'\s+', '', content)
        if len(compact_query) >= 4 and compact_query in compact_content:
            return 0.8

        return 0

    def _filename_score(self, query, file_name):
        """文件名命中可帮助制度、规范、手册类问题排序"""
        return self._keyword_score(query, file_name)

    def _to_unit_score(self, value, default=0):
        """把分数字段转换到0-1区间。"""
        try:
            score = float(value)
        except (TypeError, ValueError):
            return default
        return max(0, min(score, 1))

    def _normalize_hybrid_scores(self, docs):
        """
        对RRF hybrid_score做候选集内归一化。
        RRF原始分通常很小，不能直接与vector/keyword分数加权。
        """
        raw_scores = []
        for doc in docs:
            metadata = doc.metadata or {}
            try:
                raw_scores.append(float(metadata.get('hybrid_score')))
            except (TypeError, ValueError):
                raw_scores.append(0)

        if not raw_scores:
            return {}

        max_score = max(raw_scores)
        min_score = min(raw_scores)
        if max_score <= 0:
            return {index: 0 for index in range(len(docs))}
        if max_score == min_score:
            return {index: 1 for index in range(len(docs))}

        return {
            index: (score - min_score) / (max_score - min_score)
            for index, score in enumerate(raw_scores)
        }

    def _combined_score(self, hybrid_score, vector_score, keyword_score, filename_score):
        """计算最终轻量重排分数。"""
        score = (
            self.hybrid_weight * hybrid_score
            + self.vector_weight * vector_score
            + self.keyword_weight * keyword_score
            + self.filename_weight * filename_score
        )
        return round(max(0, min(score, 1)), 4)

    def score(self, query, doc):
        """
        计算单个文档片段的重排分数
        :param query: 检索问题
        :param doc: LangChain Document
        :return: 0-1之间的相关性分数
        """
        metadata = doc.metadata or {}
        hybrid_score = self._to_unit_score(metadata.get('hybrid_score_norm'))
        vector_score = self._to_unit_score(metadata.get('vector_score', metadata.get('relevance_score', 0)))

        content = doc.page_content or ''
        file_name = metadata.get('file_name', '')
        keyword_score = self._keyword_score(query, content)
        phrase_bonus = self._phrase_bonus(query, content) * 0.1
        filename_score = self._filename_score(query, file_name)

        return self._combined_score(
            hybrid_score,
            vector_score,
            min(1, keyword_score + phrase_bonus),
            filename_score
        )

    def rerank(self, query, docs, top_k):
        """
        对召回片段重排并返回TopK
        :param query: 检索问题
        :param docs: 初始召回片段
        :param top_k: 返回数量
        """
        if not docs:
            return []

        reranked = []
        hybrid_score_norms = self._normalize_hybrid_scores(docs)

        for index, doc in enumerate(docs):
            metadata = dict(doc.metadata or {})
            hybrid_score = self._to_unit_score(hybrid_score_norms.get(index))
            vector_score = self._to_unit_score(metadata.get('vector_score', metadata.get('relevance_score', 0)))

            content = doc.page_content or ''
            file_name = metadata.get('file_name', '')
            keyword_score = min(1, self._keyword_score(query, content) + self._phrase_bonus(query, content) * 0.1)
            filename_score = self._filename_score(query, file_name)
            rerank_score = self._combined_score(hybrid_score, vector_score, keyword_score, filename_score)

            metadata['hybrid_score_norm'] = round(hybrid_score, 4)
            metadata['keyword_score'] = round(keyword_score, 4)
            metadata['filename_score'] = round(filename_score, 4)
            metadata['rerank_score'] = rerank_score
            metadata['rerank_backend'] = 'lightweight'
            metadata['rerank_enabled'] = True
            doc.metadata = metadata
            reranked.append(doc)

        reranked.sort(key=lambda item: item.metadata.get('rerank_score', 0), reverse=True)
        return reranked[:top_k]
