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
    # Colunas nomeadas de forma explícita para evitar erros de mapeamento
    inicializacao = Column(Float)
    planejamento = Column(Float)
    workshop_de_processos = Column(Float)
    construcao = Column(Float)
    go_live = Column(Float)
    operacao_assistida = Column(Float)
    finalizacao = Column(Float)

Base.metadata.create_all(engine)

# --- METODOLOGIA DE IMPLANTACAO ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato", "Planilha de Orçamento Inicial", "Alinhamento MV", "Alinhamento Cliente", "Termo de Abertura (TAP)", "Declaração de Escopo (DEP)"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião de Alinhamento", "Cronograma do Projeto", "Plano de Projeto"],
    "Workshop de Processos": ["Gaps Críticos", "Business Blue Print", "Configuração", "Apresentação da Solução"],
    "Construção": ["Plano de Cutover", "Avaliação do Treinamento", "Progressão das tabelas"],
    "Go Live": ["Carga de Dados Finais", "Escala de Apoio", "Metas de Simulação", "Testes Integrados", "Reunião Go/No Go"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding Sustentação"],
    "Finalização": ["Termo de Encerramento", "Lições Aprendidas"]
}

# Mapeamento para garantir que o SQLAlchemy encontre as colunas certas
MAPA_COLUNAS = {
    "Inicialização": "inicializacao",
    "Planejamento": "planejamento",
    "Workshop de Processos": "workshop_de_processos",
    "Construção": "construcao",
    "Go Live": "go_live",
    "Operação Assistida": "operacao_assistida",
    "Finalização": "finalizacao"
}

# --- FUNÇÕES DE APOIO (RADAR E PDF MANTIDOS) ---
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
    ax.plot(angulos, realizado, color='#ff7f0e', linewidth=3, label="Realizado (%)")
    ax.fill(angulos, realizado, color='#ff7f0e', alpha=0.4)
    plt.xticks(angulos[:-1], categorias, color='grey', size=10)
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

# --- INTERFACE ---
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
            checked = st.checkbox(item, key=f"{fase}_{item}")
            detalhes_entrega[fase].append({"documento": item, "status": "Concluído" if checked else "Pendente"})
            if checked: concluidos += 1
        perc = (concluidos / len(METODOLOGIA[fase])) * 100
        perc_fases[fase] = perc
        st.caption(f"Progresso: {perc:.0f}%")

if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
    if nome_proj and gp_proj:
        # Criando o objeto de forma segura mapeando fase -> coluna
        dados_salvamento = {
            "nome_projeto": nome_proj,
            "gerente_projeto": gp_proj
        }
        for fase_nome, valor in perc_fases.items():
            coluna_db = MAPA_COLUNAS[fase_nome]
            dados_salvamento[coluna_db] = valor
        
        novo = Projeto(**dados_salvamento)
        session.add(novo)
        session.commit()
        st.success(f"Dados sincronizados às {datetime.now().strftime('%H:%M:%S')}!")
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
            analise_ia = "Análise Concluída: O projeto encontra-se em 100% de conformidade com a metodologia de implantação MV."
            
        pdf.multi_cell(0, 8, analise_ia, border=1)
        
        path_pdf = "Relatorio_Premium.pdf"
        pdf.output(path_pdf)
        
        with open(path_pdf, "rb") as f:
            st.download_button(label="📥 BAIXAR RELATÓRIO PDF", data=f, 
                               file_name=f"Report_{nome_proj}.pdf", use_container_width=True)



