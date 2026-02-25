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
    "Go Live": ["Carga Final de Dados", "Escala Apoio Go Live", "Metas de Simulação", "Testes Integrados", "Reunição Go/No Go", "Ata de Reunião"],
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
    plt.xticks(angulos[:-1], categorias, size=6, fontweight='bold')
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
        # Topo azul escuro
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 35, 'F')
        
        # Logo MV
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
        self.cell(0, 10, f"Protocolo de Autenticidade: {ts} | Documento Gerado via MV Intelligence Hub | Pagina {self.page_no()}", 0, 0, 'C')

    def add_watermark(self):
        self.set_font("Helvetica", 'B', 50)
        self.set_text_color(245, 245, 245)
        with self.rotation(45, 105, 148):
            self.text(45, 155, "C O N F I D E N C I A L")

    def desenhar_sparkline(self, perc_fases, y_pos):
        x_start, largura_total = 15, 180
        passo = largura_total / (len(perc_fases) - 1)
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.5)
        self.line(x_start, y_pos + 4, x_start + largura_total, y_pos + 4)
        
        for i, (fase, valor) in enumerate(perc_fases.items()):
            x_circ = x_start + (i * passo)
            if valor >= 100:
                self.set_fill_color(20, 50, 100)
                self.set_draw_color(20, 50, 100)
            elif valor > 0:
                self.set_fill_color(20, 50, 100)
                self.set_draw_color(255, 179, 14)
                self.set_line_width(0.6)
            else:
                self.set_fill_color(240, 240, 240)
                self.set_draw_color(200, 200, 200)
            
            self.ellipse(x_circ - 2.5, y_pos + 1.5, 5, 5, 'FD')
            self.set_font("Helvetica", 'B', 5)
            self.set_text_color(20, 50, 100)
            # Encurta nomes para caber
            nome_fase = fase.split(" ")[-1] if " " in fase else fase
            self.text(x_circ - 5, y_pos + 10, f"{nome_fase}: {valor:.0f}%")

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Hub Executivo MV", layout="wide")
st.title("🛡️ Gestão de Entregas e Metodologia")

# Busca Lateral
with st.sidebar:
    st.header("🔍 Consultar Hub")
    projetos_salvos = [p.nome_projeto for p in session.query(Projeto.nome_projeto).distinct().all()]
    projeto_busca = st.selectbox("Selecionar Projeto", [""] + projetos_salvos)

# Input de Dados
with st.container():
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Nome do Projeto", value=projeto_busca if projeto_busca else "")
    oportunidade = c2.text_input("Oportunidade (CRM)")
    gp_p = c3.text_input("Gerente de Projeto")

    c4, c5, c6 = st.columns(3)
    horas_cont = c4.number_input("Horas Contratadas", min_value=0.0, step=10.0)
    tipo_p = c5.selectbox("Tipo", ["Implantação", "Migração", "Revitalização", "Consultoria"])
    resp_v = c6.text_input("Responsável Verificação")

    c7, c8, c9 = st.columns(3)
    d_ini = c7.date_input("Início", format="DD/MM/YYYY")
    d_ter = c8.date_input("Término", format="DD/MM/YYYY")
    d_pro = c9.date_input("Produção", format="DD/MM/YYYY")

# Checklist
st.write("### 📋 Checklist Metodológico")
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

# Progresso
st.divider()
avg_global = sum(perc_fases.values()) / len(perc_fases)
st.write(f"### 🛤️ Evolução Consolidada: {avg_global:.1f}%")
st.progress(avg_global / 100)

# Ações e Gráfico
col_radar, col_acoes = st.columns([1.5, 1])
with col_radar:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight', dpi=150)
    img_buf.seek(0)

with col_acoes:
    st.subheader("⚙️ Hub de Governança")
    if st.button("💾 SALVAR SNAPSHOT NO HUB", use_container_width=True):
        if nome_p:
            ts_now = datetime.now()
            novo_snapshot = Projeto(
                nome_projeto=nome_p, gerente_projeto=gp_p, oportunidade=oportunidade,
                horas_contratadas=horas_cont, tipo=tipo_p, responsavel_verificacao=resp_v,
                data_inicio=d_ini.strftime("%d/%m/%Y"), data_termino=d_ter.strftime("%d/%m/%Y"),
                data_producao=d_pro.strftime("%d/%m/%Y"), timestamp=ts_now,
                **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()}
            )
            session.add(novo_snapshot); session.commit()
            st.success(f"✅ Snapshot salvo em {ts_now.strftime('%d/%m/%Y %H:%M')}")
            st.toast("Hub Sincronizado!", icon="🚀")
        else:
            st.warning("Preencha o Nome do Projeto.")

    if st.button("📄 GERAR RELATÓRIO ONE-PAGE", type="primary", use_container_width=True):
        pdf = PDFExecutivo()
        pdf.add_page(); pdf.add_watermark()
        
        # Grid de Informações
        pdf.set_y(40)
        pdf.set_font("Helvetica", 'B', 9); pdf.set_text_color(20, 50, 100)
        pdf.set_fill_color(245, 245, 245)
        
        pdf.cell(63, 7, f" PROJETO: {nome_p.upper()}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" CRM: {oportunidade}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" GP: {gp_p}", 1, 1, 'L', True)
        
        pdf.cell(63, 7, f" HORAS: {horas_cont}", 1, 0, 'L')
        pdf.cell(63, 7, f" TIPO: {tipo_p}", 1, 0, 'L')
        pdf.cell(64, 7, f" RESPONSÁVEL: {resp_v}", 1, 1, 'L')
        
        pdf.cell(63, 7, f" INÍCIO: {d_ini.strftime('%d/%m/%Y')}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" TÉRMINO: {d_ter.strftime('%d/%m/%Y')}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" PRODUÇÃO: {d_pro.strftime('%d/%m/%Y')}", 1, 1, 'L', True)
        
        # Sparkline
        pdf.ln(5)
        pdf.desenhar_sparkline(perc_fases, pdf.get_y())
        
        # QR Code e Radar lado a lado
        pdf.set_y(85)
        pdf.image(img_buf, x=15, w=85)
        
        link_qr = f"https://hub.mv.com.br/validar?id={nome_p.replace(' ', '_')}"
        qr_buf = gerar_qrcode(link_qr)
        pdf.image(qr_buf, x=140, y=95, w=35)
        pdf.set_xy(140, 132); pdf.set_font("Helvetica", 'I', 6)
        pdf.cell(35, 5, "Escanear para Autenticidade", 0, 0, 'C')
        
        # Diagnóstico IA
        pdf.set_y(155)
        pdf.set_fill_color(255, 243, 205)
        pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(190, 8, " INTELIGÊNCIA DE ENTREGA: DIAGNÓSTICO DE PENDÊNCIAS", 0, 1, 'L', True)
        
        pdf.set_font("Helvetica", '', 8); pdf.set_text_color(60, 60, 60)
        pdf.ln(2)
        for fase, itens in detalhes_entrega.items():
            pendentes = [i["doc"] for i in itens if i["status"] == "Pendente"]
            if pendentes:
                pdf.set_font("Helvetica", 'B', 8)
                pdf.cell(190, 5, f"> {fase}:", ln=True)
                pdf.set_font("Helvetica", '', 7)
                pdf.multi_cell(190, 4, f"Pendências críticas detectadas: {', '.join(pendentes[:6])}...")
                pdf.ln(1)
                
        st.download_button("📥 BAIXAR RELATÓRIO FINAL", data=bytes(pdf.output()), file_name=f"Executive_Report_{nome_p}.pdf")
