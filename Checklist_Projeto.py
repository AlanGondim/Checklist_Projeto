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

# Diretório para evidências (Prints de e-mail, PDFs, etc)
if not os.path.exists("evidencias_audit"):
    os.makedirs("evidencias_audit")

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

# Novas tabelas para Auditoria e Rastreabilidade
class AuditoriaHistorico(Base):
    __tablename__ = 'historico_auditorias'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer)
    data_auditoria = Column(String)
    responsavel = Column(String)
    status_snapshot = Column(String) # JSON ou String com resumo
    timestamp = Column(DateTime, default=datetime.now)

class Evidencia(Base):
    __tablename__ = 'evidencias_arquivos'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer)
    fase = Column(String)
    nome_arquivo = Column(String)
    caminho = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

class StatusItem(Base):
    __tablename__ = 'status_itens_detalhado'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer)
    fase = Column(String)
    item = Column(String)
    entregue = Column(Integer) # 1 ou 0

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

# --- FUNÇÕES DE APOIO ---
def get_status_itens(projeto_id):
    itens = session.query(StatusItem).filter(StatusItem.projeto_id == projeto_id).all()
    return {(i.fase, i.item): bool(i.entregue) for i in itens}

# --- POPUP DE AUDITORIA DE RASTREABILIDADE ---
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto):
    st.write(f"### Projeto: {projeto.nome_projeto} | Regional: {projeto.regional}")
    
    status_db = get_status_itens(projeto.id)
    tab1, tab2, tab3 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico de Auditorias", "📂 Evidências (Docs/Prints)"])
    
    with tab1:
        st.info("Valide os artefatos entregues. Itens marcados anteriormente aparecem com check.")
        novos_status = {}
        for fase, itens in METODOLOGIA.items():
            entregues_fase = sum(1 for i in itens if status_db.get((fase, i), False))
            perc_fase = (entregues_fase / len(itens)) * 100
            
            with st.expander(f"Fase: {fase} | Status: {perc_fase:.1f}%"):
                for item in itens:
                    val_check = status_db.get((fase, item), False)
                    novos_status[(fase, item)] = st.checkbox(item, value=val_check, key=f"aud_{projeto.id}_{fase}_{item}")
        
        st.divider()
        c1, c2 = st.columns(2)
        auditor = c1.text_input("Analista Auditor MV", key="auditor_nome")
        data_aud = c2.date_input("Data da Auditoria Técnica", value=datetime.now())
        
        if st.button("💾 Consolidar Auditoria e Salvar Rastreabilidade", use_container_width=True):
            # Salvar itens individuais
            session.query(StatusItem).filter(StatusItem.projeto_id == projeto.id).delete()
            for (f, i), val in novos_status.items():
                session.add(StatusItem(projeto_id=projeto.id, fase=f, item=i, entregue=1 if val else 0))
            
            # Atualizar percentuais na tabela Projeto
            proj_db = session.query(Projeto).filter(Projeto.id == projeto.id).first()
            for fase in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[fase] if novos_status[(fase, it)])
                setattr(proj_db, MAPA_COLUNAS[fase], (count / len(METODOLOGIA[fase])) * 100)
            
            proj_db.data_auditoria = str(data_aud)
            proj_db.responsavel_auditoria = auditor
            
            # Histórico
            session.add(AuditoriaHistorico(projeto_id=projeto.id, data_auditoria=str(data_aud), responsavel=auditor))
            session.commit()
            st.success("Auditoria Consolidada com Sucesso! Risco jurídico mitigado.")
            st.rerun()

    with tab2:
        st.write("### Linha do Tempo de Auditorias")
        historico = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == projeto.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if historico:
            for h in historico:
                st.write(f"📅 **{h.data_auditoria}** - Auditor: `{h.responsavel}` (Registrado em: {h.timestamp.strftime('%d/%m/%Y %H:%M')})")
        else:
            st.warning("Nenhuma auditoria anterior registrada para este projeto.")

    with tab3:
        st.write("### 📎 Depósito de Evidências (Prints de E-mail / Documentos)")
        fase_ev = st.selectbox("Vincular evidência à fase:", list(METODOLOGIA.keys()))
        uploaded_file = st.file_uploader("Arraste prints ou documentos aqui", key="file_audit")
        
        if st.button("📤 Salvar Evidência"):
            if uploaded_file:
                caminho = os.path.join("evidencias_audit", f"{projeto.id}_{fase_ev}_{uploaded_file.name}")
                with open(caminho, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                session.add(Evidencia(projeto_id=projeto.id, fase=fase_ev, nome_arquivo=uploaded_file.name, caminho=caminho))
                session.commit()
                st.success(f"Evidência para {fase_ev} salva com sucesso!")
        
        st.divider()
        st.write("### Arquivos Vinculados")
        evs = session.query(Evidencia).filter(Evidencia.projeto_id == projeto.id).all()
        for ev in evs:
            col_a, col_b = st.columns([0.8, 0.2])
            col_a.write(f"📄 **{ev.fase}**: {ev.nome_arquivo}")
            with open(ev.caminho, "rb") as f:
                col_b.download_button("Baixar", f, file_name=ev.nome_arquivo, key=f"dl_{ev.id}")

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
    

[Image of Gantt chart showing project phases]

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
                # Ao salvar no HUB, também inicializamos o status detalhado se for novo
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

            # --- TABELA COMPLETA INTERATIVA ---
            st.markdown("---")
            st.markdown("### 🔎 Detalhamento Completo da Carteira")
            st.info("💡 **Ação**: Selecione um projeto na tabela abaixo para abrir o painel de Auditoria de Rastreabilidade.")
            
            # Preparação do DataFrame Detalhado
            df_detalhe = df_filt.copy()
            df_detalhe = df_detalhe.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
            
            # Seleção e Ordenação das Colunas (incluindo ID oculto para busca)
            colunas_view = ['id', 'nome_projeto', 'gerente_projeto', 'regional', 'Progresso %'] + col_fases_reais
            
            # Tabela com seleção de linha
            selecao = st.dataframe(
                df_detalhe[colunas_view].sort_values(by='Progresso %', ascending=False),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "id": None, # Oculta o ID
                    "Progresso %": st.column_config.ProgressColumn("Progresso Total", min_value=0, max_value=100, format="%.1f%%"),
                    **{fase: st.column_config.NumberColumn(f"{fase} %", format="%.0f%%") for fase in col_fases_reais}
                }
            )

            # Lógica do Popup
            if len(selecao["selection"]["rows"]) > 0:
                row_idx = selecao["selection"]["rows"][0]
                projeto_id = df_detalhe.iloc[row_idx]['id']
                projeto_obj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
                if projeto_obj:
                    popup_auditoria(projeto_obj)
                    
        else: st.warning("Nenhum projeto encontrado para os filtros selecionados.")
    else: st.info("Nenhum projeto registrado.")
