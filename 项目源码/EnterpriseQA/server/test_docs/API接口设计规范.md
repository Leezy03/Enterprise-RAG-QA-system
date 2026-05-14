# API接口设计规范

## 一、概述

本规范旨在统一公司内部所有RESTful API的设计标准，确保接口的一致性、可读性和可维护性。所有后端开发人员在设计和开发API时须遵循本规范。

## 二、URL设计规范

### 2.1 基本原则

- 使用HTTPS协议
- API版本号放在URL中，如：`/api/v1/users`
- 使用名词复数形式表示资源，如：`/users`、`/orders`
- URL中使用小写字母和连字符，如：`/user-profiles`
- URL层级不超过3层

### 2.2 资源命名示例

| 操作 | HTTP方法 | URL |
|------|---------|-----|
| 获取用户列表 | GET | /api/v1/users |
| 获取单个用户 | GET | /api/v1/users/{id} |
| 创建用户 | POST | /api/v1/users |
| 更新用户 | PUT | /api/v1/users/{id} |
| 删除用户 | DELETE | /api/v1/users/{id} |
| 获取用户的订单 | GET | /api/v1/users/{id}/orders |

### 2.3 查询参数

- 分页：`?page=1&page_size=20`
- 排序：`?sort=create_time&order=desc`
- 筛选：`?status=active&role=admin`
- 搜索：`?keyword=张三`

## 三、请求规范

### 3.1 请求头

必须包含以下请求头：

- `Content-Type: application/json`（POST/PUT请求）
- `Authorization: Bearer {token}`（需认证的接口）
- `Accept-Language: zh-CN`（可选，指定语言）

### 3.2 请求体格式

POST和PUT请求使用JSON格式：

```json
{
  "username": "zhangsan",
  "nickname": "张三",
  "role": "user",
  "status": 1
}
```

### 3.3 文件上传

文件上传使用`multipart/form-data`格式，文件字段名统一使用`file`。

## 四、响应规范

### 4.1 统一响应结构

所有接口返回统一的JSON结构：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {}
}
```

### 4.2 状态码定义

| code值 | 含义 | 说明 |
|--------|------|------|
| 200 | 成功 | 请求处理成功 |
| 400 | 参数错误 | 请求参数不合法 |
| 401 | 未授权 | Token无效或已过期 |
| 403 | 权限不足 | 无操作权限 |
| 404 | 资源不存在 | 请求的资源未找到 |
| 500 | 服务器错误 | 服务器内部错误 |

### 4.3 分页响应

```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "list": [],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### 4.4 错误响应

```json
{
  "code": 400,
  "message": "用户名不能为空",
  "data": null
}
```

## 五、认证与授权

### 5.1 认证方式

- 采用JWT（JSON Web Token）进行身份认证
- Token通过登录接口获取，有效期为24小时
- 请求需在Header中携带`Authorization: Bearer {token}`

### 5.2 权限控制

- 接口按角色进行权限控制
- 管理员接口须验证`role=admin`
- 未授权访问返回401，权限不足返回403

## 六、安全规范

### 6.1 输入验证

- 所有输入参数必须进行类型和长度校验
- 防止SQL注入、XSS攻击
- 敏感数据传输必须加密

### 6.2 频率限制

- 登录接口：同一IP每分钟最多10次
- 普通接口：同一用户每分钟最多60次
- 上传接口：同一用户每分钟最多5次

### 6.3 日志记录

- 所有API请求须记录访问日志
- 日志包含：请求时间、用户ID、请求URL、请求方法、响应状态码、响应时间
- 敏感信息（密码等）不得记录在日志中

## 七、文档规范

### 7.1 接口文档

- 每个API接口必须编写接口文档
- 文档内容包括：接口描述、请求方式、URL、请求参数、响应参数、示例
- 推荐使用Swagger/OpenAPI生成接口文档

### 7.2 变更管理

- API变更须向前兼容，不得直接修改已发布的接口
- 重大变更须升级版本号（如v1升级为v2）
- 废弃的接口须在文档中标注，并保留至少3个月
