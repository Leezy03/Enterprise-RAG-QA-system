"""Build the production RAG evaluation set.

The first 28 cases are the original baseline set. This script appends
production-oriented cases for multi-turn follow-up, no-answer refusal,
synonym paraphrase, similar-clause interference, and cross-document QA.
"""

import json
from collections import Counter
from pathlib import Path


TARGET_SIZE = 120
ORIGINAL_BASELINE_SIZE = 28
OUTPUT_PATH = Path(__file__).with_name("rag_eval_set.json")


def normalize_original_cases(cases):
    normalized = []
    for item in cases[:ORIGINAL_BASELINE_SIZE]:
        item = dict(item)
        item.setdefault("type", "single_turn")
        item.setdefault("category", "single_fact")
        item.setdefault("eval_dimension", "retrieval")
        item.setdefault("expected_answer_keywords", list(item.get("expected_keywords", [])))
        normalized.append(item)
    return normalized


def append_case(
    items,
    ids,
    case_id,
    question,
    kb_name,
    expected_sources=None,
    expected_keywords=None,
    expected_answer_keywords=None,
    category="single_fact",
    case_type="single_turn",
    eval_dimension="retrieval",
    conversation_history=None,
    expected_retrieval_query=None,
    rewritten_question_keywords=None,
    paired_with=None,
    should_refuse=False,
    negative_keywords=None,
):
    if case_id in ids:
        raise ValueError(f"duplicate case id: {case_id}")
    ids.add(case_id)

    item = {
        "id": case_id,
        "kb_name": kb_name,
        "question": question,
        "type": case_type,
        "category": category,
        "eval_dimension": eval_dimension,
        "expected_sources": expected_sources or [],
        "expected_keywords": expected_keywords or [],
        "expected_answer_keywords": (
            expected_answer_keywords
            if expected_answer_keywords is not None
            else list(expected_keywords or [])
        ),
    }
    if conversation_history:
        item["conversation_history"] = conversation_history
    if expected_retrieval_query:
        item["expected_retrieval_query"] = expected_retrieval_query
    if rewritten_question_keywords:
        item["rewritten_question_keywords"] = rewritten_question_keywords
    if paired_with:
        item["paired_with"] = paired_with
    if should_refuse:
        item["expected_answerable"] = False
        item["expected_refusal"] = True
    if negative_keywords:
        item["negative_keywords"] = negative_keywords

    items.append(item)


def build_cases(items):
    ids = {item["id"] for item in items}
    policy_kb = "公司规章制度"
    tech_kb = "技术文档库"
    product_kb = "产品帮助中心"

    policy_cases = [
        ("policy_flexible_clock", "公司弹性打卡允许提前或延后多久？", ["公司考勤管理制度.txt"], ["30分钟", "弹性打卡", "08:30-09:30"], "single_fact"),
        ("policy_core_work_time", "考勤制度中的核心工作时间是什么？", ["公司考勤管理制度.txt"], ["核心工作时间", "10:00-16:00"], "single_fact"),
        ("policy_missing_clock_process", "员工漏打卡后应该怎么补卡？", ["公司考勤管理制度.txt"], ["漏打卡", "OA系统", "24小时内"], "single_fact"),
        ("policy_missing_clock_limit", "每个月最多允许几次漏打卡补卡？", ["公司考勤管理制度.txt"], ["每月", "3次", "漏打卡"], "single_fact"),
        ("policy_late_under_30", "迟到30分钟以内会怎么处理？", ["公司考勤管理制度.txt"], ["迟到", "30分钟以内", "50元"], "similar_distractor"),
        ("policy_late_30_to_60", "迟到30分钟到1小时之间会怎么处理？", ["公司考勤管理制度.txt"], ["迟到30分钟至1小时", "100元"], "similar_distractor"),
        ("policy_absence_one_day_salary", "旷工一天扣多少工资？", ["公司考勤管理制度.txt"], ["旷工1天", "扣除3天工资"], "single_fact"),
        ("policy_absence_termination_condition", "连续旷工或累计旷工达到什么程度会解除劳动合同？", ["公司考勤管理制度.txt"], ["连续旷工3天", "累计旷工5天", "解除劳动合同"], "similar_distractor"),
        ("policy_overtime_workday_pay", "工作日加班工资按什么比例计算？", ["公司薪酬福利制度.pdf"], ["工作日加班", "150%"], "similar_distractor"),
        ("policy_overtime_weekend_pay", "周末加班工资按什么比例计算？", ["公司薪酬福利制度.pdf"], ["周末加班", "200%"], "similar_distractor"),
        ("policy_overtime_holiday_pay", "法定节假日加班工资按什么比例计算？", ["公司薪酬福利制度.pdf"], ["法定节假日", "300%"], "similar_distractor"),
        ("policy_annual_leave_under_10", "工龄不满10年的员工年假有几天？", ["员工请假管理办法.md"], ["工作满1年不满10年", "5天"], "single_fact"),
        ("policy_annual_leave_over_20", "工龄满20年的员工年假有几天？", ["员工请假管理办法.md"], ["已满20年", "15天"], "single_fact"),
        ("policy_personal_leave_salary", "事假期间工资如何计算？", ["员工请假管理办法.md"], ["事假期间", "不发放工资"], "single_fact"),
        ("policy_sick_leave_1_3_approval", "请1到3天病假需要谁审批？", ["员工请假管理办法.md"], ["1-3天", "部门经理审批"], "similar_distractor"),
        ("policy_sick_leave_over_3_approval", "请3天以上病假需要哪些人审批？", ["员工请假管理办法.md"], ["3天以上", "部门经理", "人力资源部"], "similar_distractor"),
        ("policy_maternity_leave_days", "女员工产假是多少天？", ["员工请假管理办法.md"], ["产假", "98天"], "single_fact"),
        ("policy_leave_unapproved_absence_cross", "请假未获批准但员工没来上班，会按什么处理？", ["员工请假管理办法.md", "公司考勤管理制度.txt"], ["未经批准", "未到岗", "旷工"], "cross_document"),
        ("policy_full_attendance_bonus_cross", "如果员工迟到或旷工，会影响当月全勤奖吗？", ["公司薪酬福利制度.pdf", "公司考勤管理制度.txt"], ["全勤奖", "无迟到", "无旷工", "200元"], "cross_document"),
        ("policy_salary_components", "员工月度工资由哪些部分组成？", ["公司薪酬福利制度.pdf"], ["基本工资", "绩效工资", "岗位津贴", "加班费"], "single_fact"),
        ("policy_salary_pay_day", "公司每月什么时候发放上月工资？", ["公司薪酬福利制度.pdf"], ["每月10日", "上月工资"], "single_fact"),
        ("policy_confidentiality_obligation", "员工对客户信息和商业秘密有什么保密要求？", ["员工行为规范手册.docx"], ["保密义务", "客户信息", "商业秘密"], "single_fact"),
    ]
    for case_id, question, sources, keywords, category in policy_cases:
        append_case(items, ids, case_id, question, policy_kb, sources, keywords, category=category)

    tech_cases = [
        ("tech_db_name_rule", "数据库名应该采用什么命名规则？", ["数据库设计规范.pdf"], ["数据库命名", "小写字母", "下划线"], "single_fact"),
        ("tech_table_name_rule", "数据表命名有什么要求？", ["数据库设计规范.pdf"], ["表名", "小写字母", "下划线", "业务含义"], "single_fact"),
        ("tech_primary_key_rule", "每张业务表的主键应该如何设计？", ["数据库设计规范.pdf"], ["主键", "id", "BIGINT", "自增"], "single_fact"),
        ("tech_status_field_rule", "业务表的状态字段推荐怎么设计？", ["数据库设计规范.pdf"], ["status", "TINYINT", "默认值"], "single_fact"),
        ("tech_normal_index_name", "普通索引的命名规范是什么？", ["数据库设计规范.pdf"], ["普通索引", "idx_表名_字段名"], "similar_distractor"),
        ("tech_unique_index_name", "唯一索引的命名规范是什么？", ["数据库设计规范.pdf"], ["唯一索引", "uk_表名_字段名"], "similar_distractor"),
        ("tech_decimal_money_rule", "金额字段为什么推荐使用DECIMAL而不是浮点类型？", ["数据库设计规范.pdf"], ["金额", "DECIMAL", "精度丢失"], "similar_distractor"),
        ("tech_time_type_rule", "创建时间和更新时间字段应该使用什么类型？", ["数据库设计规范.pdf"], ["created_at", "updated_at", "DATETIME"], "similar_distractor"),
        ("tech_sql_parameterized", "API和数据库规范中如何避免SQL注入？", ["API接口设计规范.md", "数据库设计规范.pdf"], ["参数化查询", "SQL注入", "禁止拼接"], "cross_document"),
        ("tech_db_root_forbidden", "数据库连接为什么禁止使用root账户？", ["数据库设计规范.pdf"], ["禁止使用root账户", "最小权限原则"], "single_fact"),
        ("tech_api_https_version", "API接口路径需要满足哪些版本和协议要求？", ["API接口设计规范.md"], ["HTTPS", "/api/v1", "版本号"], "single_fact"),
        ("tech_api_required_headers", "API请求头必须包含哪些字段？", ["API接口设计规范.md"], ["Content-Type", "Authorization", "X-Request-ID"], "single_fact"),
        ("tech_api_response_structure", "统一API响应结构包含哪些字段？", ["API接口设计规范.md"], ["code", "message", "data", "timestamp"], "single_fact"),
        ("tech_api_status_401_403", "401和403错误分别表示什么？", ["API接口设计规范.md"], ["401", "未授权", "403", "禁止访问"], "similar_distractor"),
        ("tech_api_token_expiration", "访问令牌和刷新令牌分别多久过期？", ["API接口设计规范.md"], ["访问令牌", "2小时", "刷新令牌", "7天"], "single_fact"),
        ("tech_api_rate_limit_login", "登录接口的限流规则是什么？", ["API接口设计规范.md"], ["登录接口", "5次/分钟"], "similar_distractor"),
        ("tech_api_rate_limit_upload", "文件上传接口的限流规则是什么？", ["API接口设计规范.md"], ["文件上传接口", "10次/分钟"], "similar_distractor"),
        ("tech_python_module_name", "Python模块和包命名应该遵循什么风格？", ["Python开发编码规范.txt"], ["模块名", "包名", "小写字母", "下划线"], "single_fact"),
        ("tech_python_line_length", "Python代码每行长度建议限制是多少？", ["Python开发编码规范.txt"], ["行长度", "88字符"], "single_fact"),
        ("tech_git_main_branch", "main分支的用途是什么？", ["Git版本管理规范.docx"], ["main分支", "生产环境", "稳定代码"], "single_fact"),
        ("tech_git_feature_branch", "功能分支应该如何命名？", ["Git版本管理规范.docx"], ["feature/功能名称", "功能分支"], "similar_distractor"),
        ("tech_sensitive_info_cross", "代码和Git规范中对密码、密钥这类敏感信息有什么要求？", ["Python开发编码规范.txt", "Git版本管理规范.docx"], ["敏感信息", "密码", "API密钥", "提交"], "cross_document"),
    ]
    for case_id, question, sources, keywords, category in tech_cases:
        append_case(items, ids, case_id, question, tech_kb, sources, keywords, category=category)

    product_cases = [
        ("product_oa_url", "企业OA系统的访问地址是什么？", ["企业OA系统使用手册.txt"], ["oa.company.com"], "single_fact"),
        ("product_oa_first_login_account", "新员工首次登录OA系统时账号和初始密码是什么？", ["企业OA系统使用手册.txt", "新员工入职指南.docx"], ["员工工号", "身份证后6位", "首次登录"], "cross_document"),
        ("product_oa_password_expire", "OA密码有效期是多久？", ["企业OA系统使用手册.txt"], ["密码有效期", "90天"], "single_fact"),
        ("product_oa_launch_process", "在OA里如何发起流程申请？", ["企业OA系统使用手册.txt"], ["流程管理", "发起流程", "选择流程类型"], "single_fact"),
        ("product_oa_common_process_types", "OA系统常用流程包括哪些？", ["企业OA系统使用手册.txt"], ["请假申请", "报销申请", "采购申请", "用章申请"], "single_fact"),
        ("product_oa_document_upload_limit", "OA文档上传支持哪些格式，单个文件最大多大？", ["企业OA系统使用手册.txt"], ["PDF", "Word", "Excel", "50MB"], "similar_distractor"),
        ("product_email_format", "企业邮箱账号格式是什么？", ["企业邮箱配置说明.pdf"], ["邮箱账号格式", "姓名拼音@company.com"], "single_fact"),
        ("product_email_web_login", "企业邮箱Web端登录地址是什么？", ["企业邮箱配置说明.pdf"], ["mail.company.com"], "single_fact"),
        ("product_email_imap_config", "企业邮箱IMAP服务器和端口如何配置？", ["企业邮箱配置说明.pdf"], ["IMAP", "imap.company.com", "993", "SSL"], "similar_distractor"),
        ("product_email_smtp_config", "企业邮箱SMTP服务器和端口如何配置？", ["企业邮箱配置说明.pdf"], ["SMTP", "smtp.company.com", "587", "STARTTLS"], "similar_distractor"),
        ("product_email_change_password", "企业邮箱密码应该在哪里修改？", ["企业邮箱配置说明.pdf"], ["邮箱设置", "账户安全", "修改密码"], "single_fact"),
        ("product_onboarding_materials", "新员工入职当天需要提交哪些材料？", ["新员工入职指南.docx"], ["身份证复印件", "学历证书", "银行卡复印件", "体检报告"], "single_fact"),
        ("product_onboarding_contract_confidentiality", "新员工入职当天需要签署哪些协议？", ["新员工入职指南.docx", "员工行为规范手册.docx"], ["劳动合同", "保密协议", "员工手册确认书"], "cross_document"),
        ("product_canteen_time", "公司午餐和晚餐分别在什么时间供应？", ["新员工入职指南.docx"], ["午餐", "11:30-13:30", "晚餐", "17:30-19:30"], "single_fact"),
        ("product_probation_two_months", "试用期2个月适用于哪类合同期限？", ["新员工入职指南.docx"], ["试用期2个月", "1年以上不满3年"], "similar_distractor"),
        ("product_probation_three_months", "试用期3个月适用于哪类合同期限？", ["新员工入职指南.docx"], ["试用期3个月", "3年以上"], "similar_distractor"),
        ("product_pm_url", "项目管理平台的访问地址是什么？", ["项目管理平台操作指南.md"], ["pm.company.com"], "single_fact"),
        ("product_pm_project_number_format", "项目编号格式是什么样的？", ["项目管理平台操作指南.md"], ["PRJ-YYYY-NNN", "项目编号"], "single_fact"),
        ("product_pm_task_types", "项目管理平台支持哪些任务类型？", ["项目管理平台操作指南.md"], ["开发任务", "测试任务", "设计任务", "文档任务", "会议任务"], "single_fact"),
        ("product_pm_task_flow", "项目任务状态流转顺序是什么？", ["项目管理平台操作指南.md"], ["待开始", "进行中", "待测试", "已完成"], "single_fact"),
        ("product_pm_doc_types", "项目管理平台支持上传哪些文档类型？", ["项目管理平台操作指南.md"], ["需求文档", "设计文档", "测试用例", "会议纪要"], "single_fact"),
        ("product_pm_export_report", "项目管理平台可以导出哪些项目报告？", ["项目管理平台操作指南.md"], ["项目进度报告", "工时统计报表", "任务完成情况", "团队绩效报告"], "single_fact"),
    ]
    for case_id, question, sources, keywords, category in product_cases:
        append_case(items, ids, case_id, question, product_kb, sources, keywords, category=category)

    synonym_cases = [
        ("syn_policy_late_gt1_a", "迟到超过一个小时算什么？", policy_kb, ["公司考勤管理制度.txt"], ["迟到超过1小时", "旷工半天"], "syn_policy_late_gt1_b"),
        ("syn_policy_late_gt1_b", "晚到60分钟以上会被如何认定？", policy_kb, ["公司考勤管理制度.txt"], ["迟到超过1小时", "旷工半天"], "syn_policy_late_gt1_a"),
        ("syn_policy_leave_5_a", "请五天事假要谁批？", policy_kb, ["员工请假管理办法.md"], ["3天以上", "部门经理", "人力资源部"], "syn_policy_leave_5_b"),
        ("syn_policy_leave_5_b", "事假超过三天的审批链路是什么？", policy_kb, ["员工请假管理办法.md"], ["3天以上", "部门经理", "人力资源部"], "syn_policy_leave_5_a"),
        ("syn_tech_api_deprecated_a", "接口废弃后多久下线？", tech_kb, ["API接口设计规范.md"], ["接口废弃", "至少提前30天", "废弃通知"], "syn_tech_api_deprecated_b"),
        ("syn_tech_api_deprecated_b", "老API停止服务前需要提前多长时间通知？", tech_kb, ["API接口设计规范.md"], ["接口废弃", "至少提前30天", "废弃通知"], "syn_tech_api_deprecated_a"),
        ("syn_tech_select_star_a", "SQL查询能不能直接select *？", tech_kb, ["数据库设计规范.pdf"], ["避免SELECT *", "明确字段名"], "syn_tech_select_star_b"),
        ("syn_tech_select_star_b", "数据库查询是否允许使用星号返回所有列？", tech_kb, ["数据库设计规范.pdf"], ["避免SELECT *", "明确字段名"], "syn_tech_select_star_a"),
        ("syn_product_oa_lock_a", "OA账号输错密码几次会被锁？", product_kb, ["企业OA系统使用手册.txt"], ["连续5次", "账户锁定", "30分钟"], "syn_product_oa_lock_b"),
        ("syn_product_oa_lock_b", "OA登录失败达到多少次会临时锁定账号？", product_kb, ["企业OA系统使用手册.txt"], ["连续5次", "账户锁定", "30分钟"], "syn_product_oa_lock_a"),
    ]
    for case_id, question, kb_name, sources, keywords, paired_with in synonym_cases:
        append_case(
            items,
            ids,
            case_id,
            question,
            kb_name,
            sources,
            keywords,
            category="synonym_paraphrase",
            case_type="synonym",
            eval_dimension="robustness",
            paired_with=paired_with,
        )

    follow_up_cases = [
        ("follow_policy_annual_11", "那11年呢？", "工龄11年的员工年假有几天？", policy_kb, ["员工请假管理办法.md"], ["工作满10年不满20年", "10天"], [{"role": "user", "content": "工龄不满10年的员工年假有几天？"}, {"role": "assistant", "content": "工作满1年不满10年的员工年休假为5天。"}], ["工龄", "11年", "年假"]),
        ("follow_policy_sick_pay_6", "如果是6天呢？", "病假6天期间工资怎么发？", policy_kb, ["员工请假管理办法.md"], ["病假4-15天", "70%"], [{"role": "user", "content": "病假3天以内工资怎么发？"}, {"role": "assistant", "content": "病假1-3天期间发放基本工资的80%。"}], ["病假", "6天", "工资"]),
        ("follow_policy_overtime_weekend", "周末呢？", "周末加班工资按什么比例计算？", policy_kb, ["公司薪酬福利制度.pdf"], ["周末加班", "200%"], [{"role": "user", "content": "工作日加班按多少比例算？"}, {"role": "assistant", "content": "工作日加班工资按150%计算。"}], ["周末加班", "工资", "比例"]),
        ("follow_tech_api_token", "刷新令牌呢？", "刷新令牌多久过期？", tech_kb, ["API接口设计规范.md"], ["刷新令牌", "7天"], [{"role": "user", "content": "访问令牌多久过期？"}, {"role": "assistant", "content": "访问令牌有效期为2小时。"}], ["刷新令牌", "过期"]),
        ("follow_tech_git_release", "发布分支呢？", "发布分支应该如何命名？", tech_kb, ["Git版本管理规范.docx"], ["release/版本号", "发布分支"], [{"role": "user", "content": "功能分支怎么命名？"}, {"role": "assistant", "content": "功能分支命名为feature/功能名称。"}], ["发布分支", "命名"]),
        ("follow_tech_db_index", "唯一索引呢？", "唯一索引的命名规范是什么？", tech_kb, ["数据库设计规范.pdf"], ["唯一索引", "uk_表名_字段名"], [{"role": "user", "content": "普通索引怎么命名？"}, {"role": "assistant", "content": "普通索引命名格式为idx_表名_字段名。"}], ["唯一索引", "命名规范"]),
        ("follow_product_email_smtp", "发信服务器呢？", "企业邮箱SMTP发信服务器如何配置？", product_kb, ["企业邮箱配置说明.pdf"], ["SMTP", "smtp.company.com", "587"], [{"role": "user", "content": "企业邮箱收信服务器怎么配置？"}, {"role": "assistant", "content": "IMAP服务器为imap.company.com，端口993。"}], ["SMTP", "发信服务器", "配置"]),
        ("follow_product_pm_task_flow", "任务状态怎么流转？", "项目管理平台任务状态如何流转？", product_kb, ["项目管理平台操作指南.md"], ["待开始", "进行中", "待测试", "已完成"], [{"role": "user", "content": "项目管理平台有哪些任务类型？"}, {"role": "assistant", "content": "支持开发、测试、设计、文档和会议任务。"}], ["任务状态", "流转"]),
    ]
    for case_id, question, expected_query, kb_name, sources, keywords, history, rewrite_keywords in follow_up_cases:
        append_case(
            items,
            ids,
            case_id,
            question,
            kb_name,
            sources,
            keywords,
            category="multi_turn_followup",
            case_type="follow_up",
            eval_dimension="multi_turn",
            conversation_history=history,
            expected_retrieval_query=expected_query,
            rewritten_question_keywords=rewrite_keywords,
        )

    no_answer_cases = [
        ("no_policy_pet_insurance", "公司是否提供宠物医疗保险？", policy_kb, ["宠物医疗保险"]),
        ("no_policy_remote_work", "公司远程办公每周最多可以申请几天？", policy_kb, ["远程办公", "每周"]),
        ("no_policy_stock_option", "员工期权归属周期是几年？", policy_kb, ["期权", "归属周期"]),
        ("no_tech_k8s_deploy", "Kubernetes生产发布的灰度策略是什么？", tech_kb, ["Kubernetes", "灰度策略"]),
        ("no_tech_java_style", "Java代码的包名规范是什么？", tech_kb, ["Java", "包名规范"]),
        ("no_product_vpn_setup", "公司VPN客户端如何配置？", product_kb, ["VPN", "客户端配置"]),
        ("no_product_crm_password", "CRM系统密码忘记后如何重置？", product_kb, ["CRM", "密码重置"]),
        ("no_product_travel_booking", "差旅机票应该在哪个系统预订？", product_kb, ["差旅", "机票预订"]),
    ]
    for case_id, question, kb_name, negative_keywords in no_answer_cases:
        append_case(
            items,
            ids,
            case_id,
            question,
            kb_name,
            category="no_answer_refusal",
            case_type="no_answer",
            eval_dimension="robustness",
            should_refuse=True,
            negative_keywords=negative_keywords,
        )

    return items


def main():
    source_cases = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    items = normalize_original_cases(source_cases)
    build_cases(items)

    if len(items) != TARGET_SIZE:
        raise SystemExit(f"Expected {TARGET_SIZE} cases, got {len(items)}")

    OUTPUT_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {len(items)} cases to {OUTPUT_PATH}")
    print("By category:", dict(Counter(item.get("category") for item in items)))
    print("By dimension:", dict(Counter(item.get("eval_dimension") for item in items)))


if __name__ == "__main__":
    main()
