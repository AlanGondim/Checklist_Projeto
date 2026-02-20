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

# --- METODOLOGIA ---
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
    "Inicialização": "inicializacao",
    "Planejamento": "planejamento",
    "Workshop de Processos": "workshop_de_processos",
    "Construção": "construcao",
    "Go Live": "go_live",
    "Operação Assistida": "operacao_assistida",
    "Finalização": "finalizacao"
}

def gerar_radar_chart(realizado_dict):
    categorias = list(realizado_dict.keys())
    valores = list(realizado_dict.values())
    N = len(categorias)
    angulos = [n / float(N) * 2 * np.pi for n in range(N)]
    angulos += angulos[:1]
    
    realizado = valores + valores[:1]
    planejado = [100.0] * (N + 1)

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angulos, planejado, color='#1f77b4', linewidth=2, linestyle='--', label="Ideal (100%)")
    ax.fill(angulos, planejado, color='#1f77b4', alpha=0.05)
    ax.plot(angulos, realizado, color='#ff7f0e', linewidth=3, label="Realizado (%)")
    ax.fill(angulos, realizado, color='#ff7f0e', alpha=0.4)
    plt.xticks(angulos[:-1], categorias, color='grey', size=8)
    ax.set_ylim(0, 100)
    return fig

class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 45, 'F')
        self.set_font('Arial', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, "STATUS REPORT EXECUTIVO", ln=True, align='C')
        self.ln(25)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()} | Confidencial', align='C')
    def add_watermark(self):
        self.set_font("Arial", 'B', 50); self.set_text_color(240, 240, 240)
        with self.rotation(45, 105, 148): self.text(35, 190, "C O N F I D E N C I A L")
    def section_title(self, label):
        self.set_font("Arial", 'B', 12)
        self.set_fill_color(230, 230, 230); self.set_text_color(0, 0, 0)
        self.cell(0, 10, label, 0, 1, 'L', True); self.ln(4)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Project Hub", layout="wide")
st.title("🛡️ Gestão de Entregas e Conformidade")

c1, c2 = st.columns(2)
nome_proj = c1.text_input("Nome do Projeto")
gp_proj = c2.text_input("Gerente de Projeto")

perc_fases = {}
detalhes_entrega = {}
cols = st.columns(len(METODOLOGIA))

for i, fase in enumerate(METODOLOGIA.keys()):
    with cols[i]:
        st.markdown(f"**{fase}**")
        concluidos = 0
        detalhes_entrega[fase] = []
        for item in METODOLOGIA[fase]:
            checked = st.checkbox(item, key=f"chk_{fase}_{item}")
            detalhes_entrega[fase].append({"documento": item, "status": "Concluído" if checked else "Pendente"})
            if checked: concluidos += 1
        perc = (concluidos / len(METODOLOGIA[fase])) * 100
        perc_fases[fase] = perc
        st.caption(f"Progresso: {perc:.0f}%")

st.markdown("---")
col_graf, col_btn = st.columns([2, 1])

with col_graf:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    fig.savefig("temp_radar.png", bbox_inches='tight', dpi=100)

with col_btn:
    st.subheader("⚙️ Ações do Hub")
    
    # BOTÃO SALVAR
    if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
        if nome_proj and gp_proj:
            dados_salvamento = {"nome_projeto": nome_proj, "gerente_projeto": gp_proj}
            for fase_nome, valor in perc_fases.items():
                dados_salvamento[MAPA_COLUNAS[fase_nome]] = valor
            
            novo = Projeto(**dados_salvamento)
            session.add(novo)
            session.commit()
            st.success(f"Dados salvos com sucesso às {datetime.now().strftime('%H:%M:%S')}!")
        else:
            st.error("Preencha o Nome do Projeto e Gerente antes de salvar.")

    # BOTÃO PDF (Fora do bloco de salvar)
    if st.button("📄 GERAR RELATÓRIO EXECUTIVO PDF", use_container_width=True, type="primary"):
        if not nome_proj:
            st.error("Informe o nome do projeto para gerar o relatório.")
        else:
            pdf = PDFExecutivo()
            pdf.add_page()
            pdf.add_watermark()
            
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0,0,0)
            pdf.cell(0, 8, f"PROJETO: {nome_proj.upper()}", ln=True)
            pdf.cell(0, 8, f"GERENTE: {gp_proj}", ln=True)
            pdf.cell(0, 8, f"DATA: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
            pdf.ln(5)
            
            pdf.section_title("MAPA DE MATURIDADE DA IMPLANTAÇÃO")
            if os.path.exists("temp_radar.png"):
                pdf.image("temp_radar.png", x=55, w=100)
                pdf.ln(70) # Ajuste de espaço após imagem
            
            pdf.section_title("DETALHAMENTO DE ENTREGÁVEIS")
            for fase, itens in detalhes_entrega.items():
                pdf.set_font("Arial", 'B', 10)
                pdf.set_fill_color(245, 245, 245)
                pdf.cell(140, 8, f" Fase: {fase}", 1, 0, 'L', True)
                pdf.cell(50, 8, f"{perc_fases[fase]:.0f}%", 1, 1, 'C', True)
                
                for item in itens:
                    pdf.set_font("Arial", '', 9)
                    pdf.set_text_color(34, 139, 34) if item["status"] == "Concluído" else pdf.set_text_color(200, 0, 0)
                    pdf.cell(140, 7, f"   - {item['documento']}", 1)
                    pdf.cell(50, 7, item["status"], 1, 1, 'C')
                pdf.ln(2)
                pdf.set_text_color(0,0,0)

            path_pdf = "Relatorio_Premium.pdf"
            pdf.output(path_pdf)
            
            with open(path_pdf, "rb") as f:
                st.download_button(label="📥 CLIQUE PARA BAIXAR PDF", data=f, file_name=f"Report_{nome_proj}.pdf", mime="application/pdf", use_container_width=True)
