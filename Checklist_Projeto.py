import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fpdf import FPDF
from datetime import datetime
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

# Garante que as colunas existam
Base.metadata.create_all(engine)

# --- METODOLOGIA ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial", "Alinhamento time MV", "Ata de reunião", "Alinhamento Cliente", "TAP", "DEP"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião", "Cronograma", "Plano de Projeto"],
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
    
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angulos, [100.0]*(N+1), color='#143264', linewidth=1, linestyle='--')
    ax.plot(angulos, realizado, color='#ffb30e', linewidth=3, label="Realizado")
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.3)
    plt.xticks(angulos[:-1], categorias, size=7, fontweight='bold')
    return fig

class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 40, 'F')
        if os.path.exists("Logomarca MV Atualizada.png"):
            self.image("Logomarca MV Atualizada.png", x=10, y=8, w=22)
        self.set_font('Helvetica', 'B', 16); self.set_text_color(255, 255, 255)
        self.set_xy(35, 15)
        self.cell(140, 10, "METODOLOGIA - CHECKLIST DO PROJETO", ln=True, align='C')
        self.ln(20)

    def footer(self):
        # Rodapé com Protocolo de Auditoria e Timestamp
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        timestamp_audit = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.cell(0, 10, f"Protocolo de Auditoria: {timestamp_audit} | Documento Gerado via Hub de Inteligência | Pagina {self.page_no()}", 0, 0, 'C')
    
    def add_watermark(self):
        self.set_font("Helvetica", 'B', 50); self.set_text_color(248, 248, 248)
        with self.rotation(45, 105, 148):
            self.text(40, 160, "C O N F I D E N C I A L")

    def desenhar_sparkline_pdf(self, perc_fases, y_pos):
        x_start, largura_total = 25, 160
        passo = largura_total / (len(perc_fases) - 1)
        self.set_draw_color(200, 200, 200); self.set_line_width(0.8)
        self.line(x_start, y_pos + 5, x_start + largura_total, y_pos + 5)
        
        for i, (fase, valor) in enumerate(perc_fases.items()):
            x_circ = x_start + (i * passo)
            if valor >= 100:
                self.set_fill_color(20, 50, 100); self.set_draw_color(20, 50, 100)
            elif valor > 0:
                self.set_fill_color(20, 50, 100); self.set_draw_color(255, 179, 14); self.set_line_width(0.8)
            else:
                self.set_fill_color(230, 230, 230); self.set_draw_color(200, 200, 200)
                
            self.ellipse(x_circ - 3, y_pos + 2, 6, 6, 'FD')
            self.set_font("Helvetica", 'B', 6); self.set_text_color(20, 50, 100)
            self.text(x_circ - 8, y_pos + 12, fase[:15])

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Checklist do Projeto", layout="wide")
st.title("🏛️ Metodologia | Checklist de Projeto")

# Busca de Projeto no Hub
with st.sidebar:
    st.header("🔍 Buscar no Hub")
    projetos_salvos = [p.nome_projeto for p in session.query(Projeto.nome_projeto).distinct().all()]
    projeto_busca = st.selectbox("Carregar Projeto Existente", [""] + projetos_salvos)

# --- CAMPOS EXECUTIVOS ---
with st.container():
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Nome do Projeto", value=projeto_busca if projeto_busca else "")
    oportunidade = c2.text_input("Oportunidade (CRM)")
    gp_p = c3.text_input("Gerente de Projeto")

    c4, c5, c6 = st.columns(3)
    horas_cont = c4.number_input("Horas Contratadas", min_value=0.0, step=10.0 )
    tipo_p = c5.selectbox("Tipo", ["Implantação", "Migração" , "Revitalização", "Consultoria"])
    resp_verificacao = c6.text_input("Responsável pela Verificação")

    c7, c8, c9 = st.columns(3)
    d_inicio = c7.date_input("Data de Início", format="DD/MM/YYYY")
    d_termino = c8.date_input("Data de Término", format="DD/MM/YYYY")
    d_producao = c9.date_input("Entrada em Produção", format="DD/MM/YYYY")

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

# --- ESCALA DE PROGRESSÃO ---
st.markdown("---")
global_avg = sum(perc_fases.values()) / len(perc_fases)
st.write(f"### 🛤️ Evolução da Implantação: {global_avg:.1f}%")

cols_spark = st.columns(len(perc_fases))
for i, (fase, valor) in enumerate(perc_fases.items()):
    with cols_spark[i]:
        cor_circulo = "#143264" if valor > 0 else "#eeeeee"
        estilo_borda = "border: 3px solid #143264;" if valor >= 100 else ("border: 3px solid #ffb30e;" if valor > 0 else "border: 1px solid #cccccc;")
        st.markdown(f"""<div style='text-align: center;'><div style='display: inline-block; width: 25px; height: 25px; border-radius: 50%; background: {cor_circulo}; {estilo_borda}'></div><p style='font-size: 11px; font-weight: bold; color: #143264; margin-top: 5px;'>{fase}</p></div>""", unsafe_allow_html=True)

st.progress(global_avg / 100)

# --- HUB DE AÇÕES ---
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
        if nome_p:
            try:
                agora = datetime.now()
                data_hora_save = agora.strftime("%d/%m/%Y às %H:%M:%S")
                
                novo_projeto = Projeto(
                    nome_projeto=nome_p, gerente_projeto=gp_p, oportunidade=oportunidade,
                    horas_contratadas=horas_cont, tipo=tipo_p, responsavel_verificacao=resp_verificacao,
                    data_inicio=d_inicio.strftime("%d/%m/%Y"), 
                    data_termino=d_termino.strftime("%d/%m/%Y"), 
                    data_producao=d_producao.strftime("%d/%m/%Y"),
                    **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()}
                )
                session.add(novo_projeto)
                session.commit()
                st.success(f"✅ Snapshot de '{nome_p}' salvo com sucesso!")
                st.info(f"📅 **Data:** {data_formatada} | 🕒 **Hora:** {hora_formatada}")
                st.toast(f"Protocolado em {data_formatada} às {hora_formatada}", icon='🚀')
            except Exception as e:
                session.rollback()
                st.error(f"Erro ao salvar: {e}")
        else:
            st.warning("Nome do Projeto é obrigatório.")

    if st.button("📄 GERAR RELATÓRIO EXECUTIVO (IA)", use_container_width=True, type="primary"):
        pdf = PDFExecutivo()
        pdf.add_page(); pdf.add_watermark()
        
        # Grid Executiva dd/mm/aaaa
        pdf.set_font("Helvetica", 'B', 8); pdf.set_text_color(20, 50, 100); pdf.set_fill_color(245, 245, 245)
        pdf.cell(63, 7, f" PROJETO: {nome_p.upper()}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" OPORTUNIDADE: {oportunidade}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" GP: {gp_p}", 1, 1, 'L', True)
        pdf.cell(63, 7, f" INICIO: {d_inicio.strftime('%d/%m/%Y')}", 1, 0, 'L')
        pdf.cell(63, 7, f" TERMINO: {d_termino.strftime('%d/%m/%Y')}", 1, 0, 'L')
        pdf.cell(64, 7, f" PRODUCAO: {d_producao.strftime('%d/%m/%Y')}", 1, 1, 'L')
        
        pdf.ln(5); pdf.desenhar_sparkline_pdf(perc_fases, pdf.get_y()); pdf.set_y(pdf.get_y() + 20)
        pdf.image(img_buf, x=65, w=80); pdf.ln(80)
        
        # Detalhamento IA
        pdf.set_fill_color(255, 243, 205); pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(190, 8, " INTELIGENCIA DE ENTREGA: DIAGNOSTICO DE PENDENCIAS", 0, 1, 'L', True)
        pdf.set_font("Helvetica", '', 8); pdf.set_text_color(50, 50, 50)
        
        for fase, itens in detalhes_entrega.items():
            pend = [i["doc"] for i in itens if i["status"] == "Pendente"]
            if pend:
                pdf.set_font("Helvetica", 'B', 8); pdf.cell(190, 5, f"> Fase {fase}:", ln=True)
                pdf.set_font("Helvetica", '', 8); pdf.multi_cell(190, 4, f" Pendencias Criticas: {', '.join(pend[:5])}...")
                pdf.ln(1)
        
        st.download_button("📥 BAIXAR RELATORIO PDF", data=bytes(pdf.output()), file_name=f"Checklist_Projeto_{nome_p}.pdf", mime="application/pdf", use_container_width=True)











