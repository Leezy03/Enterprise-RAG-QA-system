"""
RAG检索评测脚本。

默认模式：
    对比现有向量库上的 baseline 检索与 rerank 检索。

切分策略对比模式：
    为每个chunk策略创建临时Chroma collection，重新索引同一批文档，
    再用同一评测集对比不同chunk size / overlap 的检索效果。

运行方式：
    python evaluation/evaluate_rag.py
    python evaluation/evaluate_rag.py --compare-chunk-strategies
    python evaluation/evaluate_rag.py --compare-chunk-strategies --chunk-strategy-file evaluation/chunk_strategy_presets.example.json
"""
import argparse
import csv
import copy
import json
import logging
import math
import os
import re
import sys
import uuid
from pathlib import Path

os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')
logging.getLogger('chromadb.telemetry.product.posthog').disabled = True


SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from flask import current_app  # noqa: E402

from app import create_app  # noqa: E402
from models import db  # noqa: E402
from models.document import Document  # noqa: E402
from models.knowledge_base import KnowledgeBase  # noqa: E402
from services.rag_service import RAGService  # noqa: E402
from services.vector_service import VectorService  # noqa: E402


DEFAULT_DATASET = Path(__file__).with_name('rag_eval_set.json')
DEFAULT_OUTPUT_DIR = Path(__file__).with_name('results')
ANSWER_HIT_THRESHOLD = 0.67
NO_ANSWER_REFUSAL_PATTERNS = (
    '未找到',
    '没有找到',
    '不足以回答',
    '无法回答',
    '无法确定',
    '不清楚',
    '不知道',
    '抱歉',
    '知识库中未找到',
    '知识库中没有'
)
TEXT_STOP_TERMS = {
    '的', '是', '了', '和', '与', '及', '或', '在', '对', '中', '为', '个',
    '项', '可', '需', '应', '按', '将', '把', '吗', '么', '什', '哪些',
    '是否', '以及', '一个', '这个', '那个', '需要', '什么', '怎么', '如何'
}

DEFAULT_CHUNK_STRATEGY_PRESETS = [
    {
        'name': 'current',
        'description': '使用config.py/.env中的当前切分配置',
        'chunk_strategies': None
    },
    {
        'name': 'small_chunks',
        'description': '更小的chunk，偏向精准召回，embedding成本更高',
        'chunk_strategies': {
            'txt': {'chunk_size': 350, 'chunk_overlap': 60},
            'pdf': {'chunk_size': 350, 'chunk_overlap': 80},
            'md': {'chunk_size': 500, 'chunk_overlap': 80},
            'docx': {'chunk_size': 500, 'chunk_overlap': 80}
        }
    },
    {
        'name': 'large_chunks',
        'description': '更大的chunk，偏向保留上下文，可能降低精准度',
        'chunk_strategies': {
            'txt': {'chunk_size': 800, 'chunk_overlap': 100},
            'pdf': {'chunk_size': 700, 'chunk_overlap': 120},
            'md': {'chunk_size': 1200, 'chunk_overlap': 150},
            'docx': {'chunk_size': 1000, 'chunk_overlap': 150}
        }
    }
]


def load_dataset(path):
    """加载评测集。"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_filter_values(value):
    """解析逗号分隔的评测样本过滤值。"""
    if not value:
        return None
    values = {
        part.strip()
        for part in str(value).split(',')
        if part.strip()
    }
    return values or None


def filter_dataset(dataset, args):
    """按样本类型过滤评测集，便于低成本运行生成级评测。"""
    category_filter = parse_filter_values(getattr(args, 'filter_category', None))
    dimension_filter = parse_filter_values(getattr(args, 'filter_dimension', None))
    type_filter = parse_filter_values(getattr(args, 'filter_type', None))

    filtered = []
    for item in dataset:
        if category_filter and item.get('category') not in category_filter:
            continue
        if dimension_filter and item.get('eval_dimension') not in dimension_filter:
            continue
        if type_filter and item.get('type') not in type_filter:
            continue
        filtered.append(item)

    if not filtered:
        raise ValueError('过滤后评测集为空，请检查 --filter-category/--filter-dimension/--filter-type')
    return filtered


def round_metric(value, digits=4):
    """统一处理指标保留位数；None表示当前样本不适用。"""
    if value is None:
        return None
    return round(float(value), digits)


def safe_divide(numerator, denominator, default=0):
    """安全除法。"""
    if not denominator:
        return default
    return numerator / denominator


def normalize_text(value):
    """评测用文本归一化，避免大小写和空白影响简单匹配。"""
    return re.sub(r'\s+', '', str(value or '').lower())


def keyword_coverage_in_text(text, expected_keywords):
    """计算一段文本对预期关键词的覆盖比例。"""
    if not expected_keywords:
        return None

    normalized = normalize_text(text)
    if not normalized:
        return 0

    matched = 0
    for keyword in expected_keywords:
        if normalize_text(keyword) in normalized:
            matched += 1
    return matched / len(expected_keywords)


def extract_eval_terms(text):
    """
    提取评测用轻量terms。
    用于答案一致性和groundedness的启发式统计，不替代人工或LLM评审。
    """
    text = str(text or '').lower()
    terms = set(re.findall(r'[a-z0-9_]+(?:[./:_-][a-z0-9_]+)*', text))
    chinese_sequences = re.findall(r'[\u4e00-\u9fff]+', text)
    for sequence in chinese_sequences:
        chars = [char for char in sequence if char not in TEXT_STOP_TERMS]
        terms.update(char for char in chars if char not in TEXT_STOP_TERMS)
        terms.update(
            ''.join(chars[index:index + 2])
            for index in range(len(chars) - 1)
        )
    return {term for term in terms if term and term not in TEXT_STOP_TERMS}


def term_overlap_score(expected_text, actual_text):
    """计算actual_text覆盖expected_text中评测terms的比例。"""
    expected_terms = extract_eval_terms(expected_text)
    if not expected_terms:
        return None
    actual_terms = extract_eval_terms(actual_text)
    return len(expected_terms & actual_terms) / len(expected_terms)


def term_jaccard(left_text, right_text):
    """计算两段文本评测terms的Jaccard相似度。"""
    left_terms = extract_eval_terms(left_text)
    right_terms = extract_eval_terms(right_text)
    if not left_terms and not right_terms:
        return None
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def looks_like_refusal(answer):
    """判断回答是否像无答案拒答。"""
    normalized = normalize_text(answer)
    return any(normalize_text(pattern) in normalized for pattern in NO_ANSWER_REFUSAL_PATTERNS)


def is_no_answer_case(item):
    """识别无答案/拒答评测样本。"""
    if item.get('expected_answerable') is False:
        return True
    if item.get('expected_refusal') is True:
        return True
    return str(item.get('type', '')).lower() in {'no_answer', 'unanswerable', 'refusal'}


def resolve_kb_id(item):
    """根据评测样本中的kb_id或kb_name解析知识库ID。"""
    if item.get('kb_id'):
        return item['kb_id']

    kb_name = item.get('kb_name')
    if not kb_name:
        raise ValueError(f"评测样本 {item.get('id')} 缺少 kb_id 或 kb_name")

    kb = KnowledgeBase.query.filter_by(kb_name=kb_name, status=1).first()
    if not kb:
        raise ValueError(f"未找到可用知识库: {kb_name}")

    return kb.id


def get_document_name(doc_id):
    """根据文档ID获取原始文件名。"""
    if doc_id is None:
        return ''
    try:
        document = db.session.get(Document, int(doc_id))
    except (RuntimeError, TypeError, ValueError):
        document = None
    return document.file_name if document else ''


def source_names(doc):
    """收集一个检索片段可能对应的来源文件名。"""
    metadata = doc.metadata or {}
    names = {
        metadata.get('file_name', ''),
        metadata.get('stored_file_name', ''),
        get_document_name(metadata.get('doc_id'))
    }
    return {name for name in names if name}


def name_matches(actual, expected):
    """宽松比较文件名，兼容上传后的随机存储名和原始文件名。"""
    actual = normalize_text(actual)
    expected = normalize_text(expected)
    return bool(actual and expected and (actual == expected or actual in expected or expected in actual))


def matched_expected_sources(actual_names, expected_sources):
    """返回actual_names命中的预期来源集合。"""
    matched = set()
    for expected in expected_sources:
        if any(name_matches(actual, expected) for actual in actual_names):
            matched.add(expected)
    return matched


def source_hit(doc, expected_sources):
    """判断单个片段是否命中预期来源。"""
    return bool(matched_expected_sources(source_names(doc), expected_sources))


def first_hit_rank(docs, expected_sources):
    """返回第一个命中预期来源的排名，未命中返回None。"""
    for index, doc in enumerate(docs, 1):
        if source_hit(doc, expected_sources):
            return index
    return None


def retrieval_metrics(docs, expected_sources, expected_keywords, top_k):
    """计算检索级指标。"""
    top_docs = docs[:top_k]
    rank = first_hit_rank(top_docs, expected_sources)
    relevant_flags = [source_hit(doc, expected_sources) for doc in top_docs]
    relevant_count = sum(1 for flag in relevant_flags if flag)

    matched_sources = set()
    relevance_by_rank = []
    for doc in top_docs:
        current_matches = matched_expected_sources(source_names(doc), expected_sources)
        new_matches = current_matches - matched_sources
        relevance_by_rank.append(1 if new_matches else 0)
        matched_sources.update(new_matches)

    dcg = sum(
        relevance / math.log2(index + 2)
        for index, relevance in enumerate(relevance_by_rank)
    )
    ideal_relevance_count = min(len(expected_sources), len(top_docs))
    idcg = sum(1 / math.log2(index + 2) for index in range(ideal_relevance_count))

    return {
        'first_hit_rank': rank,
        'hit_at_k': bool(rank),
        'hit_at_1': rank == 1,
        'mrr': round_metric(1 / rank if rank else 0),
        'recall_at_k': round_metric(safe_divide(len(matched_sources), len(expected_sources))),
        'precision_at_k': round_metric(safe_divide(relevant_count, len(top_docs))),
        'ndcg_at_k': round_metric(safe_divide(dcg, idcg)),
        'keyword_coverage': round_metric(keyword_coverage(top_docs, expected_keywords)),
        'top1_keyword_coverage': round_metric(keyword_coverage(top_docs[:1], expected_keywords)),
        'matched_expected_sources': sorted(matched_sources)
    }


def keyword_coverage(docs, expected_keywords):
    """计算TopK片段对预期关键词的覆盖比例。"""
    if not expected_keywords:
        return None

    text = '\n'.join(doc.page_content or '' for doc in docs).lower()
    return keyword_coverage_in_text(text, expected_keywords)


def docs_to_citations(docs):
    """把检索片段转换为引用评测结构。"""
    citations = []
    for index, doc in enumerate(docs, 1):
        metadata = doc.metadata or {}
        citations.append({
            'rank': index,
            'file_names': sorted(source_names(doc)),
            'file_name': metadata.get('file_name') or metadata.get('stored_file_name') or '',
            'content': doc.page_content or '',
            'content_preview': ' '.join((doc.page_content or '').split())[:300],
            'source_label': metadata.get('source_label')
        })
    return citations


def source_docs_to_citations(source_docs):
    """把RAG生成接口返回的source_docs转换为引用评测结构。"""
    citations = []
    for index, source in enumerate(source_docs or [], 1):
        file_names = set()
        if source.get('file_name'):
            file_names.add(source['file_name'])
        if source.get('source_label'):
            file_names.add(source['source_label'])
        citations.append({
            'rank': index,
            'file_names': sorted(file_names),
            'file_name': source.get('file_name', ''),
            'content': source.get('content') or source.get('content_preview') or '',
            'content_preview': source.get('content_preview') or source.get('content') or '',
            'source_label': source.get('source_label')
        })
    return citations


def citation_metrics(citations, expected_sources, expected_keywords, answer=None):
    """计算引用级指标。"""
    if not citations:
        return {
            'citation_precision': 0 if expected_sources else None,
            'citation_recall': 0 if expected_sources else None,
            'citation_support': 0 if expected_keywords else None,
            'citation_answer_support': None
        }

    matched_sources = set()
    relevant_citations = 0
    for citation in citations:
        names = set(citation.get('file_names') or [])
        if citation.get('file_name'):
            names.add(citation['file_name'])
        matches = matched_expected_sources(names, expected_sources)
        if matches:
            relevant_citations += 1
            matched_sources.update(matches)

    citation_text = '\n'.join(
        citation.get('content') or citation.get('content_preview') or ''
        for citation in citations
    )
    return {
        'citation_precision': round_metric(safe_divide(relevant_citations, len(citations))) if expected_sources else None,
        'citation_recall': round_metric(safe_divide(len(matched_sources), len(expected_sources))) if expected_sources else None,
        'citation_support': round_metric(keyword_coverage_in_text(citation_text, expected_keywords)),
        'citation_answer_support': round_metric(answer_support_score(answer, citation_text)) if answer else None
    }


def answer_support_score(answer, support_text, question=''):
    """启发式groundedness：答案中的事实terms有多少能在上下文中找到。"""
    answer_terms = extract_eval_terms(answer)
    if not answer_terms:
        return None

    question_terms = extract_eval_terms(question)
    factual_terms = answer_terms - question_terms
    if not factual_terms:
        factual_terms = answer_terms

    support_terms = extract_eval_terms(support_text)
    return len(factual_terms & support_terms) / len(factual_terms)


def generation_metrics(answer, docs, item):
    """计算生成级指标。当前为启发式评估，可后续替换为LLM-as-Judge。"""
    if answer is None:
        return {
            'answer_correctness': None,
            'faithfulness': None,
            'groundedness': None,
            'completeness': None,
            'hallucination_rate': None,
            'refusal_detected': None
        }

    expected_keywords = item.get('expected_answer_keywords') or item.get('expected_keywords', [])
    correctness = keyword_coverage_in_text(answer, expected_keywords)
    completeness = correctness

    if item.get('expected_answer'):
        expected_answer_score = term_overlap_score(item['expected_answer'], answer)
        if correctness is None:
            correctness = expected_answer_score
        elif expected_answer_score is not None:
            correctness = (correctness + expected_answer_score) / 2

    support_text = '\n'.join(doc.page_content or '' for doc in docs)
    faithfulness = answer_support_score(answer, support_text, item.get('question', ''))
    hallucination_rate = None if faithfulness is None else 1 - faithfulness

    return {
        'answer_correctness': round_metric(correctness),
        'faithfulness': round_metric(faithfulness),
        'groundedness': round_metric(faithfulness),
        'completeness': round_metric(completeness),
        'hallucination_rate': round_metric(hallucination_rate),
        'refusal_detected': looks_like_refusal(answer)
    }


def average_metric(rows, key, predicate=None):
    """对适用样本计算均值。"""
    values = []
    for row in rows:
        if predicate and not predicate(row):
            continue
        value = row.get(key)
        if value is not None:
            values.append(float(value))
    return round_metric(sum(values) / len(values)) if values else None


def summarize_synonym_consistency(rows):
    """计算同义改写样本组的一致性。"""
    groups = {}
    for row in rows:
        group_name = row.get('synonym_group')
        if group_name:
            groups.setdefault(group_name, []).append(row)

    source_scores = []
    answer_scores = []
    for group_rows in groups.values():
        if len(group_rows) < 2:
            continue
        for left_index in range(len(group_rows)):
            for right_index in range(left_index + 1, len(group_rows)):
                left = group_rows[left_index]
                right = group_rows[right_index]
                left_sources = set(left.get('retrieved_source_names', []))
                right_sources = set(right.get('retrieved_source_names', []))
                if left_sources or right_sources:
                    source_scores.append(
                        len(left_sources & right_sources) / len(left_sources | right_sources)
                    )
                if left.get('answer') and right.get('answer'):
                    answer_score = term_jaccard(left['answer'], right['answer'])
                    if answer_score is not None:
                        answer_scores.append(answer_score)

    return {
        'synonym_group_count': len(groups),
        'synonym_retrieval_consistency': round_metric(sum(source_scores) / len(source_scores)) if source_scores else None,
        'synonym_answer_consistency': round_metric(sum(answer_scores) / len(answer_scores)) if answer_scores else None
    }


def summarize_rows(rows):
    """汇总评测指标。"""
    total = len(rows)
    retrieval_predicate = lambda row: row.get('has_expected_sources')
    keyword_predicate = lambda row: row.get('has_expected_keywords')
    if total == 0:
        return {
            'count': 0,
            'retrieval_count': 0,
            'followup_count': 0,
            'no_answer_count': 0,
            'synonym_case_count': 0,
            'hit_at_k': 0,
            'hit_at_1': 0,
            'recall_at_k': 0,
            'precision_at_k': 0,
            'ndcg_at_k': 0,
            'mrr': 0,
            'keyword_coverage': 0,
            'top1_keyword_coverage': 0,
            'answer_hit_at_1': 0,
            'avg_first_hit_rank': 0,
            'answer_correctness': None,
            'faithfulness': None,
            'groundedness': None,
            'completeness': None,
            'hallucination_rate': None,
            'citation_precision': None,
            'citation_recall': None,
            'citation_support': None,
            'citation_answer_support': None,
            'query_rewrite_accuracy': None,
            'followup_retrieval_hit_at_k': None,
            'no_answer_refusal_accuracy': None,
            'synonym_group_count': 0,
            'synonym_retrieval_consistency': None,
            'synonym_answer_consistency': None
        }

    hit_ranks = [row['first_hit_rank'] for row in rows if row['first_hit_rank']]
    summary = {
        'count': total,
        'retrieval_count': sum(1 for row in rows if row.get('has_expected_sources')),
        'followup_count': sum(1 for row in rows if row.get('is_followup')),
        'no_answer_count': sum(1 for row in rows if row.get('is_no_answer_case')),
        'synonym_case_count': sum(1 for row in rows if row.get('synonym_group')),
        'hit_at_k': average_metric(rows, 'hit_at_k', predicate=retrieval_predicate),
        'hit_at_1': average_metric(rows, 'hit_at_1', predicate=retrieval_predicate),
        'recall_at_k': average_metric(rows, 'recall_at_k', predicate=retrieval_predicate),
        'precision_at_k': average_metric(rows, 'precision_at_k', predicate=retrieval_predicate),
        'ndcg_at_k': average_metric(rows, 'ndcg_at_k', predicate=retrieval_predicate),
        'mrr': average_metric(rows, 'reciprocal_rank', predicate=retrieval_predicate),
        'keyword_coverage': average_metric(rows, 'keyword_coverage', predicate=keyword_predicate),
        'top1_keyword_coverage': average_metric(rows, 'top1_keyword_coverage', predicate=keyword_predicate),
        'answer_hit_at_1': average_metric(rows, 'answer_hit_at_1', predicate=keyword_predicate),
        'avg_first_hit_rank': round_metric(sum(hit_ranks) / len(hit_ranks)) if hit_ranks else 0,
        'answer_correctness': average_metric(rows, 'answer_correctness'),
        'faithfulness': average_metric(rows, 'faithfulness'),
        'groundedness': average_metric(rows, 'groundedness'),
        'completeness': average_metric(rows, 'completeness'),
        'hallucination_rate': average_metric(rows, 'hallucination_rate'),
        'citation_precision': average_metric(rows, 'citation_precision'),
        'citation_recall': average_metric(rows, 'citation_recall'),
        'citation_support': average_metric(rows, 'citation_support'),
        'citation_answer_support': average_metric(rows, 'citation_answer_support'),
        'query_rewrite_accuracy': average_metric(rows, 'query_rewrite_accuracy'),
        'followup_retrieval_hit_at_k': average_metric(
            rows,
            'hit_at_k',
            predicate=lambda row: row.get('is_followup')
        ),
        'no_answer_refusal_accuracy': average_metric(
            rows,
            'no_answer_refusal_hit',
            predicate=lambda row: row.get('is_no_answer_case')
        )
    }
    summary.update(summarize_synonym_consistency(rows))
    return summary


def summarize_by_field(rows, field):
    """按样本字段分组汇总指标。"""
    groups = {}
    for row in rows:
        value = row.get(field)
        if value:
            groups.setdefault(value, []).append(row)
    return {
        value: summarize_rows(group_rows)
        for value, group_rows in sorted(groups.items())
    }


def build_top_source(index, doc):
    """生成可写入报告的TopK来源信息。"""
    metadata = doc.metadata or {}
    return {
        'rank': index,
        'file_names': sorted(source_names(doc)),
        'source_label': metadata.get('source_label'),
        'retrieval_method': metadata.get('retrieval_method'),
        'vector_score': metadata.get('vector_score'),
        'keyword_score': metadata.get('keyword_score'),
        'keyword_search_score': metadata.get('keyword_search_score'),
        'keyword_backend': metadata.get('keyword_backend'),
        'bm25_score': metadata.get('bm25_score'),
        'bm25_score_raw': metadata.get('bm25_score_raw'),
        'bm25_query_terms': metadata.get('bm25_query_terms'),
        'bm25_matched_terms': metadata.get('bm25_matched_terms'),
        'bm25_matched_keywords': metadata.get('bm25_matched_keywords'),
        'hybrid_score': metadata.get('hybrid_score'),
        'rerank_score': metadata.get('rerank_score'),
        'rerank_backend': metadata.get('rerank_backend'),
        'chunk_index': metadata.get('chunk_index'),
        'chunk_strategy': metadata.get('chunk_strategy'),
        'chunk_size': metadata.get('chunk_size'),
        'chunk_overlap': metadata.get('chunk_overlap'),
        'page_number': metadata.get('page_number'),
        'header_path': metadata.get('header_path'),
        'section_title': metadata.get('section_title'),
        'content_preview': ' '.join((doc.page_content or '').split())[:200]
    }


def evaluate_query_rewrite(item, retrieval_query):
    """计算多轮追问改写准确率。"""
    expected_keywords = (
        item.get('rewritten_question_keywords')
        or item.get('expected_retrieval_query_keywords')
    )
    if expected_keywords:
        return round_metric(keyword_coverage_in_text(retrieval_query, expected_keywords))

    expected_query = (
        item.get('expected_retrieval_query')
        or item.get('standalone_question')
        or item.get('expected_query')
    )
    if not expected_query:
        return None
    return round_metric(term_overlap_score(expected_query, retrieval_query))


def case_history(item):
    """兼容history和conversation_history两种多轮样本字段。"""
    return item.get('history') or item.get('conversation_history') or []


def synonym_group_name(item):
    """根据显式分组或paired_with生成同义改写分组名。"""
    if item.get('synonym_group'):
        return item['synonym_group']
    paired_with = item.get('paired_with')
    if not paired_with:
        return None
    return '|'.join(sorted([str(item.get('id', '')), str(paired_with)]))


def run_retrieval(rag_service, item, eval_kb_id, top_k, use_rerank):
    """执行评测检索；多轮样本会复用RAGService的问题改写逻辑。"""
    history = case_history(item)
    if history:
        standalone_query = (
            item.get('expected_retrieval_query')
            or item.get('standalone_question')
            or item.get('expected_query')
        )
        if standalone_query:
            docs = rag_service.retrieve_for_eval(
                standalone_query,
                eval_kb_id,
                top_k=top_k,
                use_rerank=use_rerank
            )
            return docs, standalone_query, []

        context = rag_service._prepare_rag_context(
            item['question'],
            eval_kb_id,
            history=history,
            use_rerank=use_rerank
        )
        return context['docs'][:top_k], context['retrieval_query'], context['source_docs']

    docs = rag_service.retrieve_for_eval(
        item['question'],
        eval_kb_id,
        top_k=top_k,
        use_rerank=use_rerank
    )
    return docs, item['question'], []


def evaluate_mode(
    rag_service,
    dataset,
    top_k,
    use_rerank,
    kb_id_map=None,
    strategy_name='current',
    include_generation=False
):
    """按指定检索模式执行评测。"""
    rows = []
    kb_id_map = kb_id_map or {}

    for item in dataset:
        original_kb_id = resolve_kb_id(item)
        eval_kb_id = kb_id_map.get(original_kb_id, original_kb_id)
        docs, retrieval_query, prepared_sources = run_retrieval(
            rag_service,
            item,
            eval_kb_id,
            top_k=top_k,
            use_rerank=use_rerank
        )
        expected_sources = item.get('expected_sources', [])
        expected_keywords = item.get('expected_keywords', [])
        metrics = retrieval_metrics(docs, expected_sources, expected_keywords, top_k)
        top1_keyword_score = metrics['top1_keyword_coverage'] or 0
        answer = item.get('generated_answer')
        source_docs = prepared_sources

        if include_generation:
            try:
                answer, source_docs, retrieval_query = rag_service.ask(
                    item['question'],
                    eval_kb_id,
                    history=case_history(item)
                )
            except Exception as e:
                current_app.logger.warning(f"生成级评测失败 {item.get('id')}: {e}")
                answer = None
                source_docs = prepared_sources

        citations = source_docs_to_citations(source_docs) if source_docs else docs_to_citations(docs)
        citation_result = citation_metrics(citations, expected_sources, expected_keywords, answer=answer)
        generation_result = generation_metrics(answer, docs, item)
        no_answer_case = is_no_answer_case(item)
        no_answer_refusal_hit = (
            bool(generation_result['refusal_detected'])
            if no_answer_case and generation_result['refusal_detected'] is not None
            else None
        )

        row = {
            'id': item['id'],
            'kb_name': item.get('kb_name', ''),
            'question': item['question'],
            'retrieval_query': retrieval_query,
            'category': item.get('category', 'general'),
            'case_type': item.get('type', 'single_turn'),
            'eval_dimension': item.get('eval_dimension', item.get('type', 'single_turn')),
            'strategy_name': strategy_name,
            'mode': 'rerank' if use_rerank else 'baseline',
            'first_hit_rank': metrics['first_hit_rank'],
            'hit_at_k': metrics['hit_at_k'],
            'hit_at_1': metrics['hit_at_1'],
            'reciprocal_rank': metrics['mrr'],
            'recall_at_k': metrics['recall_at_k'],
            'precision_at_k': metrics['precision_at_k'],
            'ndcg_at_k': metrics['ndcg_at_k'],
            'keyword_coverage': metrics['keyword_coverage'],
            'top1_keyword_coverage': metrics['top1_keyword_coverage'],
            'answer_hit_at_1': top1_keyword_score >= ANSWER_HIT_THRESHOLD,
            'matched_expected_sources': metrics['matched_expected_sources'],
            'has_expected_sources': bool(expected_sources),
            'has_expected_keywords': bool(expected_keywords),
            'answer': answer,
            'is_followup': bool(case_history(item)) or item.get('type') == 'follow_up',
            'query_rewrite_accuracy': evaluate_query_rewrite(item, retrieval_query),
            'is_no_answer_case': no_answer_case,
            'no_answer_refusal_hit': no_answer_refusal_hit,
            'synonym_group': synonym_group_name(item),
            'retrieved_source_names': sorted({
                name
                for doc in docs
                for name in source_names(doc)
            }),
            **generation_result,
            **citation_result,
            'top_sources': [
                build_top_source(index, doc)
                for index, doc in enumerate(docs, 1)
            ],
            'citations': citations
        }
        rows.append(row)

    return rows, summarize_rows(rows)


def pct(value):
    """格式化百分比。"""
    if value is None:
        return 'N/A'
    return f'{value * 100:.1f}%'


def decimal_text(value, digits=3, signed=False):
    """格式化小数指标，兼容None。"""
    if value is None:
        return 'N/A'
    sign = '+' if signed else ''
    return f'{float(value):{sign}.{digits}f}'


def metric_delta(after, before):
    """计算指标差值，任一侧不可用时返回None。"""
    if after is None or before is None:
        return None
    return round(after - before, 4)


def metric_greater(after, before):
    """None安全的指标比较。"""
    return after is not None and before is not None and after > before


def build_standard_report(dataset, baseline_rows, baseline_summary, rerank_rows, rerank_summary):
    """构建默认的baseline vs rerank评测报告。"""
    row_pairs = {
        row['id']: row
        for row in baseline_rows
    }

    improved = 0
    worsened = 0
    unchanged = 0
    answer_improved = 0
    answer_worsened = 0
    answer_unchanged = 0
    details = []
    for row in rerank_rows:
        baseline = row_pairs[row['id']]
        before = baseline['reciprocal_rank']
        after = row['reciprocal_rank']
        if after > before:
            improved += 1
        elif after < before:
            worsened += 1
        else:
            unchanged += 1

        before_answer = baseline['top1_keyword_coverage'] or 0
        after_answer = row['top1_keyword_coverage'] or 0
        if after_answer > before_answer:
            answer_improved += 1
        elif after_answer < before_answer:
            answer_worsened += 1
        else:
            answer_unchanged += 1

        details.append({
            'id': row['id'],
            'question': row['question'],
            'retrieval_query': row.get('retrieval_query'),
            'category': row.get('category'),
            'case_type': row.get('case_type'),
            'eval_dimension': row.get('eval_dimension'),
            'baseline_rank': baseline['first_hit_rank'],
            'rerank_rank': row['first_hit_rank'],
            'baseline_mrr': before,
            'rerank_mrr': after,
            'baseline_recall_at_k': baseline.get('recall_at_k'),
            'rerank_recall_at_k': row.get('recall_at_k'),
            'baseline_precision_at_k': baseline.get('precision_at_k'),
            'rerank_precision_at_k': row.get('precision_at_k'),
            'baseline_ndcg_at_k': baseline.get('ndcg_at_k'),
            'rerank_ndcg_at_k': row.get('ndcg_at_k'),
            'baseline_keyword_coverage': baseline.get('keyword_coverage'),
            'rerank_keyword_coverage': row['keyword_coverage'],
            'baseline_top1_keyword_coverage': baseline['top1_keyword_coverage'],
            'rerank_top1_keyword_coverage': row['top1_keyword_coverage'],
            'baseline_answer_hit_at_1': baseline['answer_hit_at_1'],
            'rerank_answer_hit_at_1': row['answer_hit_at_1'],
            'answer_correctness': row.get('answer_correctness'),
            'faithfulness': row.get('faithfulness'),
            'groundedness': row.get('groundedness'),
            'completeness': row.get('completeness'),
            'hallucination_rate': row.get('hallucination_rate'),
            'citation_precision': row.get('citation_precision'),
            'citation_recall': row.get('citation_recall'),
            'citation_support': row.get('citation_support'),
            'citation_answer_support': row.get('citation_answer_support'),
            'query_rewrite_accuracy': row.get('query_rewrite_accuracy'),
            'no_answer_refusal_hit': row.get('no_answer_refusal_hit'),
            'synonym_group': row.get('synonym_group'),
            'rerank_top_sources': row['top_sources']
        })

    if rerank_summary.get('no_answer_refusal_accuracy') is not None:
        resume_summary = (
            f"在{len(dataset)}条无答案/拒答评测样本上，系统无答案拒答准确率为"
            f"{pct(rerank_summary['no_answer_refusal_accuracy'])}。"
        )
    elif metric_greater(rerank_summary['hit_at_1'], baseline_summary['hit_at_1']) or metric_greater(rerank_summary['mrr'], baseline_summary['mrr']):
        resume_summary = (
            f"在{len(dataset)}条自建RAG检索评测样本上，Rerank后Top1来源命中率"
            f"由{pct(baseline_summary['hit_at_1'])}提升至{pct(rerank_summary['hit_at_1'])}，"
            f"MRR由{decimal_text(baseline_summary['mrr'])}提升至{decimal_text(rerank_summary['mrr'])}。"
        )
    elif metric_greater(rerank_summary['top1_keyword_coverage'], baseline_summary['top1_keyword_coverage']):
        resume_summary = (
            f"在{len(dataset)}条自建RAG检索评测样本上，Rerank在保持TopK来源命中率"
            f"{pct(rerank_summary['hit_at_k'])}的同时，将Top1答案关键词覆盖率"
            f"由{pct(baseline_summary['top1_keyword_coverage'])}提升至"
            f"{pct(rerank_summary['top1_keyword_coverage'])}。"
        )
    elif metric_greater(rerank_summary['answer_hit_at_1'], baseline_summary['answer_hit_at_1']):
        resume_summary = (
            f"在{len(dataset)}条自建RAG检索评测样本上，Rerank在保持TopK来源命中率"
            f"{pct(rerank_summary['hit_at_k'])}的同时，将Top1答案片段命中率"
            f"由{pct(baseline_summary['answer_hit_at_1'])}提升至"
            f"{pct(rerank_summary['answer_hit_at_1'])}。"
        )
    else:
        resume_summary = (
            f"在{len(dataset)}条自建RAG检索评测样本上，Rerank后TopK来源命中率为"
            f"{pct(rerank_summary['hit_at_k'])}，Top1答案关键词覆盖率为"
            f"{pct(rerank_summary['top1_keyword_coverage'])}。"
        )

    return {
        'baseline_summary': baseline_summary,
        'rerank_summary': rerank_summary,
        'delta': {
            'hit_at_k': metric_delta(rerank_summary['hit_at_k'], baseline_summary['hit_at_k']),
            'hit_at_1': metric_delta(rerank_summary['hit_at_1'], baseline_summary['hit_at_1']),
            'recall_at_k': metric_delta(rerank_summary['recall_at_k'], baseline_summary['recall_at_k']),
            'precision_at_k': metric_delta(rerank_summary['precision_at_k'], baseline_summary['precision_at_k']),
            'ndcg_at_k': metric_delta(rerank_summary['ndcg_at_k'], baseline_summary['ndcg_at_k']),
            'mrr': metric_delta(rerank_summary['mrr'], baseline_summary['mrr']),
            'keyword_coverage': metric_delta(rerank_summary['keyword_coverage'], baseline_summary['keyword_coverage']),
            'top1_keyword_coverage': metric_delta(
                rerank_summary['top1_keyword_coverage'],
                baseline_summary['top1_keyword_coverage']
            ),
            'answer_hit_at_1': metric_delta(rerank_summary['answer_hit_at_1'], baseline_summary['answer_hit_at_1']),
            'answer_correctness': metric_delta(
                rerank_summary['answer_correctness'],
                baseline_summary['answer_correctness']
            ),
            'faithfulness': metric_delta(rerank_summary['faithfulness'], baseline_summary['faithfulness']),
            'groundedness': metric_delta(rerank_summary['groundedness'], baseline_summary['groundedness']),
            'completeness': metric_delta(rerank_summary['completeness'], baseline_summary['completeness']),
            'hallucination_rate': metric_delta(
                rerank_summary['hallucination_rate'],
                baseline_summary['hallucination_rate']
            ),
            'citation_precision': metric_delta(
                rerank_summary['citation_precision'],
                baseline_summary['citation_precision']
            ),
            'citation_recall': metric_delta(rerank_summary['citation_recall'], baseline_summary['citation_recall']),
            'citation_support': metric_delta(
                rerank_summary['citation_support'],
                baseline_summary['citation_support']
            ),
            'citation_answer_support': metric_delta(
                rerank_summary['citation_answer_support'],
                baseline_summary['citation_answer_support']
            )
        },
        'case_changes': {
            'improved': improved,
            'worsened': worsened,
            'unchanged': unchanged,
            'answer_improved': answer_improved,
            'answer_worsened': answer_worsened,
            'answer_unchanged': answer_unchanged
        },
        'group_summaries': {
            'baseline_by_category': summarize_by_field(baseline_rows, 'category'),
            'rerank_by_category': summarize_by_field(rerank_rows, 'category'),
            'baseline_by_dimension': summarize_by_field(baseline_rows, 'eval_dimension'),
            'rerank_by_dimension': summarize_by_field(rerank_rows, 'eval_dimension'),
            'baseline_by_knowledge_base': summarize_by_field(baseline_rows, 'kb_name'),
            'rerank_by_knowledge_base': summarize_by_field(rerank_rows, 'kb_name')
        },
        'resume_summary': resume_summary,
        'details': details
    }


def write_standard_outputs(report, output_dir):
    """写入默认评测的JSON和CSV。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'rag_eval_report.json'
    csv_path = output_dir / 'rag_eval_details.csv'

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                'id',
                'question',
                'retrieval_query',
                'category',
                'case_type',
                'eval_dimension',
                'baseline_rank',
                'rerank_rank',
                'baseline_mrr',
                'rerank_mrr',
                'baseline_recall_at_k',
                'rerank_recall_at_k',
                'baseline_precision_at_k',
                'rerank_precision_at_k',
                'baseline_ndcg_at_k',
                'rerank_ndcg_at_k',
                'baseline_keyword_coverage',
                'rerank_keyword_coverage',
                'baseline_top1_keyword_coverage',
                'rerank_top1_keyword_coverage',
                'baseline_answer_hit_at_1',
                'rerank_answer_hit_at_1',
                'answer_correctness',
                'faithfulness',
                'groundedness',
                'completeness',
                'hallucination_rate',
                'citation_precision',
                'citation_recall',
                'citation_support',
                'citation_answer_support',
                'query_rewrite_accuracy',
                'no_answer_refusal_hit',
                'synonym_group'
            ]
        )
        writer.writeheader()
        for row in report['details']:
            writer.writerow({
                key: row[key]
                for key in writer.fieldnames
            })

    return json_path, csv_path


def print_standard_summary(report, json_path, csv_path):
    """打印默认评测摘要。"""
    baseline = report['baseline_summary']
    rerank = report['rerank_summary']
    delta = report['delta']

    print('\n=== RAG检索评测结果 ===')
    print(
        f"样本数量: {baseline['count']} | "
        f"检索样本: {baseline.get('retrieval_count', 0)} | "
        f"多轮样本: {baseline.get('followup_count', 0)} | "
        f"无答案样本: {baseline.get('no_answer_count', 0)} | "
        f"同义改写样本: {baseline.get('synonym_case_count', 0)}"
    )
    print(f"Baseline Hit@K: {pct(baseline['hit_at_k'])} | Rerank Hit@K: {pct(rerank['hit_at_k'])} | Delta: {pct(delta['hit_at_k'])}")
    print(f"Baseline Recall@K: {pct(baseline['recall_at_k'])} | Rerank Recall@K: {pct(rerank['recall_at_k'])} | Delta: {pct(delta['recall_at_k'])}")
    print(f"Baseline Precision@K: {pct(baseline['precision_at_k'])} | Rerank Precision@K: {pct(rerank['precision_at_k'])} | Delta: {pct(delta['precision_at_k'])}")
    print(
        f"Baseline NDCG@K: {decimal_text(baseline['ndcg_at_k'])} | "
        f"Rerank NDCG@K: {decimal_text(rerank['ndcg_at_k'])} | "
        f"Delta: {decimal_text(delta['ndcg_at_k'], signed=True)}"
    )
    print(f"Baseline Hit@1: {pct(baseline['hit_at_1'])} | Rerank Hit@1: {pct(rerank['hit_at_1'])} | Delta: {pct(delta['hit_at_1'])}")
    print(
        f"Baseline MRR: {decimal_text(baseline['mrr'])} | "
        f"Rerank MRR: {decimal_text(rerank['mrr'])} | "
        f"Delta: {decimal_text(delta['mrr'], signed=True)}"
    )
    print(f"关键词覆盖率: {pct(baseline['keyword_coverage'])} -> {pct(rerank['keyword_coverage'])}")
    print(
        "Top1答案关键词覆盖率: "
        f"{pct(baseline['top1_keyword_coverage'])} -> "
        f"{pct(rerank['top1_keyword_coverage'])} | "
        f"Delta: {pct(delta['top1_keyword_coverage'])}"
    )
    print(
        f"Top1答案片段命中率(关键词覆盖>={ANSWER_HIT_THRESHOLD:.0%}): "
        f"{pct(baseline['answer_hit_at_1'])} -> {pct(rerank['answer_hit_at_1'])}"
    )
    if rerank.get('answer_correctness') is not None:
        print('\n=== 生成级启发式评测 ===')
        print(f"Answer Correctness: {pct(rerank['answer_correctness'])}")
        print(f"Faithfulness/Groundedness: {pct(rerank['faithfulness'])}")
        print(f"Completeness: {pct(rerank['completeness'])}")
        print(f"Hallucination Rate: {pct(rerank['hallucination_rate'])}")
    if rerank.get('citation_precision') is not None:
        print('\n=== 引用级评测 ===')
        print(f"Citation Precision: {pct(rerank['citation_precision'])}")
        print(f"Citation Recall: {pct(rerank['citation_recall'])}")
        print(f"引用片段关键词支持率: {pct(rerank['citation_support'])}")
    if rerank.get('query_rewrite_accuracy') is not None:
        print('\n=== 多轮级评测 ===')
        print(f"Query Rewrite Accuracy: {pct(rerank['query_rewrite_accuracy'])}")
        print(f"Follow-up Retrieval Hit@K: {pct(rerank['followup_retrieval_hit_at_k'])}")
    if rerank.get('no_answer_refusal_accuracy') is not None or rerank.get('synonym_retrieval_consistency') is not None:
        print('\n=== 鲁棒性评测 ===')
        print(f"无答案拒答准确率: {pct(rerank['no_answer_refusal_accuracy'])}")
        print(f"同义改写检索一致性: {pct(rerank['synonym_retrieval_consistency'])}")
        print(f"同义改写答案一致性: {pct(rerank['synonym_answer_consistency'])}")
    print('\n简历可用表述:')
    print(report['resume_summary'])
    grouped = report.get('group_summaries', {}).get('rerank_by_dimension', {})
    if grouped:
        print('\n按评测维度汇总(Rerank):')
        for dimension, summary in grouped.items():
            print(
                f"- {dimension}: count={summary['count']}, "
                f"Hit@K={pct(summary['hit_at_k'])}, "
                f"Recall@K={pct(summary['recall_at_k'])}, "
                f"NDCG@K={decimal_text(summary['ndcg_at_k'], digits=4)}"
            )
    print(f'\n报告文件: {json_path}')
    print(f'明细CSV: {csv_path}')


def load_chunk_strategy_presets(path=None):
    """加载chunk策略预设。未提供文件时使用内置三组策略。"""
    if not path:
        return copy.deepcopy(DEFAULT_CHUNK_STRATEGY_PRESETS)

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    presets = data.get('strategies', data) if isinstance(data, dict) else data
    if not isinstance(presets, list) or not presets:
        raise ValueError('chunk策略文件必须是非空数组，或包含 strategies 数组')

    normalized = []
    for preset in presets:
        if not preset.get('name'):
            raise ValueError('每个chunk策略必须包含 name')
        normalized.append({
            'name': preset['name'],
            'description': preset.get('description', ''),
            'chunk_strategies': preset.get('chunk_strategies', preset.get('strategies'))
        })
    return normalized


def merge_chunk_strategies(base_strategies, overrides):
    """把策略覆盖项合并到当前项目配置中，未设置的字段沿用项目默认值。"""
    merged = copy.deepcopy(base_strategies or {})
    if not overrides:
        return merged

    for file_type, override in overrides.items():
        file_strategy = dict(merged.get(file_type, {}))
        file_strategy.update(override or {})
        merged[file_type] = file_strategy
    return merged


def safe_name(value):
    """生成Chroma collection可用的安全名称片段。"""
    name = re.sub(r'[^a-zA-Z0-9_-]+', '_', str(value)).strip('_-')
    return name[:80] or 'strategy'


def collect_eval_documents(dataset):
    """收集评测集涉及知识库中的已向量化文档。"""
    kb_ids = sorted({resolve_kb_id(item) for item in dataset})
    documents_by_kb = {}
    missing_files = []

    for kb_id in kb_ids:
        docs = (
            Document.query
            .filter_by(kb_id=kb_id, status='vectorized')
            .order_by(Document.id.asc())
            .all()
        )
        available_docs = []
        for doc in docs:
            if os.path.exists(doc.file_path):
                available_docs.append(doc)
            else:
                missing_files.append({
                    'doc_id': doc.id,
                    'file_name': doc.file_name,
                    'file_path': doc.file_path
                })

        if not available_docs:
            raise ValueError(f'知识库 {kb_id} 没有可用于评测重建索引的已向量化文档')
        documents_by_kb[kb_id] = available_docs

    return documents_by_kb, missing_files


def delete_eval_collection(vector_service, kb_id):
    """删除临时评测collection。"""
    collection_name = vector_service._get_collection_name(kb_id)
    try:
        vectorstore = vector_service._get_vectorstore(kb_id)
        vectorstore._client.delete_collection(collection_name)
    except Exception as e:
        message = str(e).lower()
        if 'does not exist' not in message and 'not found' not in message:
            current_app.logger.warning(f'删除临时collection失败 {collection_name}: {e}')


def build_eval_kb_id(strategy_name, original_kb_id, run_id):
    """构造不会污染正式知识库的临时kb_id。"""
    return f"eval_{safe_name(strategy_name)}_{original_kb_id}_{run_id}"


def index_documents_for_strategy(strategy_name, documents_by_kb, run_id):
    """按当前current_app中的chunk配置，将文档写入临时collection。"""
    vector_service = VectorService()
    kb_id_map = {}
    index_stats = {
        'strategy_name': strategy_name,
        'document_count': 0,
        'chunk_count': 0,
        'collections': []
    }

    for original_kb_id, documents in documents_by_kb.items():
        eval_kb_id = build_eval_kb_id(strategy_name, original_kb_id, run_id)
        kb_id_map[original_kb_id] = eval_kb_id
        delete_eval_collection(vector_service, eval_kb_id)

        collection_chunks = 0
        for doc in documents:
            chunk_count = vector_service.process_document(
                doc.id,
                doc.file_path,
                doc.file_type,
                eval_kb_id,
                original_file_name=doc.file_name
            )
            collection_chunks += chunk_count
            index_stats['document_count'] += 1

        index_stats['chunk_count'] += collection_chunks
        index_stats['collections'].append({
            'original_kb_id': original_kb_id,
            'eval_kb_id': eval_kb_id,
            'document_count': len(documents),
            'chunk_count': collection_chunks
        })

    return kb_id_map, index_stats


def compare_against_reference(results, reference_strategy):
    """计算每个策略相对参考策略的指标差异。"""
    reference_by_mode = {
        result['mode']: result
        for result in results
        if result['strategy_name'] == reference_strategy
    }

    deltas = []
    for result in results:
        reference = reference_by_mode.get(result['mode'])
        if not reference or result['strategy_name'] == reference_strategy:
            continue

        summary = result['summary']
        base = reference['summary']
        deltas.append({
            'strategy_name': result['strategy_name'],
            'mode': result['mode'],
            'reference_strategy': reference_strategy,
            'hit_at_k_delta': round(summary['hit_at_k'] - base['hit_at_k'], 4),
            'hit_at_1_delta': round(summary['hit_at_1'] - base['hit_at_1'], 4),
            'recall_at_k_delta': metric_delta(summary['recall_at_k'], base['recall_at_k']),
            'precision_at_k_delta': metric_delta(summary['precision_at_k'], base['precision_at_k']),
            'ndcg_at_k_delta': metric_delta(summary['ndcg_at_k'], base['ndcg_at_k']),
            'mrr_delta': metric_delta(summary['mrr'], base['mrr']),
            'keyword_coverage_delta': metric_delta(summary['keyword_coverage'], base['keyword_coverage']),
            'top1_keyword_coverage_delta': metric_delta(
                summary['top1_keyword_coverage'],
                base['top1_keyword_coverage']
            ),
            'answer_hit_at_1_delta': metric_delta(summary['answer_hit_at_1'], base['answer_hit_at_1'])
        })

    return deltas


def build_chunk_strategy_report(dataset, results, missing_files, run_id, reference_strategy):
    """构建chunk策略对比报告。"""
    best_by_mrr = max(results, key=lambda item: item['summary']['mrr']) if results else None
    best_by_top1_keywords = (
        max(results, key=lambda item: item['summary']['top1_keyword_coverage'])
        if results else None
    )

    return {
        'run_id': run_id,
        'sample_count': len(dataset),
        'reference_strategy': reference_strategy,
        'missing_files': missing_files,
        'summaries': [
            {
                'strategy_name': item['strategy_name'],
                'description': item.get('description', ''),
                'mode': item['mode'],
                'chunk_strategies': item.get('chunk_strategies'),
                'index_stats': item.get('index_stats'),
                **item['summary']
            }
            for item in results
        ],
        'deltas': compare_against_reference(results, reference_strategy),
        'best': {
            'by_mrr': {
                'strategy_name': best_by_mrr['strategy_name'],
                'mode': best_by_mrr['mode'],
                'mrr': best_by_mrr['summary']['mrr']
            } if best_by_mrr else None,
            'by_top1_keyword_coverage': {
                'strategy_name': best_by_top1_keywords['strategy_name'],
                'mode': best_by_top1_keywords['mode'],
                'top1_keyword_coverage': best_by_top1_keywords['summary']['top1_keyword_coverage']
            } if best_by_top1_keywords else None
        },
        'details': [
            row
            for item in results
            for row in item['rows']
        ]
    }


def write_chunk_strategy_outputs(report, output_dir):
    """写入chunk策略对比评测结果。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'chunk_strategy_eval_report.json'
    csv_path = output_dir / 'chunk_strategy_eval_details.csv'

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    fieldnames = [
        'strategy_name',
        'mode',
        'id',
        'kb_name',
        'question',
        'first_hit_rank',
        'hit_at_k',
        'reciprocal_rank',
        'keyword_coverage',
        'top1_keyword_coverage',
        'answer_hit_at_1',
        'top1_file_names',
        'top1_chunk_index',
        'top1_chunk_size',
        'top1_chunk_overlap',
        'top1_chunk_strategy',
        'top1_retrieval_method',
        'top1_bm25_score',
        'top1_bm25_matched_terms',
        'top1_bm25_matched_keywords'
    ]

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in report['details']:
            top1 = row['top_sources'][0] if row['top_sources'] else {}
            writer.writerow({
                'strategy_name': row['strategy_name'],
                'mode': row['mode'],
                'id': row['id'],
                'kb_name': row.get('kb_name', ''),
                'question': row['question'],
                'first_hit_rank': row['first_hit_rank'],
                'hit_at_k': row['hit_at_k'],
                'reciprocal_rank': row['reciprocal_rank'],
                'keyword_coverage': row['keyword_coverage'],
                'top1_keyword_coverage': row['top1_keyword_coverage'],
                'answer_hit_at_1': row['answer_hit_at_1'],
                'top1_file_names': ' | '.join(top1.get('file_names', [])),
                'top1_chunk_index': top1.get('chunk_index'),
                'top1_chunk_size': top1.get('chunk_size'),
                'top1_chunk_overlap': top1.get('chunk_overlap'),
                'top1_chunk_strategy': top1.get('chunk_strategy'),
                'top1_retrieval_method': top1.get('retrieval_method'),
                'top1_bm25_score': top1.get('bm25_score'),
                'top1_bm25_matched_terms': top1.get('bm25_matched_terms'),
                'top1_bm25_matched_keywords': top1.get('bm25_matched_keywords')
            })

    return json_path, csv_path


def print_chunk_strategy_summary(report, json_path, csv_path):
    """打印chunk策略对比摘要。"""
    print('\n=== Chunk策略对比评测结果 ===')
    print(f"运行ID: {report['run_id']}")
    print(f"样本数量: {report['sample_count']}")
    print(f"参考策略: {report['reference_strategy']}")

    for summary in report['summaries']:
        print(
            f"- {summary['strategy_name']} / {summary['mode']}: "
            f"Hit@K={pct(summary['hit_at_k'])}, "
            f"Hit@1={pct(summary['hit_at_1'])}, "
            f"MRR={summary['mrr']:.3f}, "
            f"Top1关键词覆盖={pct(summary['top1_keyword_coverage'])}, "
            f"chunks={summary['index_stats']['chunk_count']}"
        )

    if report['deltas']:
        print('\n相对参考策略的变化:')
        for delta in report['deltas']:
            print(
                f"- {delta['strategy_name']} / {delta['mode']}: "
                f"MRR {delta['mrr_delta']:+.3f}, "
                f"Hit@1 {pct(delta['hit_at_1_delta'])}, "
                f"Top1关键词覆盖 {pct(delta['top1_keyword_coverage_delta'])}"
            )

    print('\n最佳结果:')
    print(f"- MRR: {report['best']['by_mrr']}")
    print(f"- Top1关键词覆盖: {report['best']['by_top1_keyword_coverage']}")
    print(f'\n报告文件: {json_path}')
    print(f'明细CSV: {csv_path}')


def run_standard_evaluation(args):
    """运行默认baseline vs rerank评测。"""
    dataset = filter_dataset(load_dataset(Path(args.dataset)), args)
    app = create_app()

    with app.app_context():
        rag_service = RAGService()
        baseline_rows, baseline_summary = evaluate_mode(
            rag_service,
            dataset,
            top_k=args.top_k,
            use_rerank=False,
            include_generation=args.include_generation
        )
        rerank_rows, rerank_summary = evaluate_mode(
            rag_service,
            dataset,
            top_k=args.top_k,
            use_rerank=True,
            include_generation=args.include_generation
        )

        report = build_standard_report(dataset, baseline_rows, baseline_summary, rerank_rows, rerank_summary)
        json_path, csv_path = write_standard_outputs(report, Path(args.output_dir))
        print_standard_summary(report, json_path, csv_path)


def modes_for_chunk_compare(value):
    """解析切分策略对比要跑的检索模式。"""
    if value == 'both':
        return [('baseline', False), ('rerank', True)]
    if value == 'baseline':
        return [('baseline', False)]
    return [('rerank', True)]


def run_chunk_strategy_evaluation(args):
    """运行chunk策略对比评测。"""
    dataset = filter_dataset(load_dataset(Path(args.dataset)), args)
    presets = load_chunk_strategy_presets(args.chunk_strategy_file)
    app = create_app()
    run_id = uuid.uuid4().hex[:8]

    with app.app_context():
        base_chunk_strategies = copy.deepcopy(current_app.config.get('CHUNK_STRATEGIES', {}))
        documents_by_kb, missing_files = collect_eval_documents(dataset)
        results = []
        eval_kb_ids = []

        try:
            for preset in presets:
                strategy_name = preset['name']
                merged_strategies = merge_chunk_strategies(
                    base_chunk_strategies,
                    preset.get('chunk_strategies')
                )
                current_app.config['CHUNK_STRATEGIES'] = merged_strategies

                print(f"\n正在索引策略: {strategy_name}")
                kb_id_map, index_stats = index_documents_for_strategy(strategy_name, documents_by_kb, run_id)
                eval_kb_ids.extend(kb_id_map.values())

                rag_service = RAGService()
                for mode_name, use_rerank in modes_for_chunk_compare(args.chunk_compare_mode):
                    rows, summary = evaluate_mode(
                        rag_service,
                        dataset,
                        top_k=args.top_k,
                        use_rerank=use_rerank,
                        kb_id_map=kb_id_map,
                        strategy_name=strategy_name,
                        include_generation=args.include_generation
                    )
                    results.append({
                        'strategy_name': strategy_name,
                        'description': preset.get('description', ''),
                        'mode': mode_name,
                        'chunk_strategies': merged_strategies,
                        'index_stats': index_stats,
                        'rows': rows,
                        'summary': summary
                    })
        finally:
            current_app.config['CHUNK_STRATEGIES'] = base_chunk_strategies
            if not args.keep_eval_collections:
                cleanup_service = VectorService()
                for eval_kb_id in eval_kb_ids:
                    delete_eval_collection(cleanup_service, eval_kb_id)

        reference_strategy = presets[0]['name']
        report = build_chunk_strategy_report(
            dataset,
            results,
            missing_files,
            run_id,
            reference_strategy
        )
        json_path, csv_path = write_chunk_strategy_outputs(report, Path(args.output_dir))
        print_chunk_strategy_summary(report, json_path, csv_path)


def main():
    parser = argparse.ArgumentParser(description='RAG检索、Rerank与chunk策略评测')
    parser.add_argument('--dataset', default=str(DEFAULT_DATASET), help='评测集JSON路径')
    parser.add_argument('--top-k', type=int, default=4, help='最终返回TopK')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR), help='评测结果输出目录')
    parser.add_argument(
        '--compare-chunk-strategies',
        action='store_true',
        help='启用chunk策略对比模式，会创建临时Chroma collection并重新索引文档'
    )
    parser.add_argument(
        '--chunk-strategy-file',
        default=None,
        help='chunk策略预设JSON路径；不传时使用内置 current/small_chunks/large_chunks'
    )
    parser.add_argument(
        '--chunk-compare-mode',
        choices=['baseline', 'rerank', 'both'],
        default='both',
        help='chunk策略对比时要评测的检索模式'
    )
    parser.add_argument(
        '--keep-eval-collections',
        action='store_true',
        help='保留临时Chroma collection，便于调试；默认评测结束后删除'
    )
    parser.add_argument(
        '--include-generation',
        action='store_true',
        help='调用LLM生成答案并启用生成级、答案引用支持和无答案拒答评测；默认只做检索/引用片段评测'
    )
    parser.add_argument(
        '--filter-category',
        default=None,
        help='只评测指定category，多个值用逗号分隔，例如 no_answer_refusal,synonym_paraphrase'
    )
    parser.add_argument(
        '--filter-dimension',
        default=None,
        help='只评测指定eval_dimension，多个值用逗号分隔，例如 retrieval,robustness'
    )
    parser.add_argument(
        '--filter-type',
        default=None,
        help='只评测指定type，多个值用逗号分隔，例如 no_answer,follow_up'
    )
    args = parser.parse_args()

    if args.compare_chunk_strategies:
        run_chunk_strategy_evaluation(args)
    else:
        run_standard_evaluation(args)


if __name__ == '__main__':
    main()
