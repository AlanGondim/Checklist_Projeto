import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fpdf import FPDF
from datetime import datetime
import os

# --- DATABASE SETUP ---
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

# --- METODOLOGIA DE IMPLANTAÇÃO (FR.IC.48) ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato", "Planilha de Orçamento Inicial", "Alinhamento MV", "Alinhamento Cliente", "Termo de Abertura (TAP)", "Declaração de Escopo (DEP)"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião de Alinhamento", "Cronograma do Projeto", "Plano de Projeto"],
    "Workshop de Processos": ["Gaps Críticos", "Business Blue Print", "Configuração", "Apresentação da Solução"],
    "Construção": ["Plano de Cutover", "Avaliação do Treinamento", "Progressão das tabelas"],
    "Go Live": ["Carga de Dados Finais", "Escala de Apoio", "Metas de Simulação", "Testes Integrados", "Reunião Go/No Go"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding Sustentação"],
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
    ax.plot(angulos, planejado, color='#1f77b4', linewidth=2, linestyle='--', label="Ideal")
    ax.plot(angulos, realizado, color='#ff7f0e', linewidth=3, label="Realizado")
    ax.fill(angulos, realizado, color='#ff7f0e', alpha=0.3)
    plt.xticks(angulos[:-1], categorias, size=8)
    return fig

class PDFAnalitico(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 45, 'F')
        self.set_font('Arial', 'B', 18); self.set_text_color(255, 255, 255)
        self.cell(0, 20, "AUDITORIA DE ENTREGAS - FR.IC.48", ln=True, align='C')
        self.ln(25)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Página {self.page_no()} | Confidencial', align='C')
    def section_title(self, label, fill_color=(230, 230, 230)):
        self.set_font("Arial", 'B', 11); self.set_fill_color(*fill_color); self.set_text_color(0, 0, 0)
        self.cell(0, 10, label, 0, 1, 'L', True); self.ln(2)

# --- INTERFACE ---
st.set_page_config(page_title="Hub FR.IC.48", layout="wide")
st.title("🛡️ Auditoria Metodológica de Projetos")

c1, c2 = st.columns(2)
nome_proj = c1.text_input("Nome do Projeto/Cliente")
gp_proj = c2.text_input("Gerente de Projeto")

perc_fases, detalhes_entrega = {}, {}
cols = st.columns(len(METODOLOGIA))

for i, fase in enumerate(METODOLOGIA.keys()):
    with cols[i]:
        st.markdown(f"**{fase}**")
        concluidos = 0
        detalhes_entrega[fase] = []
        for item in METODOLOGIA[fase]:
            checked = st.checkbox(item, key=f"chk_{fase}_{item}")
            detalhes_entrega[fase].append({"doc": item, "status": "Concluído" if checked else "Pendente"})
            if checked: concluidos += 1
        perc_fases[fase] = (concluidos / len(METODOLOGIA[fase])) * 100
        st.caption(f"Atingimento: {perc_fases[fase]:.0f}%")

st.markdown("---")
col_graf, col_btn = st.columns([2, 1])

with col_graf:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    fig.savefig("radar.png", bbox_inches='tight')

with col_btn:
    st.subheader("⚙️ Ações")
    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        if nome_proj and gp_proj:
            dados = {"nome_projeto": nome_proj, "gerente_projeto": gp_proj}
            for f, v in perc_fases.items(): dados[MAPA_COLUNAS[f]] = v
            session.add(Projeto(**dados)); session.commit()
            st.success(f"Dados rastreados: {datetime.now().strftime('%H:%M:%S')}")

    if st.button("📄 GERAR RELATÓRIO ANALÍTICO", use_container_width=True, type="primary"):
        pdf = PDFAnalitico()
        pdf.add_page(); pdf.set_text_color(0,0,0)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"PROJETO: {nome_proj.upper()}", ln=True)
        pdf.cell(0, 8, f"RESPONSÁVEL: {gp_proj}", ln=True)
        pdf.ln(5)
        
        pdf.image("radar.png", x=60, w=90); pdf.ln(95)

        # ANÁLISE DE IA E PENDÊNCIAS
        pdf.section_title("DIAGNÓSTICO DE IA: PRÓXIMOS PASSOS E PENDÊNCIAS", (255, 243, 205))
        pdf.set_font("Arial", '', 10)
        
        for fase, itens in detalhes_entrega.items():
            pendentes = [i["doc"] for i in itens if i["status"] == "Pendente"]
            total = len(itens)
            concluidos = total - len(pendentes)
            
            if pendentes:
                analise_ia = f"Fase {fase}: {concluidos}/{total} entregues. PENDENTE: {len(pendentes)} item(s). " \
                             f"Ação Necessária: Resolver {', '.join(pendentes)} para garantir a transição de fase sem riscos operacionais."
                pdf.set_text_color(150, 0, 0)
                pdf.multi_cell(0, 6, analise_ia, border='B')
                pdf.ln(1)
            else:
                pdf.set_text_color(0, 100, 0)
                pdf.cell(0, 6, f"Fase {fase}: 100% Concluída. Liberada para próxima etapa.", ln=True, border='B')
                pdf.ln(1)
        
        pdf.set_text_color(0,0,0)
        pdf.ln(5)
        pdf.section_title("DETALHAMENTO TÉCNICO (FR.IC.48)")
        for fase, itens in detalhes_entrega.items():
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 7, f" {fase}", 1, 1, 'L', True)
            pdf.set_font("Arial", '', 8)
            for i in itens:
                pdf.set_text_color(34, 139, 34) if i["status"] == "Concluído" else pdf.set_text_color(200, 0, 0)
                pdf.cell(150, 6, f"  - {i['doc']}", 1)
                pdf.cell(40, 6, i["status"], 1, 1, 'C')
            pdf.ln(1)

        path_pdf = "Analise_Metodologica.pdf"
        pdf.output(path_pdf)
        with open(path_pdf, "rb") as f:
            st.download_button("📥 BAIXAR RELATÓRIO COM DIAGNÓSTICO", f, file_name=f"Analise_{nome_proj}.pdf", use_container_width=True)
