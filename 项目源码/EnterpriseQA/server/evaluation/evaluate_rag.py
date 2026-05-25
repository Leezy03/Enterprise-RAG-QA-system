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
    except (TypeError, ValueError):
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


def source_hit(doc, expected_sources):
    """判断单个片段是否命中预期来源。"""
    actual_names = {name.lower() for name in source_names(doc)}
    expected_names = [name.lower() for name in expected_sources]

    for actual in actual_names:
        for expected in expected_names:
            if actual == expected or actual in expected or expected in actual:
                return True
    return False


def first_hit_rank(docs, expected_sources):
    """返回第一个命中预期来源的排名，未命中返回None。"""
    for index, doc in enumerate(docs, 1):
        if source_hit(doc, expected_sources):
            return index
    return None


def keyword_coverage(docs, expected_keywords):
    """计算TopK片段对预期关键词的覆盖比例。"""
    if not expected_keywords:
        return 0

    text = '\n'.join(doc.page_content or '' for doc in docs).lower()
    matched = 0
    for keyword in expected_keywords:
        if str(keyword).lower() in text:
            matched += 1
    return matched / len(expected_keywords)


def summarize_rows(rows):
    """汇总评测指标。"""
    total = len(rows)
    if total == 0:
        return {
            'count': 0,
            'hit_at_k': 0,
            'hit_at_1': 0,
            'mrr': 0,
            'keyword_coverage': 0,
            'top1_keyword_coverage': 0,
            'answer_hit_at_1': 0,
            'avg_first_hit_rank': 0
        }

    hit_ranks = [row['first_hit_rank'] for row in rows if row['first_hit_rank']]
    return {
        'count': total,
        'hit_at_k': sum(1 for row in rows if row['hit_at_k']) / total,
        'hit_at_1': sum(1 for row in rows if row['first_hit_rank'] == 1) / total,
        'mrr': sum(row['reciprocal_rank'] for row in rows) / total,
        'keyword_coverage': sum(row['keyword_coverage'] for row in rows) / total,
        'top1_keyword_coverage': sum(row['top1_keyword_coverage'] for row in rows) / total,
        'answer_hit_at_1': sum(1 for row in rows if row['answer_hit_at_1']) / total,
        'avg_first_hit_rank': sum(hit_ranks) / len(hit_ranks) if hit_ranks else 0
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
        'chunk_index': metadata.get('chunk_index'),
        'chunk_strategy': metadata.get('chunk_strategy'),
        'chunk_size': metadata.get('chunk_size'),
        'chunk_overlap': metadata.get('chunk_overlap'),
        'page_number': metadata.get('page_number'),
        'header_path': metadata.get('header_path'),
        'section_title': metadata.get('section_title'),
        'content_preview': ' '.join((doc.page_content or '').split())[:200]
    }


def evaluate_mode(rag_service, dataset, top_k, use_rerank, kb_id_map=None, strategy_name='current'):
    """按指定检索模式执行评测。"""
    rows = []
    kb_id_map = kb_id_map or {}

    for item in dataset:
        original_kb_id = resolve_kb_id(item)
        eval_kb_id = kb_id_map.get(original_kb_id, original_kb_id)
        docs = rag_service.retrieve_for_eval(
            item['question'],
            eval_kb_id,
            top_k=top_k,
            use_rerank=use_rerank
        )
        expected_sources = item.get('expected_sources', [])
        rank = first_hit_rank(docs, expected_sources)
        top1_keyword_score = keyword_coverage(docs[:1], item.get('expected_keywords', []))

        rows.append({
            'id': item['id'],
            'kb_name': item.get('kb_name', ''),
            'question': item['question'],
            'strategy_name': strategy_name,
            'mode': 'rerank' if use_rerank else 'baseline',
            'first_hit_rank': rank,
            'hit_at_k': bool(rank),
            'reciprocal_rank': round(1 / rank, 4) if rank else 0,
            'keyword_coverage': round(keyword_coverage(docs, item.get('expected_keywords', [])), 4),
            'top1_keyword_coverage': round(top1_keyword_score, 4),
            'answer_hit_at_1': top1_keyword_score >= ANSWER_HIT_THRESHOLD,
            'top_sources': [
                build_top_source(index, doc)
                for index, doc in enumerate(docs, 1)
            ]
        })

    return rows, summarize_rows(rows)


def pct(value):
    """格式化百分比。"""
    return f'{value * 100:.1f}%'


def build_standard_report(dataset, baseline_rows, baseline_summary, rerank_rows, rerank_summary):
    """构建默认的baseline vs rerank评测报告。"""
    row_pairs = {
        row['id']: {
            'baseline_rank': row['first_hit_rank'],
            'baseline_mrr': row['reciprocal_rank'],
            'baseline_top1_keyword_coverage': row['top1_keyword_coverage'],
            'baseline_answer_hit_at_1': row['answer_hit_at_1']
        }
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
        before = baseline['baseline_mrr']
        after = row['reciprocal_rank']
        if after > before:
            improved += 1
        elif after < before:
            worsened += 1
        else:
            unchanged += 1

        before_answer = baseline['baseline_top1_keyword_coverage']
        after_answer = row['top1_keyword_coverage']
        if after_answer > before_answer:
            answer_improved += 1
        elif after_answer < before_answer:
            answer_worsened += 1
        else:
            answer_unchanged += 1

        details.append({
            'id': row['id'],
            'question': row['question'],
            'baseline_rank': baseline['baseline_rank'],
            'rerank_rank': row['first_hit_rank'],
            'baseline_mrr': before,
            'rerank_mrr': after,
            'keyword_coverage': row['keyword_coverage'],
            'baseline_top1_keyword_coverage': baseline['baseline_top1_keyword_coverage'],
            'rerank_top1_keyword_coverage': row['top1_keyword_coverage'],
            'baseline_answer_hit_at_1': baseline['baseline_answer_hit_at_1'],
            'rerank_answer_hit_at_1': row['answer_hit_at_1'],
            'rerank_top_sources': row['top_sources']
        })

    if rerank_summary['hit_at_1'] > baseline_summary['hit_at_1'] or rerank_summary['mrr'] > baseline_summary['mrr']:
        resume_summary = (
            f"在{len(dataset)}条自建RAG检索评测样本上，Rerank后Top1来源命中率"
            f"由{pct(baseline_summary['hit_at_1'])}提升至{pct(rerank_summary['hit_at_1'])}，"
            f"MRR由{baseline_summary['mrr']:.3f}提升至{rerank_summary['mrr']:.3f}。"
        )
    else:
        resume_summary = (
            f"在{len(dataset)}条自建RAG检索评测样本上，Rerank在保持TopK来源命中率"
            f"{pct(rerank_summary['hit_at_k'])}的同时，将Top1答案关键词覆盖率"
            f"由{pct(baseline_summary['top1_keyword_coverage'])}提升至"
            f"{pct(rerank_summary['top1_keyword_coverage'])}。"
        )

    return {
        'baseline_summary': baseline_summary,
        'rerank_summary': rerank_summary,
        'delta': {
            'hit_at_k': round(rerank_summary['hit_at_k'] - baseline_summary['hit_at_k'], 4),
            'hit_at_1': round(rerank_summary['hit_at_1'] - baseline_summary['hit_at_1'], 4),
            'mrr': round(rerank_summary['mrr'] - baseline_summary['mrr'], 4),
            'keyword_coverage': round(
                rerank_summary['keyword_coverage'] - baseline_summary['keyword_coverage'],
                4
            ),
            'top1_keyword_coverage': round(
                rerank_summary['top1_keyword_coverage'] - baseline_summary['top1_keyword_coverage'],
                4
            ),
            'answer_hit_at_1': round(
                rerank_summary['answer_hit_at_1'] - baseline_summary['answer_hit_at_1'],
                4
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
                'baseline_rank',
                'rerank_rank',
                'baseline_mrr',
                'rerank_mrr',
                'keyword_coverage',
                'baseline_top1_keyword_coverage',
                'rerank_top1_keyword_coverage',
                'baseline_answer_hit_at_1',
                'rerank_answer_hit_at_1'
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
    print(f"样本数量: {baseline['count']}")
    print(f"Baseline Hit@K: {pct(baseline['hit_at_k'])} | Rerank Hit@K: {pct(rerank['hit_at_k'])} | Delta: {pct(delta['hit_at_k'])}")
    print(f"Baseline Hit@1: {pct(baseline['hit_at_1'])} | Rerank Hit@1: {pct(rerank['hit_at_1'])} | Delta: {pct(delta['hit_at_1'])}")
    print(f"Baseline MRR: {baseline['mrr']:.3f} | Rerank MRR: {rerank['mrr']:.3f} | Delta: {delta['mrr']:+.3f}")
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
    print('\n简历可用表述:')
    print(report['resume_summary'])
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
            'mrr_delta': round(summary['mrr'] - base['mrr'], 4),
            'keyword_coverage_delta': round(summary['keyword_coverage'] - base['keyword_coverage'], 4),
            'top1_keyword_coverage_delta': round(
                summary['top1_keyword_coverage'] - base['top1_keyword_coverage'],
                4
            ),
            'answer_hit_at_1_delta': round(summary['answer_hit_at_1'] - base['answer_hit_at_1'], 4)
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
    dataset = load_dataset(Path(args.dataset))
    app = create_app()

    with app.app_context():
        rag_service = RAGService()
        baseline_rows, baseline_summary = evaluate_mode(
            rag_service,
            dataset,
            top_k=args.top_k,
            use_rerank=False
        )
        rerank_rows, rerank_summary = evaluate_mode(
            rag_service,
            dataset,
            top_k=args.top_k,
            use_rerank=True
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
    dataset = load_dataset(Path(args.dataset))
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
                        strategy_name=strategy_name
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
    args = parser.parse_args()

    if args.compare_chunk_strategies:
        run_chunk_strategy_evaluation(args)
    else:
        run_standard_evaluation(args)


if __name__ == '__main__':
    main()
