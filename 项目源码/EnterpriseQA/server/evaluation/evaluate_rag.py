"""
RAG检索评测脚本

用途：
1. 对比基础向量检索与“向量召回 + Rerank”的检索效果
2. 输出来源命中率、Top1命中率、MRR、关键词覆盖率等指标
3. 生成可用于简历量化表达的评测摘要

运行方式（在 server 目录执行）：
    python evaluation/evaluate_rag.py
"""
import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path

os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')
logging.getLogger('chromadb.telemetry.product.posthog').disabled = True


SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app import create_app  # noqa: E402
from models import db  # noqa: E402
from models.document import Document  # noqa: E402
from models.knowledge_base import KnowledgeBase  # noqa: E402
from services.rag_service import RAGService  # noqa: E402


DEFAULT_DATASET = Path(__file__).with_name('rag_eval_set.json')
DEFAULT_OUTPUT_DIR = Path(__file__).with_name('results')
ANSWER_HIT_THRESHOLD = 0.67


def load_dataset(path):
    """加载评测集"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_kb_id(item):
    """根据评测样本中的kb_id或kb_name解析知识库ID"""
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
    """根据文档ID获取原始文件名"""
    if doc_id is None:
        return ''
    try:
        document = db.session.get(Document, int(doc_id))
    except (TypeError, ValueError):
        document = None
    return document.file_name if document else ''


def source_names(doc):
    """收集一个检索片段可能对应的来源文件名"""
    metadata = doc.metadata or {}
    names = {
        metadata.get('file_name', ''),
        metadata.get('stored_file_name', ''),
        get_document_name(metadata.get('doc_id'))
    }
    return {name for name in names if name}


def source_hit(doc, expected_sources):
    """判断单个片段是否命中预期来源"""
    actual_names = {name.lower() for name in source_names(doc)}
    expected_names = [name.lower() for name in expected_sources]

    for actual in actual_names:
        for expected in expected_names:
            if actual == expected or actual in expected or expected in actual:
                return True
    return False


def first_hit_rank(docs, expected_sources):
    """返回第一个命中预期来源的排名，未命中返回None"""
    for index, doc in enumerate(docs, 1):
        if source_hit(doc, expected_sources):
            return index
    return None


def keyword_coverage(docs, expected_keywords):
    """计算TopK片段对预期关键词的覆盖比例"""
    if not expected_keywords:
        return 0

    text = '\n'.join(doc.page_content or '' for doc in docs).lower()
    matched = 0
    for keyword in expected_keywords:
        if str(keyword).lower() in text:
            matched += 1
    return matched / len(expected_keywords)


def summarize_rows(rows):
    """汇总评测指标"""
    total = len(rows)
    if total == 0:
        return {
            'count': 0,
            'hit_at_k': 0,
            'hit_at_1': 0,
            'mrr': 0,
            'keyword_coverage': 0,
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


def evaluate_mode(rag_service, dataset, top_k, use_rerank):
    """按指定模式执行评测"""
    rows = []
    for item in dataset:
        kb_id = resolve_kb_id(item)
        docs = rag_service.retrieve_for_eval(
            item['question'],
            kb_id,
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
            'mode': 'rerank' if use_rerank else 'baseline',
            'first_hit_rank': rank,
            'hit_at_k': bool(rank),
            'reciprocal_rank': round(1 / rank, 4) if rank else 0,
            'keyword_coverage': round(keyword_coverage(docs, item.get('expected_keywords', [])), 4),
            'top1_keyword_coverage': round(top1_keyword_score, 4),
            'answer_hit_at_1': top1_keyword_score >= ANSWER_HIT_THRESHOLD,
            'top_sources': [
                {
                    'rank': index,
                    'file_names': sorted(source_names(doc)),
                    'vector_score': (doc.metadata or {}).get('vector_score'),
                    'rerank_score': (doc.metadata or {}).get('rerank_score'),
                    'chunk_index': (doc.metadata or {}).get('chunk_index')
                }
                for index, doc in enumerate(docs, 1)
            ]
        })

    return rows, summarize_rows(rows)


def pct(value):
    """格式化百分比"""
    return f'{value * 100:.1f}%'


def build_report(dataset, baseline_rows, baseline_summary, rerank_rows, rerank_summary):
    """构建完整评测报告"""
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


def write_outputs(report, output_dir):
    """写入JSON和CSV评测结果"""
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


def print_summary(report, json_path, csv_path):
    """打印评测摘要"""
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
    print(
        "样本变化: "
        f"{report['case_changes']['improved']} 提升 / "
        f"{report['case_changes']['worsened']} 下降 / "
        f"{report['case_changes']['unchanged']} 持平"
    )
    print(
        "Top1答案片段变化: "
        f"{report['case_changes']['answer_improved']} 提升 / "
        f"{report['case_changes']['answer_worsened']} 下降 / "
        f"{report['case_changes']['answer_unchanged']} 持平"
    )
    print('\n简历可用表述:')
    print(report['resume_summary'])
    print(f'\n报告文件: {json_path}')
    print(f'明细CSV: {csv_path}')


def main():
    parser = argparse.ArgumentParser(description='RAG检索与Rerank效果评测')
    parser.add_argument('--dataset', default=str(DEFAULT_DATASET), help='评测集JSON路径')
    parser.add_argument('--top-k', type=int, default=4, help='最终返回TopK')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR), help='评测结果输出目录')
    args = parser.parse_args()

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

        report = build_report(dataset, baseline_rows, baseline_summary, rerank_rows, rerank_summary)
        json_path, csv_path = write_outputs(report, Path(args.output_dir))
        print_summary(report, json_path, csv_path)


if __name__ == '__main__':
    main()
