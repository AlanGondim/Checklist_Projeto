import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# =========================================================
# 1. CONFIGURAÇÕES E BANCO DE DADOS (MODEL)
# =========================================================
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia_executivo.db'
engine = create_engine(DB_NAME)
Session = sessionmaker(bind=engine)
session = Session()

# Pasta para armazenar documentos de prova (Judicialização)
if not os.path.exists("attachments"):
    os.makedirs("attachments")

class Projeto(Base):
    __tablename__ = 'monitoramento_projetos'
    id = Column(Integer, primary_key=True)
    nome_projeto = Column(String); gerente_projeto = Column(String)
    regional = Column(String); oportunidade = Column(String)
    horas_contratadas = Column(Float); tipo = Column(String)
    data_inicio = Column(String); data_termino = Column(String)
    data_entrada_producao = Column(String); data_auditoria = Column(String)
    responsavel_auditoria = Column(String); timestamp = Column(DateTime, default=datetime.now)
    # Percentuais das fases
    inicializacao = Column(Float); planejamento = Column(Float)
    workshop_de_processos = Column(Float); construcao = Column(Float)
    go_live = Column(Float); operacao_assistida = Column(Float)
    finalizacao = Column(Float)

class AuditoriaHistorico(Base):
    __tablename__ = 'historico_auditorias'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); data_auditoria = Column(String)
    responsavel_auditoria = Column(String); progresso_total = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)

class ItemAuditoria(Base):
    __tablename__ = 'itens_auditados'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    item_nome = Column(String); entregue = Column(Integer) # 1 ou 0

class EvidenciaArtefato(Base):
    __tablename__ = 'evidencias_artefatos'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    item_nome = Column(String); arquivo_nome = Column(String)
    arquivo_path = Column(String); timestamp = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)

# =========================================================
# 2. DEFINIÇÕES DA METODOLOGIA (CONTROLLER)
# =========================================================
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial", "Alinhamento time MV", "Ata de reunião", "Alinhamento Cliente", "TAP", "DEP"],
    "Planejamento
