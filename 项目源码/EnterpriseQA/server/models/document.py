"""
文档模型
对应数据库表 t_document
"""
from models import db
from datetime import datetime


class Document(db.Model):
    """文档表ORM模型"""

    __tablename__ = 't_document'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='文档ID')
    kb_id = db.Column(db.Integer, db.ForeignKey('t_knowledge_base.id'), nullable=False, comment='所属知识库ID')
    file_name = db.Column(db.String(255), nullable=False, comment='文件名')
    file_path = db.Column(db.String(500), nullable=False, comment='文件存储路径')
    file_size = db.Column(db.BigInteger, nullable=False, default=0, comment='文件大小（字节）')
    file_type = db.Column(db.String(20), nullable=False, comment='文件类型')
    chunk_count = db.Column(db.Integer, nullable=False, default=0, comment='分块数量')
    status = db.Column(db.String(20), nullable=False, default='uploading', comment='状态：uploading/vectorized/failed')
    creator_id = db.Column(db.Integer, db.ForeignKey('t_user.id'), nullable=False, comment='上传者ID')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')

    # 关联关系
    knowledge_base = db.relationship('KnowledgeBase', backref='documents', lazy=True)
    creator = db.relationship('User', backref='documents', lazy=True)

    def to_dict(self):
        """将模型转换为字典"""
        return {
            'id': self.id,
            'kb_id': self.kb_id,
            'kb_name': self.knowledge_base.kb_name if self.knowledge_base else '',
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'chunk_count': self.chunk_count,
            'status': self.status,
            'creator_id': self.creator_id,
            'creator_name': self.creator.nickname if self.creator else '',
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else ''
        }
