"""
用户模型
对应数据库表 t_user
"""
from models import db
from datetime import datetime


class User(db.Model):
    """用户表ORM模型"""

    __tablename__ = 't_user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='用户ID')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    password = db.Column(db.String(64), nullable=False, comment='密码（MD5加密）')
    nickname = db.Column(db.String(50), default='', comment='昵称')
    role = db.Column(db.String(10), nullable=False, default='user', comment='角色：admin/user')
    avatar = db.Column(db.String(255), default='', comment='头像地址')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态：1-启用，0-禁用')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        """将模型转换为字典（不包含密码）"""
        return {
            'id': self.id,
            'username': self.username,
            'nickname': self.nickname,
            'role': self.role,
            'avatar': self.avatar,
            'status': self.status,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else '',
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else ''
        }
