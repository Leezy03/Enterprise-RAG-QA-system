"""
BM25 lexical retrieval service.

This module intentionally avoids an external tokenizer dependency. For mixed
Chinese/English enterprise documents it uses:
- English/number tokens for identifiers, model names, API names and values.
- Chinese unigram/bigram/trigram tokens for short factual queries.
"""
import math
import re
from collections import Counter, defaultdict


class BM25Service:
    """Small in-memory BM25 implementation for Chroma collection candidates."""

    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.stop_chars = set(
            '的是了和与及或在对中为个项可需应按将把吗么什哪些是否以及一个这个那个'
        )

    def tokenize(self, text):
        """
        Tokenize mixed Chinese/English text.
        Returns a list because BM25 needs term frequency, not only set overlap.
        """
        text = (text or '').lower()
        terms = []

        mixed_terms = re.findall(
            r'[a-z0-9_]+[\u4e00-\u9fff]{1,3}|[\u4e00-\u9fff]{1,3}[a-z0-9_]+',
            text
        )
        terms.extend(mixed_terms)

        english_terms = re.findall(r'[a-z0-9_]+(?:[./:_-][a-z0-9_]+)*', text)
        for term in english_terms:
            terms.append(term)
            parts = [part for part in re.split(r'[./:_-]+', term) if part]
            if len(parts) > 1:
                terms.extend(parts)

        chinese_sequences = re.findall(r'[\u4e00-\u9fff]+', text)
        for sequence in chinese_sequences:
            chars = [char for char in sequence if char not in self.stop_chars]
            terms.extend(chars)
            for n in (2, 3):
                terms.extend(
                    ''.join(chars[index:index + n])
                    for index in range(len(chars) - n + 1)
                )

        return [term for term in terms if term]

    def _build_index(self, tokenized_docs):
        """Build BM25 document statistics from tokenized documents."""
        doc_freqs = defaultdict(int)
        doc_lens = []
        doc_counters = []

        for tokens in tokenized_docs:
            counter = Counter(tokens)
            doc_counters.append(counter)
            doc_lens.append(len(tokens))
            for term in counter:
                doc_freqs[term] += 1

        doc_count = len(tokenized_docs)
        avg_doc_len = sum(doc_lens) / doc_count if doc_count else 0
        idf = {
            term: math.log(1 + (doc_count - freq + 0.5) / (freq + 0.5))
            for term, freq in doc_freqs.items()
        }
        return doc_counters, doc_lens, avg_doc_len, idf

    def _score_doc(self, query_terms, doc_counter, doc_len, avg_doc_len, idf):
        """Compute BM25 score for one document."""
        if not query_terms or not doc_len or not avg_doc_len:
            return 0

        score = 0
        for term in query_terms:
            freq = doc_counter.get(term, 0)
            if freq <= 0:
                continue
            denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / avg_doc_len)
            score += idf.get(term, 0) * (freq * (self.k1 + 1)) / denominator
        return score

    def rank(self, query, documents, top_k):
        """
        Rank documents with BM25.

        :param query: user query
        :param documents: list of dicts with content, search_text and metadata
        :param top_k: number of documents to return
        :return: ranked result dictionaries
        """
        query_terms = list(dict.fromkeys(self.tokenize(query)))
        if not query_terms or not documents:
            return []

        tokenized_docs = [
            self.tokenize(item.get('search_text') or item.get('content') or '')
            for item in documents
        ]
        doc_counters, doc_lens, avg_doc_len, idf = self._build_index(tokenized_docs)

        scored = []
        for index, item in enumerate(documents):
            score = self._score_doc(
                query_terms,
                doc_counters[index],
                doc_lens[index],
                avg_doc_len,
                idf
            )
            if score <= 0:
                continue

            matched_terms = sorted(set(query_terms) & set(doc_counters[index].keys()))
            scored.append({
                'index': index,
                'content': item.get('content') or '',
                'metadata': dict(item.get('metadata') or {}),
                'bm25_score_raw': score,
                'bm25_query_terms': len(query_terms),
                'bm25_matched_terms': len(matched_terms),
                'bm25_matched_keywords': ','.join(matched_terms[:20])
            })

        scored.sort(key=lambda item: item['bm25_score_raw'], reverse=True)
        top_results = scored[:top_k]
        max_score = top_results[0]['bm25_score_raw'] if top_results else 0

        for item in top_results:
            item['bm25_score'] = item['bm25_score_raw'] / max_score if max_score > 0 else 0

        return top_results
