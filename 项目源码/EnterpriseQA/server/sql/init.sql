-- ============================================
-- 企业内部知识库问答系统 - 数据库初始化脚本
-- 数据库名: db_enterprise_qa
-- MySQL端口: 3308
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS db_enterprise_qa DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE db_enterprise_qa;

-- ============================================
-- 用户表
-- ============================================
DROP TABLE IF EXISTS t_chat_history;
DROP TABLE IF EXISTS t_document;
DROP TABLE IF EXISTS t_knowledge_base;
DROP TABLE IF EXISTS t_user;

CREATE TABLE t_user (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(64) NOT NULL COMMENT '密码（MD5加密）',
    nickname VARCHAR(50) DEFAULT '' COMMENT '昵称',
    role VARCHAR(10) NOT NULL DEFAULT 'user' COMMENT '角色：admin-管理员，user-普通用户',
    avatar VARCHAR(255) DEFAULT '' COMMENT '头像地址',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-启用，0-禁用',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 知识库表
-- ============================================
CREATE TABLE t_knowledge_base (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '知识库ID',
    kb_name VARCHAR(100) NOT NULL COMMENT '知识库名称',
    description VARCHAR(500) DEFAULT '' COMMENT '知识库描述',
    creator_id INT NOT NULL COMMENT '创建者ID',
    doc_count INT NOT NULL DEFAULT 0 COMMENT '文档数量',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-正常，0-禁用',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (creator_id) REFERENCES t_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库表';

-- ============================================
-- 文档表
-- ============================================
CREATE TABLE t_document (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '文档ID',
    kb_id INT NOT NULL COMMENT '所属知识库ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    file_size BIGINT NOT NULL DEFAULT 0 COMMENT '文件大小（字节）',
    file_type VARCHAR(20) NOT NULL COMMENT '文件类型：txt/pdf/md/docx',
    chunk_count INT NOT NULL DEFAULT 0 COMMENT '分块数量',
    status VARCHAR(20) NOT NULL DEFAULT 'uploading' COMMENT '状态：uploading-上传中，vectorized-已向量化，failed-失败',
    creator_id INT NOT NULL COMMENT '上传者ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (kb_id) REFERENCES t_knowledge_base(id),
    FOREIGN KEY (creator_id) REFERENCES t_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表';

-- ============================================
-- 对话历史表
-- ============================================
CREATE TABLE t_chat_history (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    kb_id INT NOT NULL COMMENT '知识库ID',
    session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
    question TEXT NOT NULL COMMENT '用户提问',
    answer TEXT NOT NULL COMMENT 'AI回答',
    source_docs TEXT DEFAULT NULL COMMENT '参考文档来源（JSON格式）',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES t_user(id),
    FOREIGN KEY (kb_id) REFERENCES t_knowledge_base(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史表';

-- ============================================
-- 插入测试数据
-- ============================================

-- 管理员账号: admin / 123456 (MD5加密)
-- 普通用户: user1 / 123456, user2 / 123456
INSERT INTO t_user (username, password, nickname, role, status) VALUES
('admin', 'e10adc3949ba59abbe56e057f20f883e', '系统管理员', 'admin', 1),
('user1', 'e10adc3949ba59abbe56e057f20f883e', '张三', 'user', 1),
('user2', 'e10adc3949ba59abbe56e057f20f883e', '李四', 'user', 1);

-- 测试知识库
INSERT INTO t_knowledge_base (kb_name, description, creator_id, doc_count, status) VALUES
('公司规章制度', '包含公司各项规章制度、员工手册等文档', 1, 0, 1),
('技术文档库', '包含技术规范、API文档、开发指南等', 1, 0, 1),
('产品帮助中心', '产品使用指南、常见问题解答等', 1, 0, 1);

-- 测试对话记录
INSERT INTO t_chat_history (user_id, kb_id, session_id, question, answer, source_docs) VALUES
(2, 1, 'session_001', '公司的上班时间是什么？', '根据公司规章制度，公司的上班时间为每周一至周五，上午9:00至下午6:00，中午12:00-13:00为午休时间。', '[{"file_name": "员工手册.pdf", "content": "上班时间为每周一至周五..."}]'),
(2, 2, 'session_002', 'API接口的认证方式是什么？', '系统API接口采用JWT Token认证方式，用户登录后获取Token，在后续请求的Header中携带Authorization字段。', '[{"file_name": "API文档.md", "content": "认证方式采用JWT Token..."}]'),
(3, 1, 'session_003', '请假流程是怎样的？', '根据公司制度，请假需要提前在OA系统中提交申请，经直属主管审批后生效。病假需提供医院证明。', '[{"file_name": "考勤制度.pdf", "content": "请假需提前申请..."}]');
