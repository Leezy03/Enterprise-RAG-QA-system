"""
轻量级检索结果重排服务
融合向量相似度、关键词覆盖和短语命中，对初始召回片段进行二次排序。
"""
import re


class RerankService:
    """对向量召回结果进行轻量级相关性重排"""

    def __init__(self, vector_weight=0.65, keyword_weight=0.3, filename_weight=0.05):
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

    def score(self, query, doc):
        """
        计算单个文档片段的重排分数
        :param query: 检索问题
        :param doc: LangChain Document
        :return: 0-1之间的相关性分数
        """
        metadata = doc.metadata or {}
        vector_score = metadata.get('vector_score', metadata.get('relevance_score', 0))
        try:
            vector_score = float(vector_score)
        except (TypeError, ValueError):
            vector_score = 0
        vector_score = max(0, min(vector_score, 1))

        content = doc.page_content or ''
        file_name = metadata.get('file_name', '')
        keyword_score = self._keyword_score(query, content)
        phrase_bonus = self._phrase_bonus(query, content) * 0.1
        filename_score = self._filename_score(query, file_name)

        score = (
            self.vector_weight * vector_score
            + self.keyword_weight * min(1, keyword_score + phrase_bonus)
            + self.filename_weight * filename_score
        )
        return round(max(0, min(score, 1)), 4)

    def rerank(self, query, docs, top_k):
        """
        对召回片段重排并返回TopK
        :param query: 检索问题
        :param docs: 初始召回片段
        :param top_k: 返回数量
        """
        reranked = []
        for doc in docs:
            metadata = dict(doc.metadata or {})
            vector_score = metadata.get('vector_score', metadata.get('relevance_score', 0))
            try:
                vector_score = float(vector_score)
            except (TypeError, ValueError):
                vector_score = 0
            vector_score = max(0, min(vector_score, 1))

            content = doc.page_content or ''
            file_name = metadata.get('file_name', '')
            keyword_score = min(1, self._keyword_score(query, content) + self._phrase_bonus(query, content) * 0.1)
            filename_score = self._filename_score(query, file_name)
            rerank_score = (
                self.vector_weight * vector_score
                + self.keyword_weight * keyword_score
                + self.filename_weight * filename_score
            )

            metadata['keyword_score'] = round(keyword_score, 4)
            metadata['rerank_score'] = round(max(0, min(rerank_score, 1)), 4)
            metadata['rerank_enabled'] = True
            doc.metadata = metadata
            reranked.append(doc)

        reranked.sort(key=lambda item: item.metadata.get('rerank_score', 0), reverse=True)
        return reranked[:top_k]
