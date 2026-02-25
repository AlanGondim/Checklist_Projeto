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
import os

# --- DATABASE SETUP (SUPABASE OU LOCAL) ---
Base = declarative_base()
# Substitua pela sua Connection String do Supabase se desejar nuvem total
DB_URL = 'sqlite:///hub_inteligencia_executivo.db' 
engine = create_engine(DB_URL)
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
    parecer_gerencia = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    # Métricas das Fases
    inicializacao = Column(Float); planejamento = Column(Float)
    workshop_de_processos = Column(Float); construcao = Column(Float)
    go_live = Column(Float); operacao_assistida = Column(Float)
    finalizacao = Column(Float)

Base.metadata.create_all(engine)

# --- METODOLOGIA ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial", "Alinhamento time MV", "Ata de reunião", "TAP", "DEP"],
    "Planejamento": ["Evidência Kick Off", "Ata de Reunião", "Cronograma", "Plano de Projeto"],
    "Workshop de Processos": ["Análise de Gaps Críticos", "Business Blue Print", "Configuração", "Apresentação Solução", "Aceite"],
    "Construção": ["Plano de Cutover", "Avaliação Treinamento", "Carga Precursora", "Homologação Integração"],
    "Go Live": ["Carga Final Dados", "Escala Apoio", "Metas Simulação", "Testes Integrados", "Reunição Go/No Go"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding", "Identificação Gaps", "Aceite Entrega"],
    "Finalização": ["Reunião Finalização", "TEP", "Lições Aprendidas"]
}

MAPA_COLUNAS = {
    "Inicialização": "inicializacao", "Planejamento": "planejamento", 
    "Workshop de Processos": "workshop_de_processos", "Construção": "construcao",
    "Go Live": "go_live", "Operação Assistida": "operacao_assistida", "Finalização": "finalizacao"
}

# --- FUNÇÕES GRÁFICAS ---
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
    plt.xticks(angulos[:-1], categorias, size=8)
    return fig

class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 40, 'F')
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

    def sparkline_pdf(self, perc_fases, y_pos):
        x_start, largura_total = 25, 160
        passo = largura_total / (len(perc_fases) - 1)
        self.set_draw_color(200, 200, 200); self.set_line_width(0.8)
        self.line(x_start, y_pos + 5, x_start + largura_total, y_pos + 5)
        
        for i, (fase, valor) in enumerate(perc_fases.items()):
            x_circ = x_start + (i * passo)
            if valor >= 100:
                self.set_fill_color(20, 50, 100); self.set_draw_color(20, 50, 100); self.set_line_width(0.1)
            elif valor > 0:
                self.set_fill_color(20, 50, 100); self.set_draw_color(255, 179, 14); self.set_line_width(0.8)
            else:
                self.set_fill_color(230, 230, 230); self.set_draw_color(200, 200, 200); self.set_line_width(0.2)
            self.ellipse(x_circ - 3, y_pos + 2, 6, 6, 'FD')
            self.set_font("Helvetica", 'B', 6); self.set_text_color(20, 50, 100)
            self.text(x_circ - 8, y_pos + 12, fase[:15])

# --- INTERFACE ---
st.set_page_config(page_title="IA Executive Hub Cloud", layout="wide")
st.title("🏛️ Hub de Inteligência Executiva (Cloud)")

with st.sidebar:
    st.header("🔍 Consultar Projetos")
    projetos_nuvem = [p.nome_projeto for p in session.query(Projeto.nome_projeto).distinct().all()]
    proj_query = st.selectbox("Carregar histórico:", [""] + projetos_nuvem)

dados_nuvem = None
if proj_query:
    dados_nuvem = session.query(Projeto).filter_by(nome_projeto=proj_query).order_by(Projeto.timestamp.desc()).first()

with st.container():
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Nome do Projeto", value=dados_nuvem.nome_projeto if dados_nuvem else "")
    oportunidade = c2.text_input("CRM / Oportunidade", value=dados_nuvem.oportunidade if dados_nuvem else "")
    gp_p = c3.text_input("Gerente do Projeto", value=dados_nuvem.gerente_projeto if dados_nuvem else "")

    c4, c5, c6 = st.columns(3)
    # AJUSTE: step=10.0 para aumentar de 10 em 10
    horas = c4.number_input("Horas Contratadas", value=dados_nuvem.horas_contratadas if dados_nuvem else 0.0, step=10.0)
    tipo = c5.selectbox("Tipo", ["Implantação", "Revitalização", "Upgrade"], index=0)
    resp = c6.text_input("Responsável Verificação", value=dados_nuvem.responsavel_verificacao if dados_nuvem else "")

    c7, c8, c9 = st.columns(3)
    d_ini = c7.date_input("Início", format="DD/MM/YYYY")
    d_ter = c8.date_input("Término", format="DD/MM/YYYY")
    d_pro = c9.date_input("Produção", format="DD/MM/YYYY")

st.write("### 📋 Checklist Metodológico")
tabs = st.tabs(list(METODOLOGIA.keys()))
perc_fases, detalhes_entrega = {}, {}

for i, (fase, itens) in enumerate(METODOLOGIA.items()):
    with tabs[i]:
        concluidos = 0
        detalhes_entrega[fase] = []
        cols_ui = st.columns(2)
        for idx, item in enumerate(itens):
            chk_ui = cols_ui[idx % 2].checkbox(item, key=f"v_{fase}_{item}")
            detalhes_entrega[fase].append({"doc": item, "status": "Concluído" if chk_ui else "Pendente"})
            if chk_ui: concluidos += 1
        perc_fases[fase] = (concluidos / len(itens)) * 100

st.subheader("💡 Parecer da Gerência e Plano de Ação")
parecer_ui = st.text_area("Descreva o diagnóstico IA e os próximos passos:", 
                           value=dados_nuvem.parecer_gerencia if dados_nuvem else "", height=100)

# ESCALA VISUAL (MARCOS)
st.markdown("---")
global_avg = sum(perc_fases.values()) / len(perc_fases)
st.write(f"### 🛤️ Evolução da Implantação: {global_avg:.1f}%")

cols_spark = st.columns(len(perc_fases))
for i, (fase, valor) in enumerate(perc_fases.items()):
    with cols_spark[i]:
        bg = "#143264" if valor > 0 else "#eeeeee"
        if valor >= 100: border = "border: 3px solid #143264;"
        elif valor > 0: border = "border: 3px solid #ffb30e;"
        else: border = "border: 1px solid #cccccc;"
        
        st.markdown(f"""<div style='text-align: center;'><div style='display: inline-block; width: 22px; height: 22px; border-radius: 50%; background: {bg}; {border}'></div><p style='font-size: 10px; font-weight: bold;'>{fase}<br>{valor:.0f}%</p></div>""", unsafe_allow_html=True)

# AÇÕES
st.divider()
c_radar, c_btns = st.columns([1.5, 1])

with c_radar:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    buf_img = io.BytesIO()
    fig.savefig(buf_img, format='png', bbox_inches='tight')
    buf_img.seek(0)

with c_btns:
    if st.button("💾 SALVAR E SINCRONIZAR NA NUVEM", use_container_width=True):
        novo_p = Projeto(
            nome_projeto=nome_p, gerente_projeto=gp_p, oportunidade=oportunidade,
            horas_contratadas=horas, tipo=tipo, responsavel_verificacao=resp,
            parecer_gerencia=parecer_ui,
            data_inicio=d_ini.strftime("%d/%m/%Y"), data_termino=d_ter.strftime("%d/%m/%Y"), 
            data_producao=d_pro.strftime("%d/%m/%Y"),
            **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()}
        )
        session.add(novo_p); session.commit()
        st.success("✅ Snapshot sincronizado com a nuvem!")

    if st.button("📄 GERAR RELATÓRIO ONE-PAGE (IA)", type="primary", use_container_width=True):
        pdf = PDFExecutivo()
        pdf.add_page(); pdf.add_watermark()
        
        pdf.set_font("Helvetica", 'B', 8); pdf.set_text_color(20, 50, 100); pdf.set_fill_color(245, 245, 245)
        pdf.cell(63, 7, f" PROJETO: {nome_p.upper()}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" CRM: {oportunidade}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" GP: {gp_p}", 1, 1, 'L', True)
        
        pdf.cell(63, 7, f" HORAS: {horas}", 1, 0, 'L')
        pdf.cell(63, 7, f" TIPO: {tipo}", 1, 0, 'L')
        pdf.cell(64, 7, f" RESPONSAVEL: {resp}", 1, 1, 'L')

        pdf.cell(63, 7, f" INICIO: {d_ini.strftime('%d/%m/%Y')}", 1, 0, 'L', True)
        pdf.cell(63, 7, f" TERMINO: {d_ter.strftime('%d/%m/%Y')}", 1, 0, 'L', True)
        pdf.cell(64, 7, f" PRODUCAO: {d_pro.strftime('%d/%m/%Y')}", 1, 1, 'L', True)
        
        pdf.ln(5); pdf.sparkline_pdf(perc_fases, pdf.get_y()); pdf.set_y(pdf.get_y() + 20)
        
        pdf.image(buf_img, x=65, w=80); pdf.ln(80)
        
        pdf.set_fill_color(255, 243, 205); pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(190, 8, " PARECER DA GERÊNCIA E DIAGNÓSTICO IA", 0, 1, 'L', True)
        pdf.set_font("Helvetica", 'I', 8); pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(190, 5, f"PARECER: {parecer_ui if parecer_ui else 'Sem comentários.'}")
        
        pdf.ln(2); pdf.set_font("Helvetica", 'B', 8)
        for f, itens in detalhes_entrega.items():
            pend = [i["doc"] for i in itens if i["status"] == "Pendente"]
            if pend:
                pdf.multi_cell(190, 4, f"> {f}: Pendente {', '.join(pend[:3])}...")
        
        st.download_button("📥 BAIXAR RELATÓRIO PDF", data=bytes(pdf.output()), file_name=f"Report_{nome_p}.pdf")
