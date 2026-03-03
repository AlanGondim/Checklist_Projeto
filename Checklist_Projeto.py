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

class AuditoriaHistorico(Base):
    __tablename__ = 'historico_auditorias'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer)
    nome_projeto = Column(String)
    data_auditoria = Column(String)
    responsavel_auditoria = Column(String)
    progresso_total = Column(Float)
    fase_atual = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

class ItemAuditoria(Base):
    __tablename__ = 'itens_auditados'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer)
    fase = Column(String)
    item_nome = Column(String)
    entregue = Column(Integer)  # 1 para Sim, 0 para Não

Base.metadata.create_all(engine)

# --- FUNÇÕES DE APOIO ---
def get_status_itens(projeto_id):
    itens = session.query(ItemAuditoria).filter(ItemAuditoria.projeto_id == projeto_id).all()
    return {(item.fase, item.item_nome): bool(item.entregue) for item in itens}

def salvar_status_itens(projeto_id, status_dict):
    session.query(ItemAuditoria).filter(ItemAuditoria.projeto_id == projeto_id).delete()
    for (fase, item_nome), entregue in status_dict.items():
        novo_item = ItemAuditoria(
            projeto_id=projeto_id,
            fase=fase,
            item_nome=item_nome,
            entregue=1 if entregue else 0
        )
        session.add(novo_item)
    session.commit()

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

@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def modal_pendencias(projeto_data):
    projeto_id = int(projeto_data['id'])
    st.write(f"### Projeto: {projeto_data['nome_projeto']}")
    
    status_atual = get_status_itens(projeto_id)
    novos_status = {}

    tab1, tab2 = st.tabs(["📝 Atualizar Auditoria", "📜 Histórico"])

    with tab1:
        st.info("Itens marcados já foram validados anteriormente. Atualize os novos entregues.")
        for fase, itens in METODOLOGIA.items():
            with st.expander(f"Fase: {fase}"):
                for item in itens:
                    valor_previo = status_atual.get((fase, item), False)
                    check = st.checkbox(f"{item}", value=valor_previo, key=f"chk_{projeto_id}_{fase}_{item}")
                    novos_status[(fase, item)] = check

        st.divider()
        c1, c2 = st.columns(2)
        nova_data = c1.date_input("Data da Auditoria", format="DD/MM/YYYY")
        novo_resp = c2.text_input("Analista Auditor", value=projeto_data.get('responsavel_auditoria', ''))

        if st.button("💾 Finalizar e Salvar Evolução", use_container_width=True):
            salvar_status_itens(projeto_id, novos_status)
            
            updates_projeto = {}
            total_perc = 0
            for fase, itens_fase in METODOLOGIA.items():
                concluidos = sum(1 for it in itens_fase if novos_status.get((fase, it)))
                p_fase = (concluidos / len(itens_fase)) * 100
                updates_projeto[MAPA_COLUNAS[fase]] = p_fase
                total_perc += p_fase

            proj_db = session.query(Projeto).filter(Projeto.id == projeto_id).first()
            for col, val in updates_projeto.items():
                setattr(proj_db, col, val)
            proj_db.data_auditoria = str(nova_data)
            proj_db.responsavel_auditoria = novo_resp
            
            nova_aud = AuditoriaHistorico(
                projeto_id=projeto_id,
                nome_projeto=projeto_data['nome_projeto'],
                data_auditoria=str(nova_data),
                responsavel_auditoria=novo_resp,
                progresso_total=total_perc / len(METODOLOGIA),
                fase_atual="Auditoria Técnica"
            )
            session.add(nova_aud)
            session.commit()
            st.success("Dados salvos!")
            st.rerun()

    with tab2:
        historico = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == projeto_id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if historico:
            for h in historico:
                with st.expander(f"📅 {h.data_auditoria} - Progresso: {h.progresso_total:.1f}%"):
                    st.write(f"**Auditor:** {h.responsavel_auditoria}")
                    st.caption(f"Registro: {h.timestamp.strftime('%d/%m/%Y %H:%M')}")
        else:
            st.info("Sem histórico registrado.")

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
                st.error(f"🚨 FASE BLOQUEADA: Conclua 100% da fase anterior.")
                perc_fases[fase] = 0.0
            else:
                concluidos = 0
                itens = METODOLOGIA[fase]
                cols_check = st.columns(2)
                for idx, item in enumerate(itens):
                    if cols_check[idx % 2].checkbox(item, key=f"c_{fase}_{item}"):
                        concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100

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
                st.success("Snapshot salvo!")
            except Exception as e: st.error(f"Erro: {e}")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='font-size: 24px; color: #143264; font-weight: bold;'>📊 Dashboard de Governança Regional</h2>", unsafe_allow_html=True)
    
    query = session.query(Projeto).order_by(desc(Projeto.timestamp)).all()
    if query:
        df = pd.DataFrame([vars(p) for p in query]).drop_duplicates(subset=['nome_projeto'], keep='first')
        df['regional'] = df['regional'].fillna("N/D")
        df['gerente_projeto'] = df['gerente_projeto'].fillna("Sem Nome")
        
        col_fases_db = list(MAPA_COLUNAS.values())
        col_fases_reais = list(MAPA_COLUNAS.keys())
        df['Progresso %'] = df[col_fases_db].mean(axis=1).round(1)

        f_gp = st.sidebar.multiselect("Filtrar por Gerente", sorted(df['gerente_projeto'].unique()))
        f_reg = st.sidebar.multiselect("Filtrar por Regional", sorted(df['regional'].unique()))

        if f_gp: df = df[df['gerente_projeto'].isin(f_gp)]
        if f_reg: df = df[df['regional'].isin(f_reg)]

        if not df.empty:
            df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
            col_view = ['id', 'nome_projeto', 'gerente_projeto', 'regional', 'Progresso %'] + col_fases_reais
            
            sel_event = st.dataframe(
                df_display[col_view],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "id": None,
                    "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")
                }
            )

            if len(sel_event.selection.rows) > 0:
                idx = sel_event.selection.rows[0]
                modal_pendencias(df_display.iloc[idx])
