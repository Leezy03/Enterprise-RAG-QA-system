/*
SQLyog Community v13.2.0 (64 bit)
MySQL - 8.1.0 : Database - db_enterprise_qa
*********************************************************************
*/

/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`db_enterprise_qa` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `db_enterprise_qa`;

/*Table structure for table `t_chat_history` */

DROP TABLE IF EXISTS `t_chat_history`;

CREATE TABLE `t_chat_history` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `kb_id` int NOT NULL COMMENT '知识库ID',
  `session_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '会话ID',
  `question` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户提问',
  `answer` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'AI回答',
  `source_docs` text COLLATE utf8mb4_unicode_ci COMMENT '参考文档来源（JSON格式）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `kb_id` (`kb_id`),
  CONSTRAINT `t_chat_history_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `t_user` (`id`),
  CONSTRAINT `t_chat_history_ibfk_2` FOREIGN KEY (`kb_id`) REFERENCES `t_knowledge_base` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史表';

/*Data for the table `t_chat_history` */

insert  into `t_chat_history`(`id`,`user_id`,`kb_id`,`session_id`,`question`,`answer`,`source_docs`,`create_time`) values 
(1,2,1,'session_001','公司的上班时间是什么？','根据公司规章制度，公司的上班时间为每周一至周五，上午9:00至下午6:00，中午12:00-13:00为午休时间。','[{\"file_name\": \"员工手册.pdf\", \"content\": \"上班时间为每周一至周五...\"}]','2026-03-21 18:20:17'),
(2,2,2,'session_002','API接口的认证方式是什么？','系统API接口采用JWT Token认证方式，用户登录后获取Token，在后续请求的Header中携带Authorization字段。','[{\"file_name\": \"API文档.md\", \"content\": \"认证方式采用JWT Token...\"}]','2026-03-21 18:20:17'),
(3,3,1,'session_003','请假流程是怎样的？','根据公司制度，请假需要提前在OA系统中提交申请，经直属主管审批后生效。病假需提供医院证明。','[{\"file_name\": \"考勤制度.pdf\", \"content\": \"请假需提前申请...\"}]','2026-03-21 18:20:17'),
(4,1,1,'sess_mn09qlp5eyrqjl','我工作11年，可以请几天年假？','根据公司《员工请假管理办法》第三条年假规定，员工累计工作满10年不满20年的，年休假为10天。您工作11年，符合该条件，因此可享受10天年假。','[{\"file_name\": \"061fc6f69b4c49949917d3b18466911a.md\", \"content\": \"# 员工请假管理办法\\n\\n## 第一章 总则\\n\\n### 第一条 目的\\n\\n为规范公司员工请假管理流程，保障员工合法休假权益，确保公司各项工作正常运转，特制定本办法。\\n\\n### 第二条 适用范围\\n\\n本办法适用于公司全体在职员工，包括试用期员工。\\n\\n## 第二章 假期类型\\n\\n### 第三条 年假\\n\\n- 员工累计工作满1年不满10年的，年休假5天\\n- 已满10年不满20年的，年休假10天\\n- 已满20年的，\"}]','2026-03-21 19:56:51'),
(5,1,2,'sess_mn09wxvts1c78e','我们公司的 注释规范 是啥样的？','根据提供的参考资料，我没有找到关于公司具体注释规范的详细内容。参考资料中只提到\"是否有足够的注释和文档\"是代码审查的一个要点（见来源2的4.2 代码审查要点），但没有规定具体的注释规范要求。\n\n参考资料中没有明确描述代码注释的格式、深度、内容要求等具体规范。如果您需要了解详细的注释规范，建议查阅公司内部的其他文档或直接咨询相关技术负责人。','[{\"file_name\": \"74b977bd9f8545dca742bf7efc73969c.docx\", \"content\": \"是否有足够的注释和文档。\\n4.3 冲突解决：\\n合并前须先将目标分支的最新代码合并到当前分支。\\n冲突须由功能开发者自行解决。\\n解决冲突后须重新测试。\\n五、版本发布流程\\n5.1 版本号规范（语义化版本）：\\n主版本号.次版本号.修订号（如1.2.3）\\n主版本号：不兼容的API变更\\n次版本号：向下兼容的功能新增\\n修订号：向下兼容的问题修复\\n5.2 发布流程：\\n从develop分支创建release分支。\\n\"}, {\"file_name\": \"2ee9cc33b736429f97be205d94588829.pdf\", \"content\": \"唯一索引：uk_表名_字段名，如：uk_user_email。\\n联合索引：idx_表名_字段1_字段2，如：idx_order_user_id_status。\\n三、表设计规范\\n3.1 基本要求\\n所有表必须使用InnoDB存储引擎。\\n字符集统一使用utf8mb4，排序规则使用utf8mb4_unicode_ci。\\n所有表必须有主键，推荐使用自增整型主键。\\n所有表必须包含create_time和upd\"}, {\"file_name\": \"e2ece8ca7ec243d1aa66827b902896c0.md\", \"content\": \"## 七、文档规范\\n\\n### 7.1 接口文档\\n\\n- 每个API接口必须编写接口文档\\n- 文档内容包括：接口描述、请求方式、URL、请求参数、响应参数、示例\\n- 推荐使用Swagger/OpenAPI生成接口文档\\n\\n### 7.2 变更管理\\n\\n- API变更须向前兼容，不得直接修改已发布的接口\\n- 重大变更须升级版本号（如v1升级为v2）\\n- 废弃的接口须在文档中标注，并保留至少3个月\"}]','2026-03-21 19:59:23'),
(6,1,2,'sess_mn09wxvts1c78e','我们公司的 注释规范 是啥样的？','根据提供的参考资料，公司对注释的要求在文档中有所提及，但没有完整的注释规范细节。\n\n在参考资料[来源2]中明确提到：\"4.2 代码审查要点：...是否有足够的注释和文档。\"这表明注释是代码审查的重要检查项之一，公司要求代码中要有足够的注释和文档。\n\n此外，在参考资料[来源1]中也提到\"是否有足够的注释和文档\"作为相关事项，但未详细说明具体规范。\n\n综上所述，参考资料中仅表明公司要求代码中要有足够的注释和文档，但没有提供完整的注释规范细节。','[{\"file_name\": \"74b977bd9f8545dca742bf7efc73969c.docx\", \"content\": \"是否有足够的注释和文档。\\n4.3 冲突解决：\\n合并前须先将目标分支的最新代码合并到当前分支。\\n冲突须由功能开发者自行解决。\\n解决冲突后须重新测试。\\n五、版本发布流程\\n5.1 版本号规范（语义化版本）：\\n主版本号.次版本号.修订号（如1.2.3）\\n主版本号：不兼容的API变更\\n次版本号：向下兼容的功能新增\\n修订号：向下兼容的问题修复\\n5.2 发布流程：\\n从develop分支创建release分支。\\n\"}, {\"file_name\": \"2ee9cc33b736429f97be205d94588829.pdf\", \"content\": \"唯一索引：uk_表名_字段名，如：uk_user_email。\\n联合索引：idx_表名_字段1_字段2，如：idx_order_user_id_status。\\n三、表设计规范\\n3.1 基本要求\\n所有表必须使用InnoDB存储引擎。\\n字符集统一使用utf8mb4，排序规则使用utf8mb4_unicode_ci。\\n所有表必须有主键，推荐使用自增整型主键。\\n所有表必须包含create_time和upd\"}, {\"file_name\": \"e2ece8ca7ec243d1aa66827b902896c0.md\", \"content\": \"## 七、文档规范\\n\\n### 7.1 接口文档\\n\\n- 每个API接口必须编写接口文档\\n- 文档内容包括：接口描述、请求方式、URL、请求参数、响应参数、示例\\n- 推荐使用Swagger/OpenAPI生成接口文档\\n\\n### 7.2 变更管理\\n\\n- API变更须向前兼容，不得直接修改已发布的接口\\n- 重大变更须升级版本号（如v1升级为v2）\\n- 废弃的接口须在文档中标注，并保留至少3个月\"}]','2026-03-21 20:01:00'),
(7,1,2,'sess_mn09wxvts1c78e','我们公司的 注释规范 是啥样的？','根据提供的参考资料，公司内部确实提到了注释相关要求，但没有详细说明具体的注释规范内容。\n\n在参考资料[来源2]中，代码审查要点明确提到：\"是否有足够的注释和文档\"是代码审查的一个重要检查项。这表明公司对代码注释有基本要求，但参考资料中没有提供关于注释规范的具体细节，如注释的格式、内容要求、注释深度等。\n\n因此，参考资料中没有包含我们公司完整的注释规范内容，仅能确认注释是代码审查的必要检查项之一。如需了解详细的注释规范，建议查阅公司内部更完整的开发规范文档。','[{\"file_name\": \"74b977bd9f8545dca742bf7efc73969c.docx\", \"content\": \"是否有足够的注释和文档。\\n4.3 冲突解决：\\n合并前须先将目标分支的最新代码合并到当前分支。\\n冲突须由功能开发者自行解决。\\n解决冲突后须重新测试。\\n五、版本发布流程\\n5.1 版本号规范（语义化版本）：\\n主版本号.次版本号.修订号（如1.2.3）\\n主版本号：不兼容的API变更\\n次版本号：向下兼容的功能新增\\n修订号：向下兼容的问题修复\\n5.2 发布流程：\\n从develop分支创建release分支。\\n\"}, {\"file_name\": \"2ee9cc33b736429f97be205d94588829.pdf\", \"content\": \"唯一索引：uk_表名_字段名，如：uk_user_email。\\n联合索引：idx_表名_字段1_字段2，如：idx_order_user_id_status。\\n三、表设计规范\\n3.1 基本要求\\n所有表必须使用InnoDB存储引擎。\\n字符集统一使用utf8mb4，排序规则使用utf8mb4_unicode_ci。\\n所有表必须有主键，推荐使用自增整型主键。\\n所有表必须包含create_time和upd\"}, {\"file_name\": \"e2ece8ca7ec243d1aa66827b902896c0.md\", \"content\": \"## 七、文档规范\\n\\n### 7.1 接口文档\\n\\n- 每个API接口必须编写接口文档\\n- 文档内容包括：接口描述、请求方式、URL、请求参数、响应参数、示例\\n- 推荐使用Swagger/OpenAPI生成接口文档\\n\\n### 7.2 变更管理\\n\\n- API变更须向前兼容，不得直接修改已发布的接口\\n- 重大变更须升级版本号（如v1升级为v2）\\n- 废弃的接口须在文档中标注，并保留至少3个月\"}]','2026-03-21 20:02:54'),
(8,1,2,'sess_mn0a73i1ndfawh','我们公司的 注释规范 是啥样的？','根据提供的参考资料，我无法找到公司具体的注释规范详细内容。参考资料中只提到了\"是否有足够的注释和文档\"作为代码审查的一个要点（见来源2中4.2代码审查要点），但没有详细说明公司内部的注释规范要求。\n\n参考资料中没有提供关于代码注释规范的具体标准、格式或要求。如果您需要了解公司注释规范的详细内容，建议查询公司内部的代码规范文档或相关技术文档。','[{\"file_name\": \"74b977bd9f8545dca742bf7efc73969c.docx\", \"content\": \"是否有足够的注释和文档。\\n4.3 冲突解决：\\n合并前须先将目标分支的最新代码合并到当前分支。\\n冲突须由功能开发者自行解决。\\n解决冲突后须重新测试。\\n五、版本发布流程\\n5.1 版本号规范（语义化版本）：\\n主版本号.次版本号.修订号（如1.2.3）\\n主版本号：不兼容的API变更\\n次版本号：向下兼容的功能新增\\n修订号：向下兼容的问题修复\\n5.2 发布流程：\\n从develop分支创建release分支。\\n\"}, {\"file_name\": \"2ee9cc33b736429f97be205d94588829.pdf\", \"content\": \"唯一索引：uk_表名_字段名，如：uk_user_email。\\n联合索引：idx_表名_字段1_字段2，如：idx_order_user_id_status。\\n三、表设计规范\\n3.1 基本要求\\n所有表必须使用InnoDB存储引擎。\\n字符集统一使用utf8mb4，排序规则使用utf8mb4_unicode_ci。\\n所有表必须有主键，推荐使用自增整型主键。\\n所有表必须包含create_time和upd\"}, {\"file_name\": \"e2ece8ca7ec243d1aa66827b902896c0.md\", \"content\": \"## 七、文档规范\\n\\n### 7.1 接口文档\\n\\n- 每个API接口必须编写接口文档\\n- 文档内容包括：接口描述、请求方式、URL、请求参数、响应参数、示例\\n- 推荐使用Swagger/OpenAPI生成接口文档\\n\\n### 7.2 变更管理\\n\\n- API变更须向前兼容，不得直接修改已发布的接口\\n- 重大变更须升级版本号（如v1升级为v2）\\n- 废弃的接口须在文档中标注，并保留至少3个月\"}]','2026-03-21 20:06:38'),
(9,1,2,'sess_mn0afr0ol8knvs','我们公司的 注释规范 是啥样的？','根据提供的参考资料，我无法给出我们公司详细的注释规范内容。\n\n参考资料中只提到了\"是否有足够的注释和文档\"作为代码审查的一个要点（见[来源2]中的\"4.2 代码审查要点\"部分），但没有详细说明具体的注释规范要求。\n\n在所有参考资料中，没有找到关于代码注释规范的完整描述。参考资料主要涉及版本发布流程、提交规范、数据库设计规范和接口文档规范等内容，但未提供详细的注释规范说明。\n\n如果您需要了解具体的注释规范，建议查阅公司内部的代码规范文档或直接咨询相关技术负责人。','[{\"file_name\": \"74b977bd9f8545dca742bf7efc73969c.docx\", \"content\": \"是否有足够的注释和文档。\\n4.3 冲突解决：\\n合并前须先将目标分支的最新代码合并到当前分支。\\n冲突须由功能开发者自行解决。\\n解决冲突后须重新测试。\\n五、版本发布流程\\n5.1 版本号规范（语义化版本）：\\n主版本号.次版本号.修订号（如1.2.3）\\n主版本号：不兼容的API变更\\n次版本号：向下兼容的功能新增\\n修订号：向下兼容的问题修复\\n5.2 发布流程：\\n从develop分支创建release分支。\\n\"}, {\"file_name\": \"2ee9cc33b736429f97be205d94588829.pdf\", \"content\": \"唯一索引：uk_表名_字段名，如：uk_user_email。\\n联合索引：idx_表名_字段1_字段2，如：idx_order_user_id_status。\\n三、表设计规范\\n3.1 基本要求\\n所有表必须使用InnoDB存储引擎。\\n字符集统一使用utf8mb4，排序规则使用utf8mb4_unicode_ci。\\n所有表必须有主键，推荐使用自增整型主键。\\n所有表必须包含create_time和upd\"}, {\"file_name\": \"e2ece8ca7ec243d1aa66827b902896c0.md\", \"content\": \"## 七、文档规范\\n\\n### 7.1 接口文档\\n\\n- 每个API接口必须编写接口文档\\n- 文档内容包括：接口描述、请求方式、URL、请求参数、响应参数、示例\\n- 推荐使用Swagger/OpenAPI生成接口文档\\n\\n### 7.2 变更管理\\n\\n- API变更须向前兼容，不得直接修改已发布的接口\\n- 重大变更须升级版本号（如v1升级为v2）\\n- 废弃的接口须在文档中标注，并保留至少3个月\"}]','2026-03-21 20:14:14'),
(10,1,2,'sess_mn0ajqq9dk0epu','开发的时候 整数类型 我用什么？','根据公司表设计规范，整数类型优先使用INT，大范围使用BIGINT。','[{\"file_name\": \"2ee9cc33b736429f97be205d94588829.pdf\", \"content\": \"唯一索引：uk_表名_字段名，如：uk_user_email。\\n联合索引：idx_表名_字段1_字段2，如：idx_order_user_id_status。\\n三、表设计规范\\n3.1 基本要求\\n所有表必须使用InnoDB存储引擎。\\n字符集统一使用utf8mb4，排序规则使用utf8mb4_unicode_ci。\\n所有表必须有主键，推荐使用自增整型主键。\\n所有表必须包含create_time和upd\"}, {\"file_name\": \"ec7591726edd4313b0390d25c183d7c2.txt\", \"content\": \"7.2 密码处理\\n- 密码存储必须使用加密算法（如MD5、bcrypt）\\n- 禁止在代码中硬编码密码和密钥\\n\\n八、版本要求\\n\\n公司项目统一使用Python 3.10及以上版本，新项目优先使用Python 3.12。\"}, {\"file_name\": \"74b977bd9f8545dca742bf7efc73969c.docx\", \"content\": \"是否有足够的注释和文档。\\n4.3 冲突解决：\\n合并前须先将目标分支的最新代码合并到当前分支。\\n冲突须由功能开发者自行解决。\\n解决冲突后须重新测试。\\n五、版本发布流程\\n5.1 版本号规范（语义化版本）：\\n主版本号.次版本号.修订号（如1.2.3）\\n主版本号：不兼容的API变更\\n次版本号：向下兼容的功能新增\\n修订号：向下兼容的问题修复\\n5.2 发布流程：\\n从develop分支创建release分支。\\n\"}]','2026-03-21 20:16:19'),
(11,1,3,'sess_mn0alusgn2iing','企业OA的登录密码 可以是6位吗？','根据企业OA系统使用手册（参考资料1）中的密码要求，企业OA系统的登录密码长度**不少于8位**，因此企业OA的登录密码不可以是6位。','[{\"file_name\": \"3b5c9e5aa69c461480de66cf0e3da30e.txt\", \"content\": \"企业OA系统使用手册\\n\\n一、系统概述\\n\\n企业OA办公自动化系统是公司内部日常办公管理的核心平台，涵盖流程审批、通知公告、日程管理、通讯录、文档中心等功能模块。本手册将详细介绍各功能模块的使用方法，帮助员工快速上手使用。\\n\\n系统访问地址：http://oa.company.com\\n技术支持邮箱：it-support@company.com\\n技术支持电话：内线8888\\n\\n二、登录与账号管理\\n\\n2.1 \"}, {\"file_name\": \"a352932212554d54baf73d3bd39396e9.docx\", \"content\": \"餐厅：位于1楼，提供早餐和午餐，营业时间7:30-9:00和11:30-13:00。\\n健身房：位于B座1楼，7:00-22:00开放，员工免费使用。\\n休息区：每层楼设有茶水间和休息区，提供免费咖啡、茶和零食。\\n会议室：使用前须通过OA系统预约。\\n停车场：地下停车场B1-B2层，新员工可向行政部申请停车位。\\n四、IT系统开通\\n入职后IT部门将为您开通以下系统账号：\\n4.1 电脑登录账号\\n用户名：工号\"}, {\"file_name\": \"4d87ae0742c2414cb3b12b492f4b3e10.pdf\", \"content\": \"A2: 请确认SMTP服务器已开启身份验证，用户名填写完整邮箱地址。\\nQ3: 如何修改邮箱密码？\\nA3: 登录网页版邮箱，在\\\"设置 - 安全设置\\\"中修改密码。密码须包含大小写字母、数字，长度不少于8位。\\nQ4: 邮箱容量满了怎么办？\\nA4: 请清理不需要的邮件和附件，或将重要邮件归档到本地。如需扩容请联系IT部门申请。\\n六、技术支持\\n如遇到无法解决的邮箱问题，请联系IT技术支持：\\n电话：内线888\"}]','2026-03-21 20:19:36'),
(12,2,2,'sess_mn164wdf0nl78v','API接口的认证方式是什么？','根据参考资料，API接口的认证方式是JWT（JSON Web Token）。具体说明如下：\n\n- 采用JWT进行身份认证\n- Token通过登录接口获取，有效期为24小时\n- 请求需在Header中携带`Authorization: Bearer {token}`\n\n这是企业内部API接口的认证标准，所有需要认证的接口都必须在请求头中包含该认证信息。','[{\"file_name\": \"e2ece8ca7ec243d1aa66827b902896c0.md\", \"content\": \"### 4.2 状态码定义\\n\\n| code值 | 含义 | 说明 |\\n|--------|------|------|\\n| 200 | 成功 | 请求处理成功 |\\n| 400 | 参数错误 | 请求参数不合法 |\\n| 401 | 未授权 | Token无效或已过期 |\\n| 403 | 权限不足 | 无操作权限 |\\n| 404 | 资源不存在 | 请求的资源未找到 |\\n| 500 | 服务器错误 |\"}]','2026-03-22 11:00:58'),
(13,1,2,'sess_mn17ct9d3f8lhb','API接口的认证方式是什么？','根据参考资料，API接口的认证方式是JWT（JSON Web Token）。具体说明如下：\n\n- Token通过登录接口获取\n- 有效期为24小时\n- 请求需在Header中携带`Authorization: Bearer {token}`\n\n此信息来源于企业内部知识库的\"五、认证与授权\"部分（5.1 认证方式）的描述。','[{\"file_name\": \"e2ece8ca7ec243d1aa66827b902896c0.md\", \"content\": \"### 4.2 状态码定义\\n\\n| code值 | 含义 | 说明 |\\n|--------|------|------|\\n| 200 | 成功 | 请求处理成功 |\\n| 400 | 参数错误 | 请求参数不合法 |\\n| 401 | 未授权 | Token无效或已过期 |\\n| 403 | 权限不足 | 无操作权限 |\\n| 404 | 资源不存在 | 请求的资源未找到 |\\n| 500 | 服务器错误 |\"}]','2026-03-22 11:34:46'),
(14,1,2,'sess_mn1gzux8rxq76y','API接口的认证方式是什么？','根据参考资料，API接口的认证方式是JWT（JSON Web Token）。具体说明如下：\n\n- 采用JWT进行身份认证\n- Token通过登录接口获取，有效期为24小时\n- 请求需在Header中携带`Authorization: Bearer {token}`\n\n这是企业内部API接口的认证标准，所有需要认证的接口都必须在请求头中包含该认证信息。','[{\"file_name\": \"e2ece8ca7ec243d1aa66827b902896c0.md\", \"content\": \"### 4.2 状态码定义\\n\\n| code值 | 含义 | 说明 |\\n|--------|------|------|\\n| 200 | 成功 | 请求处理成功 |\\n| 400 | 参数错误 | 请求参数不合法 |\\n| 401 | 未授权 | Token无效或已过期 |\\n| 403 | 权限不足 | 无操作权限 |\\n| 404 | 资源不存在 | 请求的资源未找到 |\\n| 500 | 服务器错误 |\"}]','2026-03-22 16:04:40'),
(15,1,1,'sess_mn1jofh7myvj3h','企业OA的登录密码 可以是6位吗？','根据提供的参考资料，我没有找到关于企业OA登录密码长度的具体规定。参考资料中仅提到第九条信息安全部分有\"妥善保管个人账号和密码，不得与他人共用\"的要求，但没有说明密码的最小长度或最大长度限制。\n\n因此，参考资料中没有相关信息，无法确定企业OA登录密码是否可以是6位。','[{\"file_name\": \"3feba57396754d42b44253b29bfdff6c.docx\", \"content\": \"（二）请假须提前申请并获得批准；\\n（三）外出办公须在OA系统中登记。\\n第八条 办公纪律：\\n（一）工作时间内专注工作，不做与工作无关的事务；\\n（二）保持工作区域整洁有序；\\n（三）公共区域轻声交流，不影响他人工作；\\n（四）会议期间将手机调至静音模式。\\n第九条 信息安全：\\n（一）妥善保管个人账号和密码，不得与他人共用；\\n（二）公司电脑不得安装未授权的软件；\\n（三）重要文件须定期备份；\\n（四）离开工位时须\"}, {\"file_name\": \"061fc6f69b4c49949917d3b18466911a.md\", \"content\": \"## 第四章 违规处理\\n\\n### 第十二条 违规情形\\n\\n- 未经审批擅自休假的，按旷工处理\\n- 提供虚假请假材料的，给予警告处分，并取消相应假期\\n- 请假期满未续假或续假未获批准而逾期不到岗的，超过部分按旷工处理\\n\\n## 第五章 附则\\n\\n### 第十三条\\n\\n本办法自2024年1月1日起执行，如有未尽事宜，由人力资源部负责解释。\"}, {\"file_name\": \"89b0b3f6755e489980520281153f9bb5.pdf\", \"content\": \"（一）年度绩效考核结果\\n（二）市场薪酬水平变化\\n（三）公司经营业绩状况\\n（四）岗位变动情况\\n第十二条 员工晋升时，薪酬按照新岗位等级标准进行调整。\\n第六章 附则\\n第十三条 本制度由人力资源部负责解释和修订。\\n第十四条 本制度自2024年1月1日起执行。\"}]','2026-03-22 17:19:55'),
(16,1,3,'sess_mn1jqgx7jg641b','企业OA的登录密码 可以是6位吗？','根据企业OA系统使用手册（参考资料1）中\"二、登录与账号管理\"部分的\"2.2 密码要求\"规定，企业OA系统的登录密码长度**不少于8位**。因此，企业OA的登录密码不能是6位，6位密码不符合系统密码长度要求。','[{\"file_name\": \"3b5c9e5aa69c461480de66cf0e3da30e.txt\", \"content\": \"企业OA系统使用手册\\n\\n一、系统概述\\n\\n企业OA办公自动化系统是公司内部日常办公管理的核心平台，涵盖流程审批、通知公告、日程管理、通讯录、文档中心等功能模块。本手册将详细介绍各功能模块的使用方法，帮助员工快速上手使用。\\n\\n系统访问地址：http://oa.company.com\\n技术支持邮箱：it-support@company.com\\n技术支持电话：内线8888\\n\\n二、登录与账号管理\\n\\n2.1 \"}, {\"file_name\": \"a352932212554d54baf73d3bd39396e9.docx\", \"content\": \"餐厅：位于1楼，提供早餐和午餐，营业时间7:30-9:00和11:30-13:00。\\n健身房：位于B座1楼，7:00-22:00开放，员工免费使用。\\n休息区：每层楼设有茶水间和休息区，提供免费咖啡、茶和零食。\\n会议室：使用前须通过OA系统预约。\\n停车场：地下停车场B1-B2层，新员工可向行政部申请停车位。\\n四、IT系统开通\\n入职后IT部门将为您开通以下系统账号：\\n4.1 电脑登录账号\\n用户名：工号\"}, {\"file_name\": \"4d87ae0742c2414cb3b12b492f4b3e10.pdf\", \"content\": \"A2: 请确认SMTP服务器已开启身份验证，用户名填写完整邮箱地址。\\nQ3: 如何修改邮箱密码？\\nA3: 登录网页版邮箱，在\\\"设置 - 安全设置\\\"中修改密码。密码须包含大小写字母、数字，长度不少于8位。\\nQ4: 邮箱容量满了怎么办？\\nA4: 请清理不需要的邮件和附件，或将重要邮件归档到本地。如需扩容请联系IT部门申请。\\n六、技术支持\\n如遇到无法解决的邮箱问题，请联系IT技术支持：\\n电话：内线888\"}]','2026-03-22 17:21:21'),
(17,1,3,'sess_mn1jqgx7jg641b','无法收到邮件怎么办？','根据参考资料，无法收到邮件的解决方法是：请检查网络连接，确认服务器设置是否正确，检查垃圾邮件文件夹。','[{\"file_name\": \"4d87ae0742c2414cb3b12b492f4b3e10.pdf\", \"content\": \"IMAP接收服务器：\\n  服务器地址：imap.company.com\\n  端口：993\\n  加密方式：SSL/TLS\\nSMTP发送服务器：\\n  服务器地址：smtp.company.com\\n  端口：465\\n  加密方式：SSL/TLS\\n  需要身份验证：是\\n四、手机客户端配置\\n4.1 iOS设备\\n打开\\\"设置 - 邮件 - 账户 - 添加账户\\\"。\\n选择\\\"其他\\\"，然后选择\\\"添加邮件账户\\\"。\\n输入姓\"}, {\"file_name\": \"3b5c9e5aa69c461480de66cf0e3da30e.txt\", \"content\": \"八、常见问题\\n\\nQ1: 系统无法登录怎么办？\\nA1: 请检查网络连接，确认用户名和密码是否正确。如账号被锁定，请等待30分钟后重试或联系IT部门。\\n\\nQ2: 流程审批人不在怎么办？\\nA2: 可在流程详情中点击\\\"催办\\\"按钮发送提醒，或联系审批人的上级进行代审批。\\n\\nQ3: 如何修改已提交的流程？\\nA3: 已提交但未审批完成的流程，可点击\\\"撤回\\\"后重新编辑提交。已审批完成的流程无法修改。\"}]','2026-03-22 17:33:46');

/*Table structure for table `t_document` */

DROP TABLE IF EXISTS `t_document`;

CREATE TABLE `t_document` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '文档ID',
  `kb_id` int NOT NULL COMMENT '所属知识库ID',
  `file_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件名',
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件存储路径',
  `file_size` bigint NOT NULL DEFAULT '0' COMMENT '文件大小（字节）',
  `file_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件类型：txt/pdf/md/docx',
  `chunk_count` int NOT NULL DEFAULT '0' COMMENT '分块数量',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'uploading' COMMENT '状态：uploading-上传中，vectorized-已向量化，failed-失败',
  `creator_id` int NOT NULL COMMENT '上传者ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `kb_id` (`kb_id`),
  KEY `creator_id` (`creator_id`),
  CONSTRAINT `t_document_ibfk_1` FOREIGN KEY (`kb_id`) REFERENCES `t_knowledge_base` (`id`),
  CONSTRAINT `t_document_ibfk_2` FOREIGN KEY (`creator_id`) REFERENCES `t_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表';

/*Data for the table `t_document` */

insert  into `t_document`(`id`,`kb_id`,`file_name`,`file_path`,`file_size`,`file_type`,`chunk_count`,`status`,`creator_id`,`create_time`) values 
(12,1,'公司考勤管理制度.txt','D:\\cursor\\EnterpriseQA\\server\\uploads\\59963262a75a4995880c3cc6ac6828c0.txt',2930,'txt',3,'vectorized',1,'2026-03-21 19:46:17'),
(13,1,'公司薪酬福利制度.pdf','D:\\cursor\\EnterpriseQA\\server\\uploads\\89b0b3f6755e489980520281153f9bb5.pdf',46016,'pdf',3,'vectorized',1,'2026-03-21 19:46:46'),
(14,1,'员工请假管理办法.md','D:\\cursor\\EnterpriseQA\\server\\uploads\\061fc6f69b4c49949917d3b18466911a.md',3304,'md',4,'vectorized',1,'2026-03-21 19:47:12'),
(15,1,'员工行为规范手册.docx','D:\\cursor\\EnterpriseQA\\server\\uploads\\3feba57396754d42b44253b29bfdff6c.docx',38464,'docx',3,'vectorized',1,'2026-03-21 19:47:39'),
(16,2,'API接口设计规范.md','D:\\cursor\\EnterpriseQA\\server\\uploads\\e2ece8ca7ec243d1aa66827b902896c0.md',3709,'md',6,'vectorized',1,'2026-03-21 19:48:11'),
(17,2,'Git版本管理规范.docx','D:\\cursor\\EnterpriseQA\\server\\uploads\\74b977bd9f8545dca742bf7efc73969c.docx',38369,'docx',3,'vectorized',1,'2026-03-21 19:48:46'),
(18,2,'Python开发编码规范.txt','D:\\cursor\\EnterpriseQA\\server\\uploads\\ec7591726edd4313b0390d25c183d7c2.txt',3208,'txt',4,'vectorized',1,'2026-03-21 19:49:09'),
(19,2,'数据库设计规范.pdf','D:\\cursor\\EnterpriseQA\\server\\uploads\\2ee9cc33b736429f97be205d94588829.pdf',44252,'pdf',3,'vectorized',1,'2026-03-21 19:49:34'),
(20,3,'企业OA系统使用手册.txt','D:\\cursor\\EnterpriseQA\\server\\uploads\\3b5c9e5aa69c461480de66cf0e3da30e.txt',3784,'txt',4,'vectorized',1,'2026-03-21 19:50:13'),
(21,3,'企业邮箱配置说明.pdf','D:\\cursor\\EnterpriseQA\\server\\uploads\\4d87ae0742c2414cb3b12b492f4b3e10.pdf',43360,'pdf',3,'vectorized',1,'2026-03-21 19:50:41'),
(22,3,'项目管理平台操作指南.md','D:\\cursor\\EnterpriseQA\\server\\uploads\\f624b9d898c849669139c2dc63d7a651.md',4172,'md',5,'vectorized',1,'2026-03-21 19:51:05'),
(23,3,'新员工入职指南.docx','D:\\cursor\\EnterpriseQA\\server\\uploads\\a352932212554d54baf73d3bd39396e9.docx',38585,'docx',3,'vectorized',1,'2026-03-21 19:51:34');

/*Table structure for table `t_knowledge_base` */

DROP TABLE IF EXISTS `t_knowledge_base`;

CREATE TABLE `t_knowledge_base` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '知识库ID',
  `kb_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '知识库名称',
  `description` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '知识库描述',
  `creator_id` int NOT NULL COMMENT '创建者ID',
  `doc_count` int NOT NULL DEFAULT '0' COMMENT '文档数量',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：1-正常，0-禁用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `creator_id` (`creator_id`),
  CONSTRAINT `t_knowledge_base_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `t_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库表';

/*Data for the table `t_knowledge_base` */

insert  into `t_knowledge_base`(`id`,`kb_name`,`description`,`creator_id`,`doc_count`,`status`,`create_time`,`update_time`) values 
(1,'公司规章制度','包含公司各项规章制度、员工手册等文档',1,4,1,'2026-03-21 18:20:17','2026-03-21 19:47:55'),
(2,'技术文档库','包含技术规范、API文档、开发指南等',1,4,1,'2026-03-21 18:20:17','2026-03-21 19:49:49'),
(3,'产品帮助中心','产品使用指南、常见问题解答等',1,4,1,'2026-03-21 18:20:17','2026-03-21 19:51:51');

/*Table structure for table `t_user` */

DROP TABLE IF EXISTS `t_user`;

CREATE TABLE `t_user` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `password` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码（MD5加密）',
  `nickname` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '昵称',
  `role` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'user' COMMENT '角色：admin-管理员，user-普通用户',
  `avatar` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '头像地址',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

/*Data for the table `t_user` */

insert  into `t_user`(`id`,`username`,`password`,`nickname`,`role`,`avatar`,`status`,`create_time`,`update_time`) values 
(1,'admin','e10adc3949ba59abbe56e057f20f883e','系统管理员','admin','',1,'2026-03-21 18:20:17','2026-03-21 18:20:17'),
(2,'user1','e10adc3949ba59abbe56e057f20f883e','张三','user','',1,'2026-03-21 18:20:17','2026-03-21 18:20:17'),
(3,'user2','e10adc3949ba59abbe56e057f20f883e','李四','user','',1,'2026-03-21 18:20:17','2026-03-21 18:20:17');

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
