import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fpdf import FPDF
from datetime import datetime
import io
import base64
import os
from PIL import Image

# --- DATABASE SETUP ---
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia_v4.db'
engine = create_engine(DB_NAME)
Session = sessionmaker(bind=engine)
session = Session()

class Projeto(Base):
    __tablename__ = 'monitoramento_projetos'
    id = Column(Integer, primary_key=True)
    nome_projeto = Column(String)
    oportunidade = Column(String)
    gerente_projeto = Column(String)
    horas_contratadas = Column(Float)
    tipo = Column(String)
    data_inicio = Column(String)
    data_termino = Column(String)
    data_producao = Column(String)
    responsavel_verificacao = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    # Percentuais das Fases
    inicializacao = Column(Float)
    planejamento = Column(Float)
    workshop_de_processos = Column(Float)
    construcao = Column(Float)
    go_live = Column(Float)
    operacao_assistida = Column(Float)
    finalizacao = Column(Float)

Base.metadata.create_all(engine)

# --- METODOLOGIA ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial", "Alinhamento time MV", "Ata de reunião", "Alinhamento Cliente", "TAP", "DEP"],
    "Planejamento": ["Evidência Kick Off", "Ata de Reunião", "Cronograma", "Plano de Projeto"],
    "Workshop de Processos": ["Levantamento Gaps Críticos", "Business Blue Print", "Configuração Sistema", "Apresentação Solução", "Aceite de Entrega"],
    "Construção": ["Plano Cutover", "Avaliação Treinamento", "Lista Presença", "Treinamento Tabelas", "Carga Precursora", "Integração Terceiros"],
    "Go Live": ["Carga Final Dados", "Escala Apoio", "Metas Simulação", "Testes Integrados", "Reunião Go/No Go", "Ata Reunião"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding", "Ata Reunião", "Identificação Gaps", "Aceite de Entrega"],
    "Finalização": ["Reunião Finalização", "Ata Reunião", "TEP", "Lições Aprendidas"]
}

MAPA_COLUNAS = {
    "Inicialização": "inicializacao", "Planejamento": "planejamento", 
    "Workshop de Processos": "workshop_de_processos", "Construção": "construcao",
    "Go Live": "go_live", "Operação Assistida": "operacao_assistida", "Finalização": "finalizacao"
}

# --- FUNÇÕES DE APOIO ---
def gerar_radar_chart(realizado_dict):
    categorias = list(realizado_dict.keys())
    valores = list(realizado_dict.values())
    N = len(categorias)
    angulos = [n / float(N) * 2 * np.pi for n in range(N)]
    angulos += angulos[:1]
    realizado = valores + valores[:1]
    
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angulos, [100]*len(angulos), color='#143264', linewidth=1, linestyle='--')
    ax.plot(angulos, realizado, color='#ffb30e', linewidth=3, label="Realizado")
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.3)
    plt.xticks(angulos[:-1], categorias, size=7, fontweight='bold')
    return fig

class PDFExecutivo(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path

    def header(self):
        # Cabeçalho Azul Marinho
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 40, 'F')
        
        # Logomarca MV (Lado Esquerdo)
        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, x=10, y=10, w=15) # Pequena e discreta
            
        self.set_font('Helvetica', 'B', 15); self.set_text_color(255, 255, 255)
        self.set_xy(30, 12)
        self.cell(160, 10, "STATUS REPORT EXECUTIVO - HUB DE INTELIGÊNCIA", ln=True, align='C')
        self.ln(18)

    def add_watermark(self):
        self.set_font("Helvetica", 'B', 50); self.set_text_color(248, 248, 248)
        with self.rotation(45, 105, 148):
            self.text(40, 160, "C O N F I D E N C I A L")

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="MV Executive Hub", layout="wide")

# Lógica para salvar a imagem carregada temporariamente para o PDF
LOGO_FILE = "logo_mv.png"

st.title("🛡️ Gestão de Entregas | Metodologia de Implantação")

# --- FORMULÁRIO DE DADOS GERAIS ---
with st.expander("📝 Dados do Projeto", expanded=True):
    col1, col2, col3 = st.columns(3)
    nome_proj = col1.text_input("Nome do Projeto", placeholder="Hospital Digital X")
    oportunidade = col2.text_input("Oportunidade (CRM)")
    gp_proj = col3.text_input("Gerente de Projetos")

    col4, col5, col6 = st.columns(3)
    horas_cont = col4.number_input("Horas Contratadas", min_value=0.0)
    tipo_proj = col5.selectbox("Tipo", ["Implantação", "Revitalização", "Upgrade", "Consultoria"])
    resp_verif = col6.text_input("Responsável pela Verificação")

    col7, col8, col9 = st.columns(3)
    d_ini = col7.date_input("Data de Início")
    d_ter = col8.date_input("Data de Término")
    d_prod = col9.date_input("Entrada em Produção")

# --- CHECKLIST ---
st.write("### 📋 Checklist Metodológico")
tabs = st.tabs(list(METODOLOGIA.keys()))
perc_fases, detalhes_entrega = {}, {}

for i, (fase, itens) in enumerate(METODOLOGIA.items()):
    with tabs[i]:
        concluidos = 0
        detalhes_entrega[fase] = []
        c_check = st.columns(2)
        for idx, item in enumerate(itens):
            chk = c_check[idx % 2].checkbox(item, key=f"v_{fase}_{item}")
            detalhes_entrega[fase].append({"doc": item, "status": "OK" if chk else "PENDENTE"})
            if chk: concluidos += 1
        perc_fases[fase] = (concluidos / len(itens)) * 100

# --- CÁLCULO GLOBAL ---
global_avg = sum(perc_fases.values()) / len(perc_fases)
st.divider()
st.progress(global_avg / 100)
st.write(f"**Progresso Atual: {global_avg:.1f}%**")

# --- AÇÕES ---
col_radar, col_actions = st.columns([1.5, 1])

with col_radar:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)

with col_actions:
    st.subheader("⚙️ Ações de Governança")
    
    if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
        if nome_proj:
            try:
                dados = {
                    "nome_projeto": nome_proj, "oportunidade": oportunidade, "gerente_projeto": gp_proj,
                    "horas_contratadas": horas_cont, "tipo": tipo_proj, "responsavel_verificacao": resp_verif,
                    "data_inicio": str(d_ini), "data_termino": str(d_ter), "data_producao": str(d_prod)
                }
                for f, v in perc_fases.items(): dados[MAPA_COLUNAS[f]] = v
                session.add(Projeto(**dados))
                session.commit()
                st.success("✅ Snapshot salvo no Hub com sucesso!")
            except Exception as e: st.error(f"Erro: {e}")
        else: st.warning("Defina o Nome do Projeto.")

    if st.button("📄 GERAR RELATÓRIO PDF (ONE-PAGE)", use_container_width=True, type="primary"):
        pdf = PDFExecutivo(logo_path="Logomarca MV Atualizada.png")
        pdf.add_page(); pdf.add_watermark()
        
        # Grid de Informações do Projeto
        pdf.set_font("Helvetica", 'B', 8); pdf.set_text_color(50, 50, 50)
        
        # Linha 1
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(63, 8, f" PROJETO: {nome_proj[:30]}", 1, 0, 'L', True)
        pdf.cell(63, 8, f" OPORTUNIDADE: {oportunidade}", 1, 0, 'L', True)
        pdf.cell(64, 8, f" GP: {gp_proj}", 1, 1, 'L', True)
        
        # Linha 2
        pdf.cell(63, 8, f" HORAS: {horas_cont}", 1, 0, 'L')
        pdf.cell(63, 8, f" TIPO: {tipo_proj}", 1, 0, 'L')
        pdf.cell(64, 8, f" RESP. VERIF: {resp_verif}", 1, 1, 'L')
        
        # Linha 3
        pdf.cell(63, 8, f" INÍCIO: {d_ini}", 1, 0, 'L', True)
        pdf.cell(63, 8, f" TÉRMINO: {d_ter}", 1, 0, 'L', True)
        pdf.cell(64, 8, f" PRODUÇÃO: {d_prod}", 1, 1, 'L', True)
        
        pdf.ln(5)
        # Radar Chart
        pdf.image(buf, x=65, w=80); pdf.ln(85)
        
        # Resumo de Pendências
        pdf.set_fill_color(255, 243, 205); pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(190, 8, " DIAGNÓSTICO DE PENDÊNCIAS POR FASE", 0, 1, 'L', True)
        pdf.set_font("Helvetica", '', 8); pdf.set_text_color(0, 0, 0)
        
        for fase, itens in detalhes_entrega.items():
            pends = [i["doc"] for i in itens if i["status"] == "PENDENTE"]
            if pends:
                pdf.set_font("Helvetica", 'B', 8); pdf.cell(190, 5, f"> {fase}:", ln=True)
                pdf.set_font("Helvetica", '', 8); pdf.multi_cell(190, 4, f" Pendentes: {', '.join(pends)}")
                pdf.ln(1)

        pdf_out = pdf.output()
        st.download_button("📥 BAIXAR PDF EXECUTIVO", data=bytes(pdf_out), file_name=f"Status_{nome_proj}.pdf", mime="application/pdf", use_container_width=True)

st.markdown("<center style='color:gray; font-size:10px;'>MV Hub de Inteligência © 2026</center>", unsafe_allow_html=True)
