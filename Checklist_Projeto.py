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

# --- DATABASE SETUP & AUTO-FIX ---
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

# Reset do DB para garantir novas colunas (Remova em produção se houver dados críticos)
Base.metadata.create_all(engine)

# --- METODOLOGIA DE IMPLANTACAO ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial", "Alinhamento time MV", "Ata de reunião", "Alinhamento Cliente", "TAP", "DEP"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião", "Cronograma do Projeto", "Plano de Projeto"],
    "Workshop de Processos": ["Análise de Gaps Críticos", "Business Blue Print", "Configuração do Sistema", "Apresentação da Solução", "Termo de Aceite"],
    "Construção": ["Plano de Cutover", "Avaliação de Treinamento", "Lista de Presença", "Treinamento de Tabelas", "Carga Precursora", "Homologação Integração"],
    "Go Live": ["Carga Final de Dados", "Escala Apoio Go Live", "Metas de Simulação", "Testes Integrados", "Reunião Go/No Go", "Ata de Reunião"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding", "Ata de Reunião", "Identificação de Gaps", "Termo de Aceite"],
    "Finalização": ["Reunião de Finalização", "Ata de Reunião", "TEP", "Lições Aprendidas"]
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
    ax.plot(angulos, [100.0]*(N+1), color='#143264', linewidth=1, linestyle='--', label="Ideal")
    ax.plot(angulos, realizado, color='#ffb30e', linewidth=3, label="Realizado")
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.3)
    plt.xticks(angulos[:-1], categorias, size=8)
    return fig

class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 40, 'F')
        
        # Logomarca (Certifique-se que o arquivo existe)
        if os.path.exists("Logomarca MV Atualizada.png"):
            self.image("Logomarca MV Atualizada.png", x=10, y=8, w=22)
            
        self.set_font('Helvetica', 'B', 16); self.set_text_color(255, 255, 255)
        self.set_xy(35, 15)
        self.cell(140, 10, "STATUS REPORT EXECUTIVO - HUB DE INTELIGÊNCIA", ln=True, align='C')
        self.ln(20)

    def add_watermark(self):
        self.set_font("Helvetica", 'B', 50); self.set_text_color(248, 248, 248)
        with self.rotation(45, 105, 148):
            self.text(40, 160, "C O N F I D E N C I A L")

    def desenhar_sparkline_pdf(self, perc_fases, y_pos):
        x_start, largura_total = 20, 170
        passo = largura_total / (len(perc_fases) - 1)
        self.set_draw_color(200, 200, 200); self.set_line_width(0.5)
        self.line(x_start, y_pos + 5, x_start + largura_total, y_pos + 5)
        for i, (fase, valor) in enumerate(perc_fases.items()):
            x_circ = x_start + (i * passo)
            cor = (20, 50, 100) if valor > 0 else (220, 220, 220)
            self.set_fill_color(*cor)
            self.ellipse(x_circ - 2, y_pos + 3, 4, 4, 'FD')
            self.set_font("Helvetica", 'B', 5); self.set_text_color(20, 50, 100)
            self.text(x_circ - 6, y_pos + 10, fase[:12])

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Hub", layout="wide")
st.title("🛡️ Metodologia | Gestão de Entregas e Conformidade")

# --- CAMPOS DE DADOS DO PROJETO ---
with st.container():
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Nome do Projeto", placeholder="Ex: Hospital Central")
    oportunidade = c2.text_input("Oportunidade (CRM)")
    gp_p = c3.text_input("Gerente de Projeto")

    c4, c5, c6 = st.columns(3)
    horas_cont = c4.number_input("Horas Contratadas", min_value=0.0)
    tipo_p = c5.selectbox("Tipo", ["Implantação", "Revitalização", "Upgrade", "Consultoria"])
    resp_verificacao = c6.text_input("Responsável pela Verificação")

    c7, c8, c9 = st.columns(3)
    d_inicio = c7.date_input("Data de Início")
    d_termino = c8.date_input("Data de Término")
    d_producao = c9.date_input("Entrada em Produção")

st.write("### 📋 Checklist do Projeto")
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

global_avg = sum(perc_fases.values()) / len(perc_fases)
st.divider()
st.progress(global_avg / 100)

# --- AÇÕES ---
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
        if nome_p:
            try:
                dados_db = {
                    "nome_projeto": nome_p, "gerente_projeto": gp_p, "oportunidade": oportunidade,
                    "horas_contratadas": horas_cont, "tipo": tipo_p, "responsavel_verificacao": resp_verificacao,
                    "data_inicio": str(d_inicio), "data_termino": str(d_termino), "data_producao": str(d_producao)
                }
                for f, v in perc_fases.items(): dados_db[MAPA_COLUNAS[f]] = v
                session.add(Projeto(**dados_db))
                session.commit()
                st.toast("✅ Dados sincronizados!", icon="💾")
            except Exception as e: st.error(f"Erro: {e}")
        else: st.warning("Informe o nome do projeto.")

    if st.button("📄 GERAR RELATÓRIO EXECUTIVO", use_container_width=True, type="primary"):
        pdf = PDFExecutivo()
        pdf.add_page(); pdf.add_watermark()
        
        # Grid de Informações
        pdf.set_font("Helvetica", 'B', 8); pdf.set_text_color(20, 50, 100)
        pdf.set_fill_color(245, 245, 245)
        
        # Linha 1
        pdf.cell(63, 7, f" PROJETO: {nome_p.upper()}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" OPORTUNIDADE: {oportunidade}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" GP: {gp_p}", 1, 1, 'L', True)
        
        # Linha 2
        pdf.cell(63, 7, f" HORAS: {horas_cont}", 1, 0, 'L')
        pdf.cell(63, 7, f" TIPO: {tipo_p}", 1, 0, 'L')
        pdf.cell(64, 7, f" RESP. VERIFICAÇÃO: {resp_verificacao}", 1, 1, 'L')
        
        # Linha 3
        pdf.cell(63, 7, f" INÍCIO: {d_inicio}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" TÉRMINO: {d_termino}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" PRODUÇÃO: {d_producao}", 1, 1, 'L', True)
        
        pdf.ln(5)
        pdf.desenhar_sparkline_pdf(perc_fases, pdf.get_y())
        pdf.set_y(pdf.get_y() + 15)
        
        pdf.image(img_buf, x=65, w=80); pdf.ln(80)
        
        pdf.set_fill_color(255, 243, 205); pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(190, 8, "DIAGNÓSTICO IA: PENDÊNCIAS E PRÓXIMOS PASSOS", 0, 1, 'L', True); pdf.ln(2)
        pdf.set_font("Helvetica", '', 8); pdf.set_text_color(50, 50, 50)
        
        for fase, itens in detalhes_entrega.items():
            pend = [i["doc"] for i in itens if i["status"] == "Pendente"]
            if pend:
                pdf.multi_cell(190, 5, f"> {fase}: {', '.join(pend[:4])}...", border='B')
        
        pdf_bytes = pdf.output()
        st.download_button("📥 BAIXAR PDF", data=bytes(pdf_bytes), file_name=f"Status_{nome_p}.pdf", mime="application/pdf", use_container_width=True)
