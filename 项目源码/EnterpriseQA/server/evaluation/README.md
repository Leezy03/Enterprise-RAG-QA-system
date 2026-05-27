# RAG评测说明

本目录中的 `evaluate_rag.py` 支持检索级、生成级、引用级、多轮级和鲁棒性评测。

## 运行方式

重建120条生产级评测集：

```powershell
python evaluation\build_eval_set.py
```

只评估检索与引用片段：

```powershell
python evaluation\evaluate_rag.py
```

当前默认链路为 Hybrid Baseline + 轻量 Rerank：向量召回和BM25召回经RRF融合后，再用 `hybrid_score`、`vector_score`、`keyword_score` 和 `filename_score` 做规则重排。

同时调用LLM生成答案，启用生成级和无答案拒答评测：

```powershell
python evaluation\evaluate_rag.py --include-generation
```

只对指定样本子集跑生成级评测，避免全量LLM调用耗时过长：

```powershell
python evaluation\evaluate_rag.py --include-generation --filter-category no_answer_refusal
python evaluation\evaluate_rag.py --include-generation --filter-category cross_document
```

对比chunk策略：

```powershell
python evaluation\evaluate_rag.py --compare-chunk-strategies
```

## 评测集规模

当前 `rag_eval_set.json` 共120条样本，三个知识库各40条：

- `single_fact`：67条，覆盖普通事实型问答。
- `similar_distractor`：21条，覆盖迟到区间、加班比例、索引命名、邮箱端口等相似条款干扰。
- `cross_document`：6条，覆盖跨制度、跨技术文档和跨产品指南的问题。
- `synonym_paraphrase`：10条，覆盖同义改写一致性。
- `multi_turn_followup`：8条，覆盖多轮追问和标准独立问题检索。
- `no_answer_refusal`：8条，覆盖知识库无答案时的拒答能力。

## 指标说明

- `Hit@K`：TopK片段中是否至少命中一个预期来源。
- `Recall@K`：TopK片段覆盖了多少比例的预期来源。
- `Precision@K`：TopK片段中有多少比例来自预期来源。
- `NDCG@K`：预期来源是否排在更靠前的位置。
- `MRR`：第一个预期来源出现排名的倒数均值。
- `Answer Correctness`：生成答案对预期关键词/标准答案terms的覆盖率，启发式计算。
- `Faithfulness / Groundedness`：答案中的事实terms有多少能在检索上下文中找到，启发式计算。
- `Completeness`：生成答案对预期关键词的覆盖率。
- `Hallucination Rate`：`1 - Faithfulness`，作为幻觉率的启发式估计。
- `Citation Precision`：返回引用中有多少比例命中预期来源。
- `Citation Recall`：返回引用覆盖了多少比例的预期来源。
- `Citation Support`：引用片段对预期关键词的覆盖率。
- `Query Rewrite Accuracy`：多轮样本中，改写后的检索问题对预期独立问题terms的覆盖率。
- `Follow-up Retrieval Hit@K`：多轮追问样本的Hit@K。
- `No-answer Refusal Accuracy`：无答案样本中，生成答案是否明确拒答。
- `Synonym Retrieval Consistency`：同义改写样本组的检索来源一致性。
- `Synonym Answer Consistency`：同义改写样本组的生成答案terms一致性。

生成级指标当前是启发式评估，适合本地快速回归；生产级评测可以进一步接入LLM-as-Judge或人工标注。默认评测不调用LLM生成答案，因此生成级和无答案拒答指标需要加 `--include-generation`。

## 样本字段

基础检索样本：

```json
{
  "id": "policy_leave_over_5_days",
  "kb_name": "公司规章制度",
  "question": "请假超过5天需要谁审批？",
  "expected_sources": ["员工请假管理办法.md"],
  "expected_keywords": ["分管副总", "人力资源部", "部门负责人"]
}
```

可选生成级字段：

```json
{
  "expected_answer": "请假超过5天需要部门负责人、分管副总和人力资源部审批。",
  "expected_answer_keywords": ["部门负责人", "分管副总", "人力资源部"]
}
```

可选多轮字段：

```json
{
  "conversation_history": [
    {
      "role": "user",
      "content": "请假审批规则是什么？"
    },
    {
      "role": "assistant",
      "content": "请假天数不同，对应不同审批人。"
    }
  ],
  "question": "那超过5天呢？",
  "expected_retrieval_query": "请假超过5天需要谁审批？",
  "rewritten_question_keywords": ["请假", "超过5天", "审批"]
}
```

可选无答案字段：

```json
{
  "type": "no_answer",
  "expected_answerable": false,
  "question": "公司是否提供宠物医疗报销？"
}
```

可选同义改写字段：

```json
{
  "paired_with": "syn_leave_over_5_b",
  "question": "请假超过5天需要谁审批？"
}
```
