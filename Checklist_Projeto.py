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
import base64

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
    "Inicialização": ["Proposta Técnica", "Contrato", "Planilha de Orçamento Inicial", "Reunião de Alinhamento com equipe MV", "Reunião de Alinhamento com o Cliente", "Ata de Reunião", "Termo de Abertura (TAP)", "Declaração de Escopo (DEP)"],
    "Planejamento": ["Reunião de Kick Off", "Ata de Reunião", "Ata de Reunião de Alinhamento de Escopo com o Cliente", "Cronograma do Projeto", "Plano de Projeto", "Termo de Aceite de Entrega"],
    "Workshop de Processos": ["Análise de Gaps Críticos", "Business Blue Print", "Configuração do Sistema", "Apresentação da Solução", "Termo de Aceite de Entrega"],
    "Construção": ["Plano de Cutover", "Avaliação do Treinamento", "Progressão das tabelas", "Termo de Aceite de Entrega"],
    "Go Live": ["Carga de Dados Finais", "Escala de Apoio", "Metas de Simulação", "Testes Integrados", "Reunião Go/No Go", "Termo de Aceite de Entrega"],
    "Operação Assistida": ["Suporte In Loco aos usuários", " Reunião de Pré-Onboarding Sustentação", "Termo de Aceite de Entrega"],
    "Finalização": ["Reunião de Finalização", "Termo de Encerramento", "Registro de Lições Aprendidas MV LEARN - Sharepoint"]
}

MAPA_COLUNAS = {
    "Inicialização": "inicializacao", "Planejamento": "planejamento", 
    "Workshop de Processos": "workshop_de_processos", "Construção": "construcao",
    "Go Live": "go_live", "Operação Assistida": "operacao_assistida", "Finalização": "finalizacao"
}

# --- FUNÇÕES GRÁFICAS ---
def gerar_radar_chart(realizado_dict):
    categorias = list(realizado_dict.keys())
    valores_realizados = list(realizado_dict.values())
    N = len(categorias)
    angulos = [n / float(N) * 2 * np.pi for n in range(N)]
    angulos += angulos[:1]
    planejado = [100.0] * N + [100.0]
    realizado = valores_realizados + valores_realizados[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.plot(angulos, planejado, color='#1f77b4', linewidth=2, linestyle='--', label="Ideal (100%)")
    ax.fill(angulos, planejado, color='#1f77b4', alpha=0.05)
    ax.plot(angulos, realizado, color="#ffb30e", linewidth=3, label="Realizado (%)")
    ax.fill(angulos, realizado, color='#ffb30e', alpha=0.4)
    plt.xticks(angulos[:-1], categorias, color='grey', size=10)
    ax.set_ylim(0, 100)
    plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
    return fig

# --- PDF EXECUTIVO ---
class PDFExecutivo(FPDF):
    def header(self):
        self.set_fill_color(20, 50, 100)
        self.rect(0, 0, 210, 45, 'F')
        self.set_font('Arial', 'B', 20); self.set_text_color(255, 255, 255)
        self.cell(0, 20, "STATUS REPORT EXECUTIVO", ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, "HUB DE INTELIGÊNCIA OPERACIONAL | METODOLOGIA TRADICIONAL", ln=True, align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Página {self.page_no()} | Confidencial', align='C')

    def add_watermark(self):
        self.set_font("Arial", 'B', 50); self.set_text_color(240, 240, 240)
        with self.rotation(45, 105, 148): self.text(35, 190, "C O N F I D E N C I A L")

    def section_title(self, label):
        self.set_font("Arial", 'B', 12); self.set_fill_color(230, 230, 230); self.set_text_color(0, 0, 0)
        self.cell(0, 10, label, 0, 1, 'L', True); self.ln(4)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Project Hub", layout="wide")
st.title("🛡️ Gestão de Entregas e Conformidade do Projeto")
st.markdown("---")

c1, c2 = st.columns(2)
with c1:
    nome_proj = st.text_input("Nome do Projeto", placeholder="Ex: Hospital X")
with c2:
    gp_proj = st.text_input("Gerente de Projeto", placeholder="Nome do Responsável")

# --- PROCESSAMENTO DOS DADOS ---
perc_fases, detalhes_entrega = {}, {}
st.subheader("📋 Checklist do Projeto")
tabs = st.tabs(list(METODOLOGIA.keys()))

for i, fase in enumerate(METODOLOGIA.keys()):
    with tabs[i]:
        concluidos = 0
        detalhes_entrega[fase] = []
        c_check = st.columns(2)
        for idx, item in enumerate(METODOLOGIA[fase]):
            checked = c_check[idx % 2].checkbox(item, key=f"{fase}_{item}")
            status = "Concluído" if checked else "Pendente"
            detalhes_entrega[fase].append({"documento": item, "status": status})
            if checked: concluidos += 1
        perc = (concluidos / len(METODOLOGIA[fase])) * 100
        perc_fases[fase] = perc
        st.write(f"Maturidade da Fase: **{perc:.0f}%**")

# --- SPARKLINE COM MARCOS E BORDAS AMARELAS ---
st.markdown("---")
st.subheader("🛤️ Escala de Progressão Metodológica")

global_avg = sum(perc_fases.values()) / len(METODOLOGIA)
cols_spark = st.columns(len(METODOLOGIA))

for i, (fase, valor) in enumerate(perc_fases.items()):
    with cols_spark[i]:
        # Lógica de destaque: Se valor < 100 e > 0, tem pendência ativa na fase atual
        # Se valor == 0, ainda não iniciada (cinza)
        # Se valor == 100, concluída (azul liso)
        bg_color = "#143264" if valor > 0 else "#ddd"
        border_style = "3px solid #ffb30e" if 0 < valor < 100 else f"2px solid {bg_color}"
        label_color = "#143264" if valor > 0 else "#999"
        
        st.markdown(f"""
            <div style='text-align: center;'>
                <div style='
                    display: inline-block;
                    width: 25px; height: 25px;
                    border-radius: 50%;
                    background-color: {bg_color};
                    border: {border_style};
                '></div>
                <p style='font-size: 10px; font-weight: bold; color: {label_color}; margin-top: 5px;'>{fase}</p>
                <p style='font-size: 10px; color: #ffb30e; font-weight: bold; margin-top: -10px;'>{valor:.0f}%</p>
            </div>
        """, unsafe_allow_html=True)

# Barra de progresso horizontal (Sparkline Principal)
st.markdown("""<style> .stProgress > div > div > div > div { background-color: #143264; } </style>""", unsafe_allow_html=True)
st.progress(global_avg / 100)
st.markdown(f"<p style='text-align: right; font-weight: bold; color: #143264;'>Total Realizado: {global_avg:.1f}%</p>", unsafe_allow_html=True)

# --- GRÁFICO E AÇÕES ---
st.markdown("---")
col_graf, col_btn = st.columns([2, 1])

with col_graf:
    chart = gerar_radar_chart(perc_fases)
    st.pyplot(chart)
    chart.savefig("temp_radar.png", bbox_inches='tight')

with col_btn:
    st.subheader("⚙️ Ações do Hub")
    if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
        if nome_proj and gp_proj:
            try:
                # Normalização para o banco
                db_data = {k.lower().replace(" ", "_").replace("ç", "c").replace("ã", "a"): v for k, v in perc_fases.items()}
                novo = Projeto(nome_projeto=nome_proj, gerente_projeto=gp_proj, **db_data)
                session.add(novo); session.commit()
                st.success(f"Dados sincronizados às {datetime.now().strftime('%H:%M:%S')}!")
            except Exception as e:
                st.error("Erro ao salvar. Verifique se o arquivo .db está bloqueado ou desatualizado.")
        else: st.error("Preencha os dados do projeto.")

    if st.button("📄 GERAR RELATÓRIO EXECUTIVO PDF", use_container_width=True, type="primary"):
        pdf = PDFExecutivo()
        pdf.add_page(); pdf.add_watermark(); pdf.set_text_color(0, 0, 0)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"PROJETO: {nome_proj.upper()}", ln=True)
        pdf.cell(0, 8, f"GERENTE: {gp_proj}", ln=True)
        pdf.cell(0, 8, f"DATA DE EMISSÃO: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.cell(0, 8, f"PROGRESSÃO GLOBAL: {global_avg:.1f}%", ln=True); pdf.ln(5)
        
        pdf.section_title("MAPA DE MATURIDADE DA IMPLANTAÇÃO")
        pdf.image("temp_radar.png", x=55, y=pdf.get_y(), w=100)
        pdf.set_y(pdf.get_y() + 105)
        
        pdf.section_title("DETALHAMENTO DE ENTREGÁVEIS POR FASE")
        for fase, itens in detalhes_entrega.items():
            pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(245, 245, 245)
            pdf.cell(140, 8, f" Fase: {fase}", 1, 0, 'L', True)
            pdf.cell(50, 8, f"Status: {perc_fases[fase]:.0f}%", 1, 1, 'C', True)
            
            pdf.set_font("Arial", '', 9)
            for item in itens:
                pdf.set_text_color(34, 139, 34) if item["status"] == "Concluído" else pdf.set_text_color(200, 0, 0)
                pdf.cell(140, 7, f"   - {item['documento']}", 1)
                pdf.cell(50, 7, item["status"], 1, 1, 'C')
                pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        pdf.ln(5); pdf.section_title("ANÁLISE DE PENDÊNCIAS (IA INSIGHTS)")
        pendencias = [i["documento"] for f in detalhes_entrega.values() for i in f if i["status"] == "Pendente"]
        if pendencias:
            analise_ia = f"Alerta: O projeto possui {len(pendencias)} pendências. Priorizar fase: {[f for f,v in perc_fases.items() if v < 100][0]}."
        else:
            analise_ia = "Conformidade Total: O projeto está 100% aderente à metodologia."
        pdf.multi_cell(0, 8, analise_ia, border=1)
        
        pdf_output = bytes(pdf.output())
        st.download_button(label="📥 BAIXAR PDF", data=pdf_output, file_name=f"Report_{nome_proj}.pdf", mime="application/pdf", use_container_width=True)
