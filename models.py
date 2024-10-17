from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class MstAlat(Base):
    __tablename__ = 'mst_alat'
    __table_args__ = {'schema': 'predictions'}

    idalat = Column(String, primary_key=True)
    name = Column(String)
    mac_address = Column(String)
    type = Column(String)
    
class MstMode(Base):
    __tablename__ = 'mst_mode'
    __table_args__ = {'schema':'predictions'}
    
    idmode = Column(String, primary_key=True)
    name = Column(String)
    value = Column(Integer)

class MstSesi(Base):
    __tablename__ = 'mst_sesi'
    __table_args__ = {'schema': 'predictions'}

    idsesi = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String)
    idalat_tx = Column(String, ForeignKey('predictions.mst_alat.idalat'))
    idalat_rx = Column(String, ForeignKey('predictions.mst_alat.idalat'))
    idmode = Column(String, ForeignKey('predictions.mst_mode.idmode'))
    iduser = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    idmode= relationship("MstMode", foreign_keys=[idmode])
    alat_tx = relationship("MstAlat", foreign_keys=[idalat_tx])
    alat_rx = relationship("MstAlat", foreign_keys=[idalat_rx])

class MstSensor(Base):
    __tablename__ = 'mst_sensor'
    __table_args__ = {'schema': 'predictions'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    spo2 = Column(Float)
    hr2 = Column(Float)
    age = Column(Integer)
    predicted_sys = Column(Float)
    predicted_dia = Column(Float)
    stress_level = Column(Float)
    steps = Column(Integer)
    longitude = Column(Float)
    latitude = Column(Float)
    temp = Column(Float)
    vo2max = Column(Float)
    idalat_tx = Column(String, ForeignKey('predictions.mst_alat.idalat'))
    idsesi = Column(Integer, ForeignKey('predictions.mst_sesi.idsesi'))
    distance = Column(Float)

    alat_tx = relationship("MstAlat")
    sesi = relationship("MstSesi")

class MstSistem(Base):
    __tablename__ = 'mst_sistem'
    __table_args__ = {'schema': 'predictions'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    

