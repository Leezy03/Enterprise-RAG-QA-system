"""
统一响应格式封装
所有API接口使用统一的JSON响应结构
"""
from flask import jsonify


def success(data=None, message='操作成功'):
    """
    成功响应
    :param data: 返回数据
    :param message: 提示信息
    :return: JSON响应
    """
    return jsonify({
        'code': 200,
        'message': message,
        'data': data
    })


def error(message='操作失败', code=400):
    """
    错误响应
    :param message: 错误信息
    :param code: 错误码
    :return: JSON响应
    """
    return jsonify({
        'code': code,
        'message': message,
        'data': None
    })


def page_response(items, total, page, page_size):
    """
    分页响应
    :param items: 数据列表
    :param total: 总记录数
    :param page: 当前页码
    :param page_size: 每页条数
    :return: JSON响应
    """
    return jsonify({
        'code': 200,
        'message': '查询成功',
        'data': {
            'list': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    })
