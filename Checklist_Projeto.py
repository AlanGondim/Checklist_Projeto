import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fpdf import FPDF
from datetime import datetime
import io
import base64
import os

# --- DATABASE SETUP ---
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia.db'
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
    inicializacao = Column(Float)
    planejamento = Column(Float)
    workshop_de_processos = Column(Float)
    construcao = Column(Float)
    go_live = Column(Float)
    operacao_assistida = Column(Float)
    finalizacao = Column(Float)

# Reset do DB se houver mudança de colunas (para fins de desenvolvimento)
Base.metadata.create_all(engine)

# --- METODOLOGIA DE IMPLANTACAO ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial do Projeto", "Alinhamento do projeto com o time MV", "Ata de reunião" , "Alinhamento do projeto com o Cliente", "TAP - Termo de Abertura do Projeto", "DEP - Declaração de Escopo do Projeto"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião", "Cronograma do Projeto", "Plano de Projeto"],
    "Workshop de Processos": ["Levantamento e Análise de Gaps Críticos", "Business Blue Print", "Configuração do Sistema", "Apresentação da Solução", "Termo de Aceite de Entrega"],
    "Construção": ["Plano de Cutover", "Avaliação de Treinamento", "Lista de Presença" , "Treinamento de Tabelas", "Dados mestres e Carga Precursora", "Homologação de Integração com Terceiros"],
    "Go Live": ["Carga Final de Dados", "Escala Apoio ao Go Live", "Metas de Simulação", "Testes Integrados", "Reunição de Go/No Go", "Ata de Reunião"],
    "Operação Assistida": ["Suporte In Loco aos usuários", "Reunião de Pré-Onboarding", "Ata de Reunião", "Identificação de Gaps", "Termo de Aceite de Entrega"],
    "Finalização": ["Reunião de Finalização", "Ata de Reunião", "TEP - Termo de Encerramento do Projeto", "Registro de Lições Aprendidas - MV LEARN | Sharepoint"]
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
    planejado = [100.0] * (N + 1)
    
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angulos, planejado, color='#143264', linewidth=1, linestyle='--', label="Ideal")
    ax.plot(angulos, realizado, color='#ffb30e', linewidth=3, label="Realizado")
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.3)
    plt.xticks(angulos[:-1], categorias, size=7)
    return fig

class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Helvetica', 'B', 16); self.set_text_color(255, 255, 255)
        self.cell(190, 15, "STATUS REPORT EXECUTIVO - HUB DE INTELIGÊNCIA", ln=True, align='C')
        self.ln(15)

    def add_watermark(self):
        self.set_font("Helvetica", 'B', 50); self.set_text_color(245, 245, 245)
        with self.rotation(45, 105, 148): self.text(35, 190, "C O N F I D E N C I A L")

    def desenhar_sparkline_pdf(self, perc_fases, y_pos):
        x_start, largura_total = 20, 170
        passo = largura_total / (len(perc_fases) - 1)
        self.set_draw_color(200, 200, 200); self.set_line_width(0.5)
        self.line(x_start, y_pos + 5, x_start + largura_total, y_pos + 5)
        for i, (fase, valor) in enumerate(perc_fases.items()):
            x_circ = x_start + (i * passo)
            if valor > 0:
                self.set_fill_color(20, 50, 100); self.set_draw_color(255, 179, 14)
            else:
                self.set_fill_color(220, 220, 220); self.set_draw_color(200, 200, 200)
            self.ellipse(x_circ - 2, y_pos + 3, 4, 4, 'FD')
            self.set_font("Helvetica", 'B', 5); self.set_text_color(20, 50, 100)
            self.text(x_circ - 5, y_pos + 10, fase[:12])

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Hub de Inteligência", layout="wide")
st.title("🛡️ Metodologia | Gestão de Entregas e Conformidade")

# --- NOVOS CAMPOS LADO A LADO ---
with st.container():
    c1, c2, c3 = st.columns(3)
    nome_proj = c1.text_input("Nome do Projeto", placeholder="Ex: Hospital X")
    oportunidade = c2.text_input("Oportunidade (CRM)")
    gp_proj = c3.text_input("Gerente de Projeto")

    c4, c5, c6 = st.columns(3)
    horas_contratadas = c4.number_input("Horas Contratadas", min_value=0.0)
    tipo_projeto = c5.selectbox("Tipo", ["Implantação", "Revitalização", "Upgrade", "Consultoria"])
    resp_verificacao = c6.text_input("Responsável pela Verificação")

    c7, c8, c9 = st.columns(3)
    data_ini = c7.date_input("Data de Início")
    data_fim = c8.date_input("Data de Término")
    data_prod = c9.date_input("Data de Entrada em Produção")

st.write("### 📋 Checklist Metodológico")
tabs = st.tabs(list(METODOLOGIA.keys()))
perc_fases, detalhes_entrega = {}, {}

for i, (fase, itens) in enumerate(METODOLOGIA.items()):
    with tabs[i]:
        concluidos = 0
        detalhes_entrega[fase] = []
        cols_check = st.columns(2)
        for idx, item in enumerate(itens):
            checked = cols_check[idx % 2].checkbox(item, key=f"chk_{fase}_{item}")
            detalhes_entrega[fase].append({"doc": item, "status": "Concluído" if checked else "Pendente"})
            if checked: concluidos += 1
        perc_fases[fase] = (concluidos / len(itens)) * 100

st.markdown("---")
global_avg = sum(perc_fases.values()) / len(perc_fases)
st.write(f"### 🛤️ Progresso Global Realizado: {global_avg:.1f}%")

# Escala Visual
cols_spark = st.columns(len(perc_fases))
for i, (fase, valor) in enumerate(perc_fases.items()):
    with cols_spark[i]:
        cor_marco = "#143264" if valor > 0 else "#ddd"
        st.markdown(f"<div style='text-align: center;'><div style='display: inline-block; width: 15px; height: 15px; border-radius: 50%; background: {cor_marco};'></div><p style='font-size: 9px; font-weight: bold;'>{fase}<br>{valor:.0f}%</p></div>", unsafe_allow_html=True)

st.progress(global_avg / 100)

# --- AÇÕES ---
st.markdown("---")
col_graf, col_btn = st.columns([1.5, 1])

with col_graf:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    img_buf.seek(0)

with col_btn:
    st.subheader("⚙️ Hub de Governança")
    
    if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
        if nome_proj:
            dados_db = {
                "nome_projeto": nome_proj, "gerente_projeto": gp_proj,
                "oportunidade": oportunidade, "horas_contratadas": horas_contratadas,
                "tipo": tipo_projeto, "data_inicio": str(data_ini),
                "data_termino": str(data_fim), "data_producao": str(data_prod),
                "responsavel_verificacao": resp_verificacao
            }
            for f, v in perc_fases.items(): dados_db[MAPA_COLUNAS[f]] = v
            session.add(Projeto(**dados_db))
            session.commit()
            st.success("✅ Snapshot gravado com sucesso!")
        else:
            st.warning("Preencha o Nome do Projeto.")

    if st.button("📄 GERAR RELATÓRIO PDF EXECUTIVO", use_container_width=True, type="primary"):
        pdf = PDFExecutivo()
        pdf.add_page(); pdf.add_watermark()
        
        # Info do Projeto em Grade (PDF)
        pdf.set_font("Helvetica", 'B', 9); pdf.set_text_color(20, 50, 100)
        
        # Linha 1
        pdf.cell(63, 7, f"PROJETO: {nome_proj[:30]}", border=1)
        pdf.cell(63, 7, f"OPORTUNIDADE: {oportunidade}", border=1)
        pdf.cell(64, 7, f"GP: {gp_proj}", border=1, ln=True)
        
        # Linha 2
        pdf.cell(63, 7, f"HORAS: {horas_contratadas}", border=1)
        pdf.cell(63, 7, f"TIPO: {tipo_projeto}", border=1)
        pdf.cell(64, 7, f"RESP. VERIFICAÇÃO: {resp_verificacao}", border=1, ln=True)
        
        # Linha 3
        pdf.cell(63, 7, f"INÍCIO: {data_ini}", border=1)
        pdf.cell(63, 7, f"TÉRMINO: {data_fim}", border=1)
        pdf.cell(64, 7, f"GO-LIVE: {data_prod}", border=1, ln=True)
        
        pdf.ln(5)
        pdf.set_font("Helvetica", 'B', 10); pdf.cell(190, 8, f"PROGRESSO GLOBAL: {global_avg:.1f}%", ln=True, align='C')
        
        # Sparkline
        pdf.desenhar_sparkline_pdf(perc_fases, pdf.get_y())
        pdf.set_y(pdf.get_y() + 15)
        
        # Radar
        pdf.image(img_buf, x=65, w=80); pdf.ln(85)
        
        # Diagnóstico IA
        pdf.set_fill_color(255, 243, 205); pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(190, 8, "DIAGNÓSTICO: PENDÊNCIAS CRÍTICAS POR FASE", 0, 1, 'L', True)
        pdf.set_font("Helvetica", '', 8); pdf.set_text_color(50, 50, 50)
        
        for fase, itens in detalhes_entrega.items():
            pendentes = [i["doc"] for i in itens if i["status"] == "Pendente"]
            if pendentes:
                pdf.set_font("Helvetica", 'B', 8)
                pdf.cell(190, 5, f"> {fase}:", ln=True)
                pdf.set_font("Helvetica", '', 8)
                pdf.multi_cell(190, 4, f"Pendentes: {', '.join(pendentes)}")
                pdf.ln(1)

        pdf_bytes = pdf.output()
        st.download_button("📥 BAIXAR RELATÓRIO PDF", data=bytes(pdf_bytes), file_name=f"Report_{nome_proj}.pdf", mime="application/pdf", use_container_width=True)

# Footer
st.markdown("<br><center><p style='color: gray;'>Hub de Inteligência | Versão Executiva 2024</p></center>", unsafe_allow_html=True)
