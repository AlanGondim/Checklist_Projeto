import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc, text
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
    data_inicio = Column(String)
    data_termino = Column(String)
    data_entrada_producao = Column(String)
    data_auditoria = Column(String)
    responsavel_auditoria = Column(String)
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

# --- FUNÇÃO PARA APRESENTAR ARTEFATOS PENDENTES (CORRIGIDA) ---
@st.dialog("📋 Artefatos Pendentes por Fase", width="large")
def modal_pendencias(projeto_data):
    st.write(f"### Projeto: {projeto_data['nome_projeto']}")
    st.write(f"**Gerente:** {projeto_data['gerente_projeto']} | **Regional:** {projeto_data['regional']}")
    st.markdown("---")
    
    # Percorre cada fase da metodologia
    for fase, itens in METODOLOGIA.items():
        # BUSCA DIRETO PELO NOME DA FASE (pois o DF foi renomeado antes de vir para cá)
        percentual = projeto_data.get(fase, 0.0)
        
        if percentual < 100:
            with st.expander(f"⚠️ {fase} ({percentual:.0f}% concluído)", expanded=True):
                st.write("Itens da metodologia para esta fase:")
                for item in itens:
                    st.markdown(f"- [ ] {item}")
        else:
            st.success(f"✅ {fase}: Todos os artefatos entregues.")

    if st.button("Fechar"):
        st.rerun()

# --- INTERFACE ---
st.set_page_config(page_title="Hub de Inteligência MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='font-size: 24px; color: #143264; font-weight: bold;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        nome_p = c1.text_input("Nome do Projeto")
        oportunidade = c2.text_input("Oportunidade (CRM)")
        gp_p = c3.text_input("Gerente de Projeto")

        c4, c5, c6 = st.columns(3)
        horas_cont = c4.number_input("Horas Contratadas", min_value=0.0, step=10.0)
        tipo_p = c5.selectbox("Tipo do Projeto", ["Migração", "Implantação", "Consultoria", "Revitalização"])
        reg_p = c6.selectbox("Regional", ["Sul", "Sudeste", "Centro-Oeste", "Nordeste", "Norte", "Internacional"])

        c7, c8, c9 = st.columns(3)
        d_inicio = c7.date_input("Data de Início", format="DD/MM/YYYY")
        d_termino = c8.date_input("Data de Término", format="DD/MM/YYYY")
        d_producao = c9.date_input("Data de Entrada em Produção", format="DD/MM/YYYY")

        c10, c11 = st.columns(2)
        d_auditoria = c10.date_input("Data da Auditoria", format="DD/MM/YYYY")
        resp_auditoria = c11.text_input("Responsável pela Auditoria")

    fases_lista = list(METODOLOGIA.keys())
    perc_fases = {}
    for fase in fases_lista: perc_fases[fase] = 0.0

    st.markdown("---")
    tabs = st.tabs(fases_lista)
    for i, fase in enumerate(fases_lista):
        with tabs[i]:
            if i > 0 and perc_fases.get(fases_lista[i-1], 0) < 100:
                st.error(f"🚨 FASE BLOQUEADA: Conclua 100% da fase anterior para liberar '{fase}'.")
                perc_fases[fase] = 0.0
            else:
                concluidos = 0
                itens = METODOLOGIA[fase]
                cols_check = st.columns(2)
                for idx, item in enumerate(itens):
                    if cols_check[idx % 2].checkbox(item, key=f"c_{fase}_{item}"):
                        concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100

    # --- RENDERIZAÇÃO SPARKLINE ---
    st.markdown("<h3 style='font-size: 18px; color: #143264;'>🛤️ Linha do Tempo da Metodologia</h3>", unsafe_allow_html=True)
    st.markdown("""
        <style>
        .timeline-wrapper { position: relative; margin-bottom: 40px; padding-top: 10px; }
        .timeline-line { position: absolute; top: 38px; left: 5%; right: 5%; height: 3px; background-color: #143264; z-index: 1; }
        .pie-circle { 
            width: 45px; height: 45px; border-radius: 50%; display: inline-block;
            transition: all 0.3s ease; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
            position: relative; z-index: 2; background-color: white;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='timeline-wrapper'>", unsafe_allow_html=True)
    st.markdown("<div class='timeline-line'></div>", unsafe_allow_html=True)
    cols_visual = st.columns(len(fases_lista))
    for i, fase in enumerate(fases_lista):
        valor = perc_fases[fase]
        border_color = "#FFD700" if valor < 100 else "#143264"
        with cols_visual[i]:
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div class='pie-circle' style='background: conic-gradient(#143264 {valor}%, #E0E0E0 0); border: 3px solid {border_color};'></div>
                    <p style='font-size: 11px; font-weight: bold; color: #143264; margin-top: 8px;'>{fase}</p>
                    <p style='font-size: 14px; font-weight: bold; color: #143264;'>{valor:.0f}%</p>
                </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        if nome_p and gp_p:
            try:
                novo = Projeto(
                    nome_projeto=nome_p, gerente_projeto=gp_p, regional=reg_p, oportunidade=oportunidade,
                    horas_contratadas=horas_cont, tipo=tipo_p, data_inicio=str(d_inicio),
                    data_termino=str(d_termino), data_entrada_producao=str(d_producao),
                    data_auditoria=str(d_auditoria), responsavel_auditoria=resp_auditoria,
                    **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()}
                )
                session.add(novo); session.commit()
                st.success("Snapshot salvo com sucesso!")
                st.balloons()
            except Exception as e: st.error(f"Erro ao salvar: {e}")
        else: st.warning("Preencha o Nome do Projeto e do Gerente.")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='font-size: 24px; color: #143264; font-weight: bold;'>📊 Dashboard de Governança Regional</h2>", unsafe_allow_html=True)
    
    query = session.query(Projeto).order_by(desc(Projeto.timestamp)).all()
    if query:
        df = pd.DataFrame([vars(p) for p in query]).drop_duplicates(subset=['nome_projeto'], keep='first')
        df['regional'] = df['regional'].fillna("N/D")
        df['gerente_projeto'] = df['gerente_projeto'].fillna("Sem Nome")
        
        # Mapeamento para exibição
        col_fases_db = list(MAPA_COLUNAS.values())
        col_fases_reais = list(MAPA_COLUNAS.keys())
        df['Progresso %'] = df[col_fases_db].mean(axis=1).round(1)

        # --- FILTROS SIDEBAR ---
        st.sidebar.header("🎯 Filtros")
        gerentes_list = sorted(df['gerente_projeto'].unique())
        f_gp = st.sidebar.multiselect("Filtrar por Gerente", gerentes_list, default=gerentes_list)
        regionais_list = sorted(df['regional'].unique())
        f_reg = st.sidebar.multiselect("Filtrar por Regional", regionais_list, default=regionais_list)

        df_filt = df[(df['gerente_projeto'].isin(f_gp)) & (df['regional'].isin(f_reg))]

        if not df_filt.empty:
            # --- RESUMO POR GERENTE ---
            st.markdown("### 🏆 Performance Média por Gerente")
            df_gerente = df_filt.groupby('gerente_projeto').agg({'Progresso %': 'mean', 'nome_projeto': 'count'}).reset_index()
            df_gerente.columns = ['Gerente', 'Média de Entrega %', 'Qtd Projetos']
            st.dataframe(df_gerente.sort_values('Média de Entrega %', ascending=False), use_container_width=True, hide_index=True,
                         column_config={"Média de Entrega %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")})

            # --- TABELA COMPLETA INTERATIVA (EM SUBSTITUIÇÃO AO GRÁFICO) ---
            st.markdown("---")
            st.markdown("### 🔎 Detalhamento Completo da Carteira")
            st.info("💡 **Dica:** Clique em uma linha da tabela para visualizar quais artefatos estão pendentes por fase.")
            
            # Preparação do DataFrame Detalhado
            df_detalhe = df_filt.copy()
            df_detalhe = df_detalhe.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
            
            colunas_view = ['nome_projeto', 'gerente_projeto', 'regional', 'tipo', 'Progresso %'] + col_fases_reais
            df_display = df_detalhe[colunas_view].sort_values(by='Progresso %', ascending=False)

            # --- NOVA TABELA INTERATIVA COM SELEÇÃO ---
            evento_selecao = st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                on_select="rerun", # Faz a página reagir ao clique
                selection_mode="single-row", # Permite selecionar uma linha por vez
                column_config={
                    "Progresso %": st.column_config.ProgressColumn("Progresso Total", min_value=0, max_value=100, format="%.1f%%"),
                    **{fase: st.column_config.NumberColumn(f"{fase} %", format="%.0f%%") for fase in col_fases_reais}
                }
            )

            # Lógica para abrir o Popup ao selecionar a linha
            if len(evento_selecao.selection.rows) > 0:
                # Recupera os dados da linha selecionada
                idx_selecionado = evento_selecao.selection.rows[0]
                dados_projeto = df_detalhe.iloc[idx_selecionado]
                
                # Chama a função de popup definida no passo 1
                modal_pendencias(dados_projeto)


