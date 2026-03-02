import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
    regional = Column(String)
    oportunidade = Column(String)
    horas_contratadas = Column(Float)
    tipo = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    inicializacao = Column(Float); planejamento = Column(Float)
    workshop_de_processos = Column(Float); construcao = Column(Float)
    go_live = Column(Float); operacao_assistida = Column(Float)
    finalizacao = Column(Float)

Base.metadata.create_all(engine)

# --- METODOLOGIA ---
METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "Orçamento Inicial", "Alinhamento time MV", "Ata de reunião", "Alinhamento Cliente", "TAP", "DEP"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião", "Cronograma", "Plano de Projeto"],
    "Workshop de Processos": ["Análise de Gaps Críticos", "Business Blue Print", "Configuração do Sistema", "Apresentação da Solução", "Termo de Aceite"],
    "Construção": ["Plano de Cutover", "Avaliação de Treinamento", "Lista de Presença", "Treinamento de Tabelas", "Carga Precursora", "Homologação Integração"],
    "Go Live": ["Carga Final de Dados", "Escala Apoio Go Live", "Metas de Simulação", "Testes Integrados", "Reunição Go/No Go", "Ata de Reunião"],
    "Operação Assistida": ["Suporte In Loco", "Pré-Onboarding", "Ata de Reunião", "Identificação de Gaps", "Termo de Aceite"],
    "Finalização": ["Reunião de Finalização", "Ata de Reunião", "TEP", "Registro das Lições Aprendidas - MV LEARN"]
}

MAPA_COLUNAS = {
    "Inicialização": "inicializacao", "Planejamento": "planejamento", 
    "Workshop de Processos": "workshop_de_processos", "Construção": "construcao",
    "Go Live": "go_live", "Operação Assistida": "operacao_assistida", "Finalização": "finalizacao"
}

# --- INTERFACE ---
st.set_page_config(page_title="Checklist de Projeto MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional (Executivo)"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='font-size: 24px; color: #143264; font-weight: bold;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        nome_p = c1.text_input("Nome do Projeto")
        gp_p = c2.text_input("Gerente de Projeto")
        reg_p = c3.selectbox("Regional", ["Sul", "Sudeste", "Centro-Oeste", "Nordeste", "Norte", "Internacional"])

    # --- LÓGICA DE TRAVA ---
    fases_lista = list(METODOLOGIA.keys())
    tabs = st.tabs(fases_lista)
    perc_fases = {}

    for i, fase in enumerate(fases_lista):
        with tabs[i]:
            # Verifica se a fase anterior atingiu 100%
            if i > 0 and perc_fases.get(fases_lista[i-1], 0) < 100:
                st.error(f"🚨 FASE BLOQUEADA: Conclua 100% da fase anterior ({fases_lista[i-1]}) para habilitar '{fase}'.")
                perc_fases[fase] = 0.0
            else:
                concluidos = 0
                itens = METODOLOGIA[fase]
                cols = st.columns(2)
                for idx, item in enumerate(itens):
                    if cols[idx % 2].checkbox(item, key=f"c_{fase}_{item}"):
                        concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100
                st.info(f"Progresso de {fase}: {perc_fases[fase]:.1f}%")

# --- NOVO BLOCO: SPARKLINE VISUAL DAS FASES ---
    st.markdown("---")
    st.markdown("<h3 style='font-size: 18px; color: #143264;'>🛤️ Linha do Tempo da Metodologia</h3>", unsafe_allow_html=True)
    
    cols_spark = st.columns(len(fases_lista))
    for i, fase in enumerate(fases_lista):
        with cols_spark[i]:
            valor = perc_fases.get(fase, 0)
            # Regra: Azul marinho se concluído, Cinza com borda amarela se pendente
            if valor >= 100:
                bg_color = "#143264"
                border_style = "none"
                text_color = "#143264"
            else:
                bg_color = "#E0E0E0"
                border_style = "2px solid #FFD700" # Amarelo destacado
                text_color = "#757575"
            
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div style='display: inline-block; width: 30px; height: 30px; border-radius: 50%; 
                         background-color: {bg_color}; border: {border_style}; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);'>
                    </div>
                    <p style='font-size: 11px; font-weight: bold; color: {text_color}; margin-top: 5px;'>{fase}</p>
                    <p style='font-size: 12px; font-weight: bold; color: #FFD700;'>{valor:.0f}%</p>
                </div>
            """, unsafe_allow_html=True)
    st.markdown("---")
    
    if st.button("💾 SALVAR NO HUB"):
        if nome_p:
            novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional=reg_p,
                           **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
            session.add(novo); session.commit()
            st.success("Dados salvos com sucesso!")
        else:
            st.warning("O Nome do Projeto é obrigatório.")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='font-size: 24px; color: #143264; font-weight: bold;'>📊 Dashboard de Governança Regional</h2>", unsafe_allow_html=True)
    
    query = session.query(Projeto).order_by(desc(Projeto.timestamp)).all()
    if query:
        df = pd.DataFrame([vars(p) for p in query]).drop_duplicates(subset=['nome_projeto'], keep='first')
        
        # Tratamento de Nulos para evitar erro de ordenação
        df['regional'] = df['regional'].fillna("N/D")
        df['gerente_projeto'] = df['gerente_projeto'].fillna("N/D")

        # Nomes amigáveis
        df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
        colunas_fases = list(METODOLOGIA.keys())
        df_display['Progresso Global %'] = df_display[colunas_fases].mean(axis=1).round(1)

        # --- FILTROS ---
        st.sidebar.header("🎯 Filtros")
        f_reg = st.sidebar.multiselect("Regionais", sorted(df_display['regional'].unique()), default=df_display['regional'].unique())
        f_gp = st.sidebar.multiselect("Gerentes", sorted(df_display['gerente_projeto'].unique()), default=df_display['gerente_projeto'].unique())

        df_filt = df_display[(df_display['regional'].isin(f_reg)) & (df_display['gerente_projeto'].isin(f_gp))]

        if not df_filt.empty:
            # Ranking Detalhado
            st.markdown("### 🔍 Ranking de Entrega Detalhado")
            st.dataframe(
                df_filt[['regional', 'gerente_projeto', 'nome_projeto', 'Progresso Global %'] + colunas_fases],
                use_container_width=True, hide_index=True,
                column_config={
                    "Progresso Global %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                    **{fase: st.column_config.NumberColumn(format="%.0f%%") for fase in colunas_fases}
                }
            )

            # --- GRÁFICO DE BARRAS HORIZONTAIS ---
            st.markdown("---")
            st.markdown("### 📈 Comparativo Global de Performance")
            
            # Ordenando para o gráfico ficar mais intuitivo (melhores no topo)
            df_chart = df_filt.sort_values(by='Progresso Global %', ascending=True)
            
            # Usando st.bar_chart configurado para horizontal através de Matplotlib para maior controle
            fig_bar, ax_bar = plt.subplots(figsize=(10, len(df_chart) * 0.6 + 2))
            barras = ax_bar.barh(df_chart['nome_projeto'], df_chart['Progresso Global %'], color='#143264')
            
            ax_bar.set_xlabel('Progresso Global %', fontweight='bold', color='#143264')
            ax_bar.set_xlim(0, 105)
            ax_bar.spines['top'].set_visible(False)
            ax_bar.spines['right'].set_visible(False)
            
            # Adiciona rótulos de dados
            for bar in barras:
                width = bar.get_width()
                ax_bar.text(width + 1, bar.get_y() + bar.get_height()/2, f'{width}%', va='center', fontsize=9, fontweight='bold')

            st.pyplot(fig_bar)

        else:
            st.warning("Sem dados para os filtros selecionados.")
    else:
        st.info("Nenhum projeto registrado.")



