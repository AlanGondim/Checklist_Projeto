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

# --- METODOLOGIA TRADICIONAL ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato", "Planilha de Orçamento Inicial", "Alinhamento MV", "Alinhamento Cliente", "Termo de Abertura (TAP)", "Declaração de Escopo (DEP)"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião de Alinhamento", "Cronograma do Projeto", "Plano de Projeto"],
    "Workshop de Processos": ["Gaps Críticos", "Business Blue Print", "Configuração", "Apresentação da Solução"],
    "Construção": ["Plano de Cutover", "Avaliação do Treinamento", "Progressão das tabelas"],
    "Go Live": ["Carga de Dados Finais", "Escala de Apoio", "Metas de Simulação", "Testes Integrados", "Reunião Go/No Go"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding Sustentação"],
    "Finalização": ["Termo de Encerramento", "Lições Aprendidas"]
}

# --- GRÁFICO RADAR (PLANEJADO VS REALIZADO) ---
def gerar_radar_chart(realizado_dict):
    categorias = list(realizado_dict.keys())
    valores_realizados = list(realizado_dict.values())
    N = len(categorias)
    
    angulos = [n / float(N) * 2 * np.pi for n in range(N)]
    angulos += angulos[:1]
    
    planejado = [100.0] * N
    planejado += planejado[:1]
    realizado = valores_realizados + valores_realizados[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.plot(angulos, planejado, color='#1f77b4', linewidth=2, linestyle='--', label="Ideal (100%)")
    ax.fill(angulos, planejado, color='#1f77b4', alpha=0.05)
    ax.plot(angulos, realizado, color="#ffb30e", linewidth=3, label="Realizado (%)")
    ax.fill(angulos, realizado, color='#ff7f0e', alpha=0.4)

    plt.xticks(angulos[:-1], categorias, color='grey', size=10)
    ax.set_ylim(0, 100)
    plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
    return fig

# --- GERAÇÃO DE PDF EXECUTIVO PREMIUM ---
class PDFExecutivo(FPDF):
    def header(self):
        # Header azul executivo
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 45, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, "STATUS REPORT EXECUTIVO", ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, "HUB DE INTELIGÊNCIA OPERACIONAL | METODOLOGIA TRADICIONAL", ln=True, align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Página {self.page_no()} | Confidencial', align='C')

    def add_watermark(self):
        self.set_font("Arial", 'B', 50)
        self.set_text_color(240, 240, 240)
        with self.rotation(45, 105, 148):
            self.text(35, 190, "C O N F I D E N C I A L")

    def section_title(self, label):
        self.set_font("Arial", 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, label, 0, 1, 'L', True)
        self.ln(4)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Project Hub", layout="wide")
st.title("🛡️ Gestão de Entregas e Conformidade do Projeto")
st.markdown("---")

c1, c2 = st.columns(2)
with c1:
    nome_proj = st.text_input("Nome do Projeto", placeholder="Ex: Implantação Hospital X")
with c2:
    gp_proj = st.text_input("Gerente de Projeto", placeholder="Nome do Responsável")

st.subheader("📋 Checklist do Projeto")
perc_fases = {}
detalhes_entrega = {} # Armazena status individual para o PDF
cols = st.columns(len(METODOLOGIA))

for i, fase in enumerate(METODOLOGIA.keys()):
    with cols[i]:
        st.markdown(f"**{fase}**")
        concluidos = 0
        detalhes_entrega[fase] = []
        for item in METODOLOGIA[fase]:
            checked = st.checkbox(item, key=f"{fase}_{item}")
            status = "Concluído" if checked else "Pendente"
            detalhes_entrega[fase].append({"documento": item, "status": status})
            if checked:
                concluidos += 1
        perc = (concluidos / len(METODOLOGIA[fase])) * 100
        perc_fases[fase] = perc
        st.caption(f"Progresso: {perc:.0f}%")

st.markdown("---")
col_graf, col_btn = st.columns([2, 1])

with col_graf:
    chart = gerar_radar_chart(perc_fases)
    st.pyplot(chart)
    # Salvar o gráfico temporariamente para o PDF
    chart.savefig("temp_radar.png", bbox_inches='tight')

with col_btn:
    st.subheader("⚙️ Ações do Hub")
    
    if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
        if nome_proj and gp_proj:
            novo = Projeto(
                nome_projeto=nome_proj, gerente_projeto=gp_proj,
                **{k.lower().replace(" ", "_").replace("ç", "c").replace("ã", "a"): v for k, v in perc_fases.items()}
            )
            session.add(novo)
            session.commit()
            agora = datetime.now().strftime("%H:%M:%S")
            st.success(f"Dados sincronizados às {agora}!")
        else:
            st.error("Preencha os dados do projeto.")

    if st.button("📄 GERAR RELATÓRIO EXECUTIVO PDF", use_container_width=True, type="primary"):
        pdf = PDFExecutivo()
        pdf.add_page()
        pdf.add_watermark()
        pdf.set_text_color(0, 0, 0)
        
        # 1. Informações Básicas
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"PROJETO: {nome_proj.upper()}", ln=True)
        pdf.cell(0, 8, f"GERENTE: {gp_proj}", ln=True)
        pdf.cell(0, 8, f"DATA DE EMISSÃO: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.ln(5)
        
        # 2. Resumo de Performance (Radar Chart)
        pdf.section_title("MAPA DE MATURIDADE DA IMPLANTAÇÃO")
        pdf.image("temp_radar.png", x=55, y=pdf.get_y(), w=100)
        pdf.set_y(pdf.get_y() + 105)
        
        # 3. Detalhamento de Entregáveis e Pendências
        pdf.section_title("DETALHAMENTO DE ENTREGÁVEIS POR FASE")
        
        for fase, itens in detalhes_entrega.items():
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(140, 8, f" Fase: {fase}", 1, 0, 'L', True)
            pdf.cell(50, 8, f"Status: {perc_fases[fase]:.0f}%", 1, 1, 'C', True)
            
            pdf.set_font("Arial", '', 9)
            for item in itens:
                # Cor dinâmica: Verde para concluído, Vermelho para pendente
                if item["status"] == "Concluído":
                    pdf.set_text_color(34, 139, 34)
                else:
                    pdf.set_text_color(200, 0, 0)
                
                pdf.cell(140, 7, f"   - {item['documento']}", 1)
                pdf.cell(50, 7, item["status"], 1, 1, 'C')
                pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # 4. Análise de IA (Insight Automático)
        pdf.ln(5)
        pdf.section_title("ANÁLISE DE PENDÊNCIAS (INSIGHTS)")
        pdf.set_font("Arial", 'I', 10)
        
        pendencias = [i["documento"] for f in detalhes_entrega.values() for i in f if i["status"] == "Pendente"]
        if pendencias:
            analise_ia = f"Alerta do Sistema: O projeto apresenta {len(pendencias)} pendências documentais. " \
                         f"Recomenda-se priorizar a fase de {[f for f,v in perc_fases.items() if v < 100][0]} " \
                         f"para evitar atrasos no Go Live."
        else:
            analise_ia = "Análise Concluída: O projeto encontra-se em 100% de conformidade metodológica."
            
        pdf.multi_cell(0, 8, analise_ia, border=1)
        
        path_pdf = "Relatorio_Premium.pdf"
        pdf.output(path_pdf)
        
        with open(path_pdf, "rb") as f:
            st.download_button(label="📥 BAIXAR PDF", data=f, 
                               file_name=f"Report_{nome_proj}.pdf", use_container_width=True)

