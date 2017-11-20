from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, unique=True, primary_key=True)
    name = Column(String(250), unique=True, nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))
    
'''
This represents a store category, which would contain
a group of items.  The items contain a refresh to the
user that created them, because only the original user
can modify or delete them.
'''


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, unique=True, primary_key=True)
    name = Column(String(250), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    items = relationship("Item", cascade="all, delete")

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }


class Item(Base):
    __tablename__ = 'item'

    name = Column(String(80), unique=True, nullable=False)
    id = Column(Integer, unique=True, primary_key=True)
    description = Column(String(250))
    price = Column(String(8))
    category_name = Column(String(250), ForeignKey('category.name'))
    category = relationship(Category)
    mydate = Column(DateTime(), default=datetime.utcnow,
                   onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'price': self.price,
        }


engine = create_engine('postgresql+psycopg2://catalog:catalog@localhost:5432/catalog')


Base.metadata.create_all(engine)
