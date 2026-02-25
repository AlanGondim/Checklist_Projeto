import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fpdf import FPDF
from datetime import datetime
import qrcode
import io
import os

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
    
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.plot(angulos, [100.0]*(N+1), color='#143264', linewidth=1, linestyle='--')
    ax.plot(angulos, realizado, color='#ffb30e', linewidth=2.5, label="Realizado")
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.3)
    plt.xticks(angulos[:-1], ["Ini", "Plan", "Work", "Const", "Live", "Op", "Fin"], size=7, fontweight='bold')
    ax.set_yticklabels([])
    return fig

def gerar_qrcode(link):
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(link)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="#143264", back_color="white")
    buf = io.BytesIO()
    img_qr.save(buf, format='PNG')
    buf.seek(0)
    return buf

class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 35, 'F')
        if os.path.exists("Logomarca MV Atualizada.png"):
            self.image("Logomarca MV Atualizada.png", x=10, y=8, w=18)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(30, 12)
        self.cell(150, 10, "STATUS REPORT EXECUTIVO - HUB DE INTELIGÊNCIA", ln=True, align='C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(150, 150, 150)
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.cell(0, 10, f"Autenticidade: {ts} | Gerado via MV Intelligence Hub | Pagina {self.page_no()}", 0, 0, 'C')

    def add_watermark(self):
        self.set_font("Helvetica", 'B', 50)
        self.set_text_color(248, 248, 248)
        with self.rotation(45, 105, 148):
            self.text(45, 155, "C O N F I D E N C I A L")

    def desenhar_sparkline(self, perc_fases, y_pos):
        x_start, largura_total = 20, 170
        passo = largura_total / (len(perc_fases) - 1)
        
        # Linha de conexão azul marinho
        self.set_draw_color(20, 50, 100)
        self.set_line_width(0.8)
        self.line(x_start, y_pos + 4, x_start + largura_total, y_pos + 4)
        
        for i, (fase, valor) in enumerate(perc_fases.items()):
            x_circ = x_start + (i * passo)
            
            # Círculo Azul Marinho
            self.set_fill_color(20, 50, 100)
            
            # Borda amarela se incompleto (>0 e <100)
            if 0 < valor < 100:
                self.set_draw_color(255, 179, 14)
                self.set_line_width(1.0)
            else:
                self.set_draw_color(20, 50, 100)
                self.set_line_width(0.2)
            
            self.ellipse(x_circ - 3, y_pos + 1, 6, 6, 'FD')
            
            self.set_font("Helvetica", 'B', 6)
            self.set_text_color(20, 50, 100)
            self.text(x_circ - 5, y_pos + 10, f"{valor:.0f}%")

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="MV Executive Hub", layout="wide")
st.title("🛡️ Governança de Metodologia e Entregas")

with st.sidebar:
    st.header("🔍 Consultar Projetos")
    projetos_salvos = [p.nome_projeto for p in session.query(Projeto.nome_projeto).distinct().all()]
    projeto_busca = st.selectbox("Carregar do Hub", [""] + projetos_salvos)

with st.container():
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Projeto", value=projeto_busca if projeto_busca else "")
    oportunidade = c2.text_input("CRM / Oportunidade")
    gp_p = c3.text_input("GP Responsável")

    c4, c5, c6 = st.columns(3)
    horas_cont = c4.number_input("Horas Contratadas", min_value=0.0, step=10.0)
    tipo_p = c5.selectbox("Tipo de Escopo", ["Implantação", "Migração", "Revitalização"])
    resp_v = c6.text_input("Validador")

    c7, c8, c9 = st.columns(3)
    d_ini = c7.date_input("Data Início", format="DD/MM/YYYY")
    d_ter = c8.date_input("Data Término", format="DD/MM/YYYY")
    d_pro = c9.date_input("Produção", format="DD/MM/YYYY")

tabs = st.tabs(list(METODOLOGIA.keys()))
perc_fases, detalhes_entrega = {}, {}

for i, (fase, itens) in enumerate(METODOLOGIA.items()):
    with tabs[i]:
        concluidos = 0
        detalhes_entrega[fase] = []
        cols = st.columns(2)
        for idx, item in enumerate(itens):
            chk = cols[idx % 2].checkbox(item, key=f"v_{fase}_{item}")
            detalhes_entrega[fase].append({"doc": item, "status": "OK" if chk else "Pendente"})
            if chk: concluidos += 1
        perc_fases[fase] = (concluidos / len(itens)) * 100

st.divider()
avg_global = sum(perc_fases.values()) / len(perc_fases)
st.progress(avg_global / 100)

col_radar, col_actions = st.columns([1.5, 1])
with col_radar:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight', dpi=150)
    img_buf.seek(0)

with col_actions:
    if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
        if nome_p:
            ts = datetime.now()
            novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, oportunidade=oportunidade,
                           horas_contratadas=horas_cont, tipo=tipo_p, responsavel_verificacao=resp_v,
                           data_inicio=d_ini.strftime("%d/%m/%Y"), data_termino=d_ter.strftime("%d/%m/%Y"),
                           data_producao=d_pro.strftime("%d/%m/%Y"), timestamp=ts,
                           **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
            session.add(novo); session.commit()
            st.success(f"Snapshot salvo: {ts.strftime('%d/%m/%Y %H:%M')}")
        else: st.warning("Defina o Projeto.")

    if st.button("📄 GERAR RELATÓRIO ONE-PAGE", type="primary", use_container_width=True):
        pdf = PDFExecutivo()
        pdf.add_page(); pdf.add_watermark()
        
        # 1. Grid de Dados do Projeto
        pdf.set_y(40)
        pdf.set_font("Helvetica", 'B', 8); pdf.set_text_color(20, 50, 100); pdf.set_fill_color(245, 245, 245)
        pdf.cell(63, 7, f" PROJETO: {nome_p.upper()}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" CRM: {oportunidade}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" GP: {gp_p}", 1, 1, 'L', True)
        pdf.cell(63, 7, f" INÍCIO: {d_ini.strftime('%d/%m/%Y')}", 1, 0, 'L')
        pdf.cell(63, 7, f" TÉRMINO: {d_ter.strftime('%d/%m/%Y')}", 1, 0, 'L')
        pdf.cell(64, 7, f" PRODUÇÃO: {d_pro.strftime('%d/%m/%Y')}", 1, 1, 'L')
        
        # 2. Sparkline (Marco Metodológico)
        pdf.ln(6)
        pdf.desenhar_sparkline(perc_fases, pdf.get_y())
        
        # 3. Radar e QR Code (Lado a Lado)
        # Fixamos o Y para o Radar para evitar que ele desça demais
        radar_y = 78 
        pdf.image(img_buf, x=15, y=radar_y, w=85)
        
        qr_buf = gerar_qrcode(f"https://hub.mv.com.br/valida?id={nome_p}")
        pdf.image(qr_buf, x=135, y=radar_y + 10, w=35)
        pdf.set_xy(135, radar_y + 46); pdf.set_font("Helvetica", 'I', 6)
        pdf.cell(35, 5, "Escanear para Autenticidade", 0, 0, 'C')
        
        # 4. Diagnóstico IA (Posição Garantida no final da página)
        # Ajustamos o Y para que comece logo após o Radar terminar
        pdf.set_y(radar_y + 75) 
        pdf.set_fill_color(255, 243, 205); pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(190, 8, " INTELIGÊNCIA DE ENTREGA: DIAGNÓSTICO DE PENDÊNCIAS", 0, 1, 'L', True)
        
        pdf.set_font("Helvetica", '', 7); pdf.set_text_color(60, 60, 60); pdf.ln(1)
        for fase, itens in detalhes_entrega.items():
            pend = [i["doc"] for i in itens if i["status"] == "Pendente"]
            if pend:
                pdf.set_font("Helvetica", 'B', 7)
                pdf.cell(190, 4, f"> {fase}:", ln=True)
                pdf.set_font("Helvetica", '', 7)
                pdf.multi_cell(190, 3.5, f"Pendências críticas: {', '.join(pend[:6])}...")
                pdf.ln(0.5)
                
        st.download_button("📥 BAIXAR RELATÓRIO PDF", data=bytes(pdf.output()), file_name=f"Report_{nome_p}.pdf")
