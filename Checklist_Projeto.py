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

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
Base = declarative_base()
engine = create_engine('sqlite:///hub_inteligencia.db')
Session = sessionmaker(bind=engine)
session = Session()

class Projeto(Base):
    __tablename__ = 'monitoramento_projetos'
    id = Column(Integer, primary_key=True)
    nome_projeto = Column(String)
    gerente_projeto = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    inicializacao = Column(Float)
    planejamento = Column(Float)
    workshop_de_processos = Column(Float)
    construcao = Column(Float)
    go_live = Column(Float)
    operacao_assistida = Column(Float)
    finalizacao = Column(Float)

Base.metadata.create_all(engine)

# --- METODOLOGIA BASEADA NO FR.IC.48 ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato", "Orçamento Inicial", "Alinhamento MV", "Alinhamento Cliente", "TAP", "DEP"],
    "Planejamento": ["Kick Off", "Ata de Alinhamento", "Cronograma", "Plano de Projeto", "Checklist FR.IC.48"],
    "Workshop de Processos": ["Gaps Críticos", "Business Blue Print", "Configuração", "Apresentação da Solução"],
    "Construção": ["Plano de Cutover", "Avaliação do Treinamento", "Progressão das Tabelas", "Carga Precursora"],
    "Go Live": ["Carga de Dados Finais", "Escala de Apoio", "Metas de Simulação", "Testes Integrados", "Reunião Go/No Go"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding", "Identificação de Gaps"],
    "Finalização": ["Termo de Encerramento", "Lições Aprendidas"]
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
    planejado = [100.0] * (N + 1)
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angulos, planejado, color='#143264', linewidth=1, linestyle='--', label="Ideal")
    ax.plot(angulos, realizado, color='#ffb30e', linewidth=3, label="Realizado")
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.3)
    plt.xticks(angulos[:-1], categorias, size=8)
    return fig

class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 45, 'F')
        self.set_font('Helvetica', 'B', 18); self.set_text_color(255, 255, 255)
        self.cell(190, 20, "STATUS REPORT EXECUTIVO - FR.IC.48", ln=True, align='C')
        self.ln(25)
    def add_watermark(self):
        self.set_font("Helvetica", 'B', 50); self.set_text_color(245, 245, 245)
        with self.rotation(45, 105, 148): self.text(35, 190, "C O N F I D E N C I A L")

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Hub FR.IC.48", layout="wide")
st.title("🛡️ Gestão de Entregas e Conformidade")

c1, c2 = st.columns(2)
nome_proj = c1.text_input("Nome do Projeto", placeholder="Ex: Hospital X")
gp_proj = c2.text_input("Gerente de Projeto")

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

# --- SPARKLINE COM PERCENTUAIS ---
st.markdown("---")
global_avg = sum(perc_fases.values()) / len(perc_fases)
st.write(f"### 🛤️ Progresso Global Realizado: {global_avg:.1f}%")

cols_spark = st.columns(len(perc_fases))
for i, (fase, valor) in enumerate(perc_fases.items()):
    with cols_spark[i]:
        cor_marco = "#143264" if valor > 0 else "#ddd"
        borda = "border: 2px solid #ffb30e;" if 0 < valor < 100 else ""
        st.markdown(f"""
            <div style='text-align: center;'>
                <div style='display: inline-block; width: 22px; height: 22px; border-radius: 50%; background: {cor_marco}; {borda}'></div>
                <p style='font-size: 10px; font-weight: bold; color: #143264; margin-bottom: 0;'>{fase}</p>
                <p style='font-size: 11px; color: #ffb30e; font-weight: bold;'>{valor:.0f}%</p>
            </div>
        """, unsafe_allow_html=True)

st.markdown("""<style> .stProgress > div > div > div > div { background-color: #143264; } </style>""", unsafe_allow_html=True)
st.progress(global_avg / 100)

# --- PROCESSAMENTO ---
col_graf, col_btn = st.columns([2, 1])

with col_graf:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    img_buf.seek(0)

with col_btn:
    st.subheader("⚙️ Hub Governança")
    
    if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
        if nome_proj and gp_proj:
            dados_db = {"nome_projeto": nome_proj, "gerente_projeto": gp_proj}
            for f, v in perc_fases.items(): dados_db[MAPA_COLUNAS[f]] = v
            try:
                session.add(Projeto(**dados_db))
                session.commit()
                st.toast(f"✅ Projeto {nome_proj} salvo com sucesso!", icon="💾")
                st.success(f"Sincronizado às {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                st.error("Erro no DB. Delete o arquivo 'hub_inteligencia.db' da sua pasta e tente novamente.")

    if st.button("📄 GERAR RELATÓRIO COM DIAGNÓSTICO", use_container_width=True, type="primary"):
        if nome_proj:
            st.toast("🤖 Analisando pendências e gerando visualização...", icon="⏳")
            pdf = PDFExecutivo()
            pdf.add_page(); pdf.add_watermark(); pdf.set_text_color(0,0,0)
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(190, 8, f"PROJETO: {nome_proj.upper()}", ln=True)
            pdf.cell(190, 8, f"GP: {gp_proj}", ln=True); pdf.ln(10)
            
            # Radar Chart em Memória
            pdf.image(img_buf, x=60, w=90); pdf.ln(95)
            
            # Diagnóstico IA
            pdf.set_fill_color(255, 243, 205); pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(190, 10, "DIAGNÓSTICO IA: PENDÊNCIAS E PRÓXIMOS PASSOS", 0, 1, 'L', True); pdf.ln(2)
            
            for fase, itens in detalhes_entrega.items():
                pendentes = [i["doc"] for i in itens if i["status"] == "Pendente"]
                if pendentes:
                    pdf.set_font("Helvetica", 'I', 10); pdf.set_text_color(180, 0, 0)
                    # Largura de 190mm para evitar erro de espaço horizontal
                    msg = f"Fase {fase}: Resolver {len(pendentes)} pendência(s): {', '.join(pendentes[:3])}..."
                    pdf.multi_cell(190, 6, msg, border='B')
            
            pdf_data = pdf.output()
            st.toast("✅ Relatório pronto!", icon="📄")
            
            # Visualização Iframe base64
            base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>'
            st.markdown("### 👁️ Visualização do Relatório")
            st.markdown(pdf_display, unsafe_allow_html=True)
            
            st.download_button("📥 BAIXAR RELATÓRIO PDF", data=pdf_data, file_name=f"Status_{nome_proj}.pdf", mime="application/pdf", use_container_width=True)
        else: st.warning("Informe o nome do projeto.")
