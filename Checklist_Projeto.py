import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fpdf import FPDF
from datetime import datetime
import io
import os
import json

# --- DATABASE SETUP ---
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia_executivo.db'
engine = create_engine(DB_NAME)
Session = sessionmaker(bind=engine)
session = Session()

class Projeto(Base):
    __tablename__ = 'monitoramento_projetos'
    id = Column(Integer, primary_key=True)
    nome_projeto = Column(String)
    gerente_projeto = Column(String)
    oportunidade = Column(String)
    horas_contratadas = Column(Float)
    tipo = Column(String)
    data_inicio = Column(String)
    data_termino = Column(String)
    data_producao = Column(String)
    responsavel_verificacao = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    checklist_json = Column(Text)  # Salva o estado individual de cada checkbox
    inicializacao = Column(Float); planejamento = Column(Float)
    workshop_de_processos = Column(Float); construcao = Column(Float)
    go_live = Column(Float); operacao_assistida = Column(Float)
    finalizacao = Column(Float)

Base.metadata.create_all(engine)

# --- METODOLOGIA ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial", "Alinhamento time MV", "Ata de reunião", "Alinhamento Cliente", "TAP", "DEP"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião", "Cronograma", "Plano de Projeto"],
    "Workshop de Processos": ["Análise de Gaps Críticos", "Business Blue Print", "Configuração do Sistema", "Apresentação da Solução", "Termo de Aceite"],
    "Construção": ["Plano de Cutover", "Avaliação de Treinamento", "Lista de Presença", "Treinamento de Tabelas", "Carga Precursora", "Homologação Integração"],
    "Go Live": ["Carga Final de Dados", "Escala Apoio Go Live", "Metas de Simulação", "Testes Integrados", "Reunição Go/No Go", "Ata de Reunião"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding", "Ata de Reunião", "Identificação de Gaps", "Termo de Aceite"],
    "Finalização": ["Reunião de Finalização", "Ata de Reunião", "TEP", "Registro das Lições Aprendidas - MV LEARN - Sharepoint"]
}

MAPA_COLUNAS = {
    "Inicialização": "inicializacao", "Planejamento": "planejamento", 
    "Workshop de Processos": "workshop_de_processos", "Construção": "construcao",
    "Go Live": "go_live", "Operação Assistida": "operacao_assistida", "Finalização": "finalizacao"
}

# --- FUNÇÕES AUXILIARES ---
def gerar_radar_chart(realizado_dict):
    categorias = list(realizado_dict.keys())
    valores = list(realizado_dict.values())
    N = len(categorias)
    angulos = [n / float(N) * 2 * np.pi for n in range(N)]
    angulos += angulos[:1]
    realizado = valores + valores[:1]
    
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angulos, [100.0]*(N+1), color='#143264', linewidth=1, linestyle='--')
    ax.plot(angulos, realizado, color='#ffb30e', linewidth=3, label="Realizado")
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.3)
    plt.xticks(angulos[:-1], ["Ini", "Plan", "Work", "Const", "Live", "Op", "Fin"], size=8, fontweight='bold')
    return fig

class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100); self.rect(0, 0, 210, 35, 'F')
        if os.path.exists("Logomarca MV Atualizada.png"):
            self.image("Logomarca MV Atualizada.png", x=10, y=8, w=18)
        self.set_font('Helvetica', 'B', 16); self.set_text_color(255, 255, 255)
        self.set_xy(30, 12)
        self.cell(150, 10, "STATUS REPORT EXECUTIVO - HUB DE INTELIGÊNCIA", ln=True, align='C')

    def footer(self):
        self.set_y(-15); self.set_font('Helvetica', 'I', 7); self.set_text_color(150, 150, 150)
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.cell(0, 10, f"Protocolo: {ts} | Hub de Inteligência MV | Pagina {self.page_no()}", 0, 0, 'C')

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Hub MV", layout="wide")

st.markdown("<h2 style='font-size: 24px; color: #143264; font-weight: bold;'>🏛️ Hub de Inteligência | Governança e Metodologia</h2>", unsafe_allow_html=True)

# 1. BUSCA E RESET
with st.sidebar:
    st.header("🔍 Buscar no Hub")
    projetos_salvos = [p.nome_projeto for p in session.query(Projeto.nome_projeto).distinct().all()]
    projeto_busca = st.selectbox("Carregar Projeto Existente", [""] + projetos_salvos)
    
    if st.button("🆕 NOVO PROJETO (LIMPAR)"):
        st.session_state.clear()
        st.rerun()

# Recuperação de dados do banco
dados_db = None
checklist_recuperado = {}
if projeto_busca:
    dados_db = session.query(Projeto).filter_by(nome_projeto=projeto_busca).order_by(Projeto.timestamp.desc()).first()
    if dados_db and dados_db.checklist_json:
        checklist_recuperado = json.loads(dados_db.checklist_json)

# 2. CAMPOS EXECUTIVOS
with st.container():
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Nome do Projeto", value=dados_db.nome_projeto if dados_db else "")
    oportunidade = c2.text_input("Oportunidade (CRM)", value=dados_db.oportunidade if dados_db else "")
    gp_p = c3.text_input("Gerente de Projeto", value=dados_db.gerente_projeto if dados_db else "")

    c4, c5, c6 = st.columns(3)
    horas_cont = c4.number_input("Horas Contratadas", min_value=0.0, step=100.0, value=float(dados_db.horas_contratadas) if dados_db else 0.0)
    tipo_p = c5.selectbox("Tipo", ["Implantação", "Migração", "Revitalização", "Consultoria"])
    resp_verificacao = c6.text_input("Responsável pela Verificação", value=dados_db.responsavel_verificacao if dados_db else "")

    c7, c8, c9 = st.columns(3)
    # Função auxiliar para tratar datas recuperadas
    def format_date(d_str):
        try: return datetime.strptime(d_str, "%d/%m/%Y")
        except: return datetime.now()

    d_inicio = c7.date_input("Data de Início", value=format_date(dados_db.data_inicio) if dados_db else datetime.now())
    d_termino = c8.date_input("Data de Término", value=format_date(dados_db.data_termino) if dados_db else datetime.now())
    d_producao = c9.date_input("Entrada em Produção", value=format_date(dados_db.data_producao) if dados_db else datetime.now())

# 3. CHECKLIST
st.markdown("<h3 style='font-size: 20px; color: #143264; font-weight: bold;'>📋 Checklist do Projeto</h3>", unsafe_allow_html=True)
tabs = st.tabs(list(METODOLOGIA.keys()))
perc_fases, detalhes_entrega, estado_atual_checks = {}, {}, {}

for i, (fase, itens) in enumerate(METODOLOGIA.items()):
    with tabs[i]:
        concluidos = 0
        detalhes_entrega[fase] = []
        cols_check = st.columns(2)
        for idx, item in enumerate(itens):
            chave_check = f"{fase}_{item}"
            valor_previo = checklist_recuperado.get(chave_check, False)
            
            checked = cols_check[idx % 2].checkbox(item, value=valor_previo, key=f"chk_{chave_check}")
            estado_atual_checks[chave_check] = checked
            
            detalhes_entrega[fase].append({"doc": item, "status": "Concluído" if checked else "Pendente"})
            if checked: concluidos += 1
        perc_fases[fase] = (concluidos / len(itens)) * 100

# 4. EVOLUÇÃO
st.markdown("---")
global_avg = sum(perc_fases.values()) / len(perc_fases)
st.markdown(f"<h3 style='font-size: 20px; color: #143264; font-weight: bold;'>🛤️ Evolução da Implantação: {global_avg:.1f}%</h3>", unsafe_allow_html=True)

cols_spark = st.columns(len(perc_fases))
for i, (fase, valor) in enumerate(perc_fases.items()):
    with cols_
