import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fpdf import FPDF
from datetime import datetime
import io
import base64
import os

# --- DATABASE SETUP & AUTO-FIX ---
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia.db'
engine = create_engine(DB_NAME)
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

# Correção automática de esquema do Banco de Dados
if os.path.exists('hub_inteligencia.db'):
    try:
        inspector = inspect(engine)
        if 'monitoramento_projetos' in inspector.get_table_names():
            colunas = [c['name'] for c in inspector.get_columns('monitoramento_projetos')]
            if 'workshop_de_processos' not in colunas:
                session.close()
                engine.dispose()
                os.remove('hub_inteligencia.db')
    except Exception:
        pass

Base.metadata.create_all(engine)

# --- METODOLOGIA FR.IC.48 ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial do Projeto", "Alinhamento do projeto com o time MV", "Ata de reunião" , "Alinhamento do projeto com o Cliente", "TAP - Termo de Abertura do Projeto", "DEP - Declaração de Escopo do Projeto"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião", "Cronograma do Projeto", "Plano de Projeto"],
    "Workshop de Processos": ["Levantamento e Análise de Gaps Críticos", "Business Blue Print", "Configuração do Sistema", "Apresentação da Solução", "Termo de Aceite de Entrega"],
    "Construção": ["Plano de Cutover", "Avaliação de Treinamento", "Lista de Presença" , "Treinamento de Tabelas", "Dados mestres e Carga Precursora", "Homologação de Integração com Terceiros"],
    "Go Live": ["Carga Final de Dados", "Escala Apoio ao Go Live", "Metas de Simulação", "Testes Integrados", "Reunição de Go/No Go", "Ata de Reunião"],
    "Operação Assistida": ["Suporte In Loco aos usuários", "Reunião de Pré-Onboarding", "Ata de Reunião", "Identificação de Gaps", "Termo de Aceite de Entrega"],
    "Finalização": ["Reunião de Finalização", "Ata de Reunião", "TEP - Termo de Encerramento do Projeto", "Registro de Lições Aprendidas - MV LEARN | Sharepoint"]
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

    def desenhar_sparkline_pdf(self, perc_fases, y_pos):
        # Configurações da escala no PDF
        x_start = 20
        largura_total = 170
        passo = largura_total / (len(perc_fases) - 1)
        
        # Linha de fundo
        self.set_draw_color(200, 200, 200); self.set_line_width(1)
        self.line(x_start, y_pos + 5, x_start + largura_total, y_pos + 5)
        
        for i, (fase, valor) in enumerate(perc_fases.items()):
            x_circ = x_start + (i * passo)
            # Cor do círculo: Azul Marinho se iniciado, Cinza se 0
            if valor > 0:
                self.set_fill_color(20, 50, 100); self.set_draw_color(255, 179, 14) # Borda amarela
                if valor < 100: self.set_line_width(0.8) 
                else: self.set_line_width(0.1)
            else:
                self.set_fill_color(220, 220, 220); self.set_draw_color(200, 200, 200); self.set_line_width(0.1)
            
            self.ellipse(x_circ - 2.5, y_pos + 2.5, 5, 5, 'FD')
            
            # Texto abaixo
            self.set_font("Helvetica", 'B', 6); self.set_text_color(20, 50, 100)
            self.text(x_circ - 8, y_pos + 12, fase[:15])
            self.set_font("Helvetica", '', 6); self.set_text_color(100, 100, 100)
            self.text(x_circ - 3, y_pos + 15, f"{valor:.0f}%")

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Executive Hub FR.IC.48", layout="wide")
st.title("🛡️ Metodologia | Gestão de Entregas e Conformidade de Implantação")

c1, c2 = st.columns(2)
nome_proj = c1.text_input("Nome do Projeto", placeholder="Ex: Hospital X")
gp_proj = c2.text_input("Gerente de Projeto")

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

# --- ESCALA DE PROGRESSÃO (TELA) ---
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
                <p style='font-size: 10px; font-weight: bold; color: #143264; margin-top: 5px; margin-bottom: 0;'>{fase}</p>
                <p style='font-size: 10px; color: #ffb30e; font-weight: bold;'>{valor:.0f}%</p>
            </div>
        """, unsafe_allow_html=True)

st.markdown("""<style> .stProgress > div > div > div > div { background-color: #143264; } </style>""", unsafe_allow_html=True)
st.progress(global_avg / 100)

# --- AÇÕES ---
st.markdown("---")
col_graf, col_btn = st.columns([2, 1])

with col_graf:
    fig = gerar_radar_chart(perc_fases)
    st.pyplot(fig)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    img_buf.seek(0)

with col_btn:
    st.subheader("⚙️ Hub de Governança")
    
    # SALVAR NO HUB (Corrigido para não imprimir 'None')
    if st.button("💾 SALVAR NO HUB DE INTELIGÊNCIA", use_container_width=True):
        if nome_proj and gp_proj:
            try:
                dados_db = {"nome_projeto": nome_proj, "gerente_projeto": gp_proj}
                for f, v in perc_fases.items(): dados_db[MAPA_COLUNAS[f]] = v
                
                # Executa o salvamento sem exibir o retorno técnico
                novo_registro = Projeto(**dados_db)
                session.add(novo_registro)
                session.commit()
                st.toast("✅ Dados sincronizados!", icon="💾")
                st.success(f"Projeto '{nome_proj}' atualizado com sucesso no Hub.")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
        else:
            st.warning("Preencha Nome do Projeto e Gerente.")

    # RELATÓRIO PDF COM SPARKLINE
    if st.button("📄 GERAR RELATÓRIO COM DIAGNÓSTICO", use_container_width=True, type="primary"):
        if nome_proj:
            st.toast("🤖 Analisando pendências e gerando escala...", icon="⏳")
            pdf = PDFExecutivo()
            pdf.add_page(); pdf.add_watermark(); pdf.set_text_color(0,0,0)
            
            # Cabeçalho de Dados
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(190, 8, f"PROJETO: {nome_proj.upper()}", ln=True)
            pdf.cell(190, 8, f"GP RESPONSÁVEL: {gp_proj}", ln=True)
            pdf.cell(190, 8, f"PROGRESSO GLOBAL: {global_avg:.1f}%", ln=True); pdf.ln(5)
            
            # INCLUSÃO DA ESCALA DE PROGRESSÃO (SPARKLINE) NO PDF
            pdf.set_font("Helvetica", 'B', 11); pdf.set_fill_color(240, 240, 240)
            pdf.cell(190, 8, " ESCALA DE MATURIDADE METODOLÓGICA", 0, 1, 'L', True); pdf.ln(2)
            pdf.desenhar_sparkline_pdf(perc_fases, pdf.get_y())
            pdf.set_y(pdf.get_y() + 25)
            
            # Radar Chart
            pdf.image(img_buf, x=60, w=90); pdf.ln(95)
            
            # Diagnóstico IA
            pdf.set_fill_color(255, 243, 205); pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(190, 10, "DIAGNÓSTICO IA: PENDÊNCIAS E PRÓXIMOS PASSOS", 0, 1, 'L', True); pdf.ln(2)
            pdf.set_font("Helvetica", 'I', 10)
            for fase, itens in detalhes_entrega.items():
                pendentes = [i["doc"] for i in itens if i["status"] == "Pendente"]
                if pendentes:
                    pdf.set_text_color(180, 0, 0)
                    pdf.multi_cell(190, 6, f"Fase {fase}: {len(pendentes)} pendência(s). Resolver: {', '.join(pendentes[:3])}...", border='B')
                    pdf.ln(1)
            
            pdf_bytes = bytes(pdf.output()) 
            
            # Visualização e Botão
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>'
            st.markdown("### 👁️ Visualização Prévia do Relatório")
            st.markdown(pdf_display, unsafe_allow_html=True)
            
            st.download_button("📥 BAIXAR RELATÓRIO PDF", data=pdf_bytes, file_name=f"Status_{nome_proj}.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.warning("Informe o nome do projeto.")




