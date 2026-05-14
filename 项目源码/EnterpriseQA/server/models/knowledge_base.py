"""
知识库模型
对应数据库表 t_knowledge_base
"""
from models import db
from datetime import datetime


class KnowledgeBase(db.Model):
    """知识库表ORM模型"""

    __tablename__ = 't_knowledge_base'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='知识库ID')
    kb_name = db.Column(db.String(100), nullable=False, comment='知识库名称')
    description = db.Column(db.String(500), default='', comment='知识库描述')
    creator_id = db.Column(db.Integer, db.ForeignKey('t_user.id'), nullable=False, comment='创建者ID')
    doc_count = db.Column(db.Integer, nullable=False, default=0, comment='文档数量')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态：1-正常，0-禁用')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联关系
    creator = db.relationship('User', backref='knowledge_bases', lazy=True)

    def to_dict(self):
        """将模型转换为字典"""
        return {
            'id': self.id,
            'kb_name': self.kb_name,
            'description': self.description,
            'creator_id': self.creator_id,
            'creator_name': self.creator.nickname if self.creator else '',
            'doc_count': self.doc_count,
            'status': self.status,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else '',
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else ''
        }
