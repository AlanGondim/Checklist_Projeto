import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fpdf import FPDF
from datetime import datetime
import qrcode
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
    checklist_json = Column(Text) 
    inicializacao = Column(Float); planejamento = Column(Float)
    workshop_de_processos = Column(Float); construcao = Column(Float)
    go_live = Column(Float); operacao_assistida = Column(Float)
    finalizacao = Column(Float)

Base.metadata.create_all(engine)

# --- METODOLOGIA ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial", "Alinhamento time MV", "Ata de reunião", "Alinhamento Cliente", "TAP", "DEP"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião", "Cronograma do Projeto", "Plano de Projeto"],
    "Workshop de Processos": ["Análise de Gaps Críticos", "Business Blue Print", "Configuração do Sistema", "Apresentação da Solução", "Termo de Aceite"],
    "Construção": ["Plano de Cutover", "Avaliação de Treinamento", "Lista de Presença", "Treinamento de Tabelas", "Carga Precursora", "Homologação Integração"],
    "Go Live": ["Carga Final de Dados", "Escala Apoio Go Live", "Metas de Simulação", "Testes Integrados", "Reunião Go/No Go", "Ata de Reunião"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding", "Ata de Reunião", "Identificação de Gaps", "Termo de Aceite"],
    "Finalização": ["Reunião de Finalização", "Ata de Reunião", "TEP", "Lições Aprendidas - MV LEARN"]
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
    ax.plot(angulos, realizado, color='#ffb30e', linewidth=3)
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.3)
    plt.xticks(angulos[:-1], ["Ini", "Plan", "Work", "Const", "Live", "Op", "Fin"], size=8, fontweight='bold')
    return fig

def gerar_qr_code(dados):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(dados)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#143264", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

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
        self.cell(0, 10, f"Protocolo: {ts} | MV Intelligence Hub | Pagina {self.page_no()}", 0, 0, 'C')

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Hub MV", layout="wide")
st.markdown("<h2 style='font-size: 24px; color: #143264; font-weight: bold;'>🏛️ Hub de Inteligência | Governança e Metodologia</h2>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 Consultar Hub")
    projetos_salvos = [p.nome_projeto for p in session.query(Projeto.nome_projeto).distinct().all()]
    projeto_busca = st.selectbox("Carregar Projeto Existente", [""] + projetos_salvos)
    
    if st.button("🆕 INICIAR NOVO PROJETO (LIMPAR)"):
        st.session_state.clear()
        st.rerun()

# Recuperação de Dados
dados_db = None
checklist_recuperado = {}
if projeto_busca:
    dados_db = session.query(Projeto).filter_by(nome_projeto=projeto_busca).order_by(Projeto.timestamp.desc()).first()
    if dados_db and dados_db.checklist_json:
        checklist_recuperado = json.loads(dados_db.checklist_json)

# Campos de Entrada
with st.container():
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Nome do Projeto", value=dados_db.nome_projeto if dados_db else "")
    oportunidade = c2.text_input("Oportunidade (CRM)", value=dados_db.oportunidade if dados_db else "")
    gp_p = c3.text_input("Gerente de Projeto", value=dados_db.gerente_projeto if dados_db else "")

    c4, c5, c6 = st.columns(3)
    horas_cont = c4.number_input("Horas", value=float(dados_db.horas_contratadas) if dados_db else 0.0, step=10.0)
    tipo_p = c5.selectbox("Tipo", ["Implantação", "Migração", "Revitalização"], index=0)
    resp_v = c6.text_input("Responsável Verificação", value=dados_db.responsavel_verificacao if dados_db else "")

# Checklist
st.markdown("<h3 style='font-size: 20px; color: #143264; font-weight: bold;'>📋 Checklist do Projeto</h3>", unsafe_allow_html=True)
tabs = st.tabs(list(METODOLOGIA.keys()))
perc_fases, estado_checklist_atual = {}, {}

for i, (fase, itens) in enumerate(METODOLOGIA.items()):
    with tabs[i]:
        concluidos = 0
        cols_check = st.columns(2)
        for idx, item in enumerate(itens):
            chave = f"{fase}_{item}"
            valor_previo = checklist_recuperado.get(chave, False)
            checked = cols_check[idx % 2].checkbox(item, value=valor_previo, key=f"chk_{chave}")
            estado_checklist_atual[chave] = checked
            if checked: concluidos += 1
        perc_fases[fase] = (concluidos / len(itens)) * 100

# Evolução
st.divider()
global_avg = sum(perc_fases.values()) / len(perc_fases)
st.markdown(f"<h3 style='font-size: 20px; color: #143264; font-weight: bold;'>🛤️ Evolução da Implantação: {global_avg:.1f}%</h3>", unsafe_allow_html=True)
cols_spark = st.columns(len(perc_fases))
for i, (fase, valor) in enumerate(perc_fases.items()):
    with cols_spark[i]:
        bg = "#143264" if valor > 0 else "#eeeeee"
        border = "border: 3px solid #143264;" if valor >= 100 else ("border: 3px solid #ffb30e;" if valor > 0 else "border: 1px solid #cccccc;")
        st.markdown(f"<div style='text-align: center;'><div style='display: inline-block; width: 25px; height: 25px; border-radius: 50%; background: {bg}; {border}'></div><p style='font-size: 11px; font-weight: bold; color: #143264;'>{fase}</p></div>", unsafe_allow_html=True)
st.progress(global_avg / 100)

# Ações
col_radar, col_btn = st.columns([1.5, 1])
with col_radar:
    fig = gerar_radar_chart(perc_fases); st.pyplot(fig)
    img_buf = io.BytesIO(); fig.savefig(img_buf, format='png', bbox_inches='tight'); img_buf.seek(0)

with col_btn:
    if st.button("💾 SALVAR SNAPSHOT NO HUB", use_container_width=True):
        if nome_p:
            try:
                novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, oportunidade=oportunidade,
                               horas_contratadas=horas_cont, tipo=tipo_p, responsavel_verificacao=resp_v,
                               checklist_json=json.dumps(estado_checklist_atual),
                               **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
                session.add(novo); session.commit()
                st.success(f"✅ Salvo com sucesso!"); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")

    if st.button("📄 GERAR RELATÓRIO ONE-PAGE", use_container_width=True, type="primary"):
        pdf = PDFExecutivo(); pdf.add_page()
        pdf.set_y(40); pdf.set_font("Helvetica", 'B', 8); pdf.set_text_color(20, 50, 100); pdf.set_fill_color(245, 245, 245)
        pdf.cell(63, 7, f" PROJETO: {nome_p.upper()}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" CRM: {oportunidade}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" GP: {gp_p}", 1, 1, 'L', True)
        # Detalhamento IA...
        pdf.image(img_buf, x=65, y=85, w=80)
        qr_buf = gerar_qr_code(f"https://hub.mv.com.br/valida?id={nome_p}")
        pdf.image(qr_buf, x=170, y=40, w=25)
        st.download_button("📥 BAIXAR PDF", data=bytes(pdf.output()), file_name=f"Report_{nome_p}.pdf")
