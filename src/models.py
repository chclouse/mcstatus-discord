import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

class MonitorType(enum.Enum):
    Passive = 0
    Active = 1

Base = declarative_base()
Session = sessionmaker()

class Status(Base):
    __tablename__ = 'statuses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, nullable=False, unique=True)
    online = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    slots = Column(Integer)
    online_players = Column(Integer)
    sample = Column(String)

    def __repr__(self):
        return ("Status(address='{}', online={}, timestamp={}, slots={}, " + \
                "online_players={}, sample='{}')").format(
                        self.address,
                        self.online,
                        self.timestamp,
                        self.slots,
                        self.online_players,
                        self.sample)


class Monitor(Base):
    __tablename__ = 'monitors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_type = Column(Enum(MonitorType), nullable=False)
    status_id = Column(Integer, ForeignKey('statuses.id'), nullable=False)
    channel = Column(String)
    message = Column(String)

    status = relationship('Status', backref='monitors');

    def __repr__(self):
        return ("Monitor(id={}, monitor_type={}, status_id={}, channel={}, " + \
                "message={})").format(
                        self.id,
                        repr(self.monitor_type),
                        self.status_id,
                        repr(self.channel),
                        repr(self.message))


def base():
    return Base
