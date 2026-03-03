import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# --- DATABASE SETUP ---
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia_executivo.db'
engine = create_engine(DB_NAME)
Session = sessionmaker(bind=engine)
session = Session()

# Diretório para evidências
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

class AuditoriaHistorico(Base):
    __tablename__ = 'historico_auditorias'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer)
    data_auditoria = Column(String)
    responsavel = Column(String)
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
    entregue = Column(Integer) 

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

def get_status_itens(projeto_id):
    itens = session.query(StatusItem).filter(StatusItem.projeto_id == projeto_id).all()
    return {(i.fase, i.item): bool(i.entregue) for i in itens}

# --- POPUP DE AUDITORIA CORRIGIDO ---
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    # Busca o objeto do projeto atualizado do banco
    projeto = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    st.write(f"## Projeto: {projeto.nome_projeto}")
    
    status_db = get_status_itens(projeto.id)
    tab1, tab2, tab3 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico", "📂 Evidências"])
    
    with tab1:
        st.info("Valide os artefatos. Itens entregues em auditorias passadas estão marcados ✅")
        novos_status = {}
        
        for fase, itens in METODOLOGIA.items():
            entregues_count = sum(1 for i in itens if status_db.get((fase, i), False))
            perc_fase = (entregues_count / len(itens)) * 100
            
            with st.expander(f"Fase: {fase} | Entrega: {perc_fase:.0f}%", expanded=(perc_fase < 100)):
                st.progress(perc_fase / 100)
                for item in itens:
                    # Rastreabilidade: recupera valor do banco de dados
                    foi_entregue = status_db.get((fase, item), False)
                    res = st.checkbox(item, value=foi_entregue, key=f"aud_{projeto.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
        
        st.divider()
        c1, c2 = st.columns(2)
        auditor = c1.text_input("Analista Auditor MV", value=projeto.responsavel_auditoria if projeto.responsavel_auditoria else "")
        data_aud = c2.date_input("Data da Auditoria Técnica", value=datetime.now())
        
        if st.button("🚀 Consolidar Auditoria e Salvar Evolução", use_container_width=True):
            # 1. Limpa e salva novos status detalhados
            session.query(StatusItem).filter(StatusItem.projeto_id == projeto.id).delete()
            for (f, i), val in novos_status.items():
                session.add(StatusItem(projeto_id=projeto.id, fase=f, item=i, entregue=1 if val else 0))
            
            # 2. Recalcula percentuais para a tabela principal
            for fase in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[fase] if novos_status[(fase, it)])
                setattr(projeto, MAPA_COLUNAS[fase], (count / len(METODOLOGIA[fase])) * 100)
            
            projeto.data_auditoria = str(data_aud)
            projeto.responsavel_auditoria = auditor
            
            # 3. Adiciona ao histórico de snapshots
            session.add(AuditoriaHistorico(projeto_id=projeto.id, data_auditoria=str(data_aud), responsavel=auditor))
            session.commit()
            st.success("Auditoria Consolidada com Sucesso!")
            st.rerun()

    with tab2:
        st.write("### Linha do Tempo de Auditorias")
        historico = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == projeto.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if historico:
            for h in historico:
                st.write(f"📅 **{h.data_auditoria}** - Auditor: `{h.responsavel}` (Registrado em: {h.timestamp.strftime('%H:%M')})")
        else: st.info("Sem histórico registrado.")

    with tab3:
        st.write("### 📎 Depósito de Evidências (Prints/Docs)")
        fase_ev = st.selectbox("Vincular à fase:", list(METODOLOGIA.keys()))
        up_file = st.file_uploader("Arraste documentos ou prints aqui", key="file_audit_popup")
        if st.button("📤 Salvar Arquivo"):
            if up_file:
                path = os.path.join("evidencias_audit", f"{projeto.id}_{fase_ev}_{up_file.name}")
                with open(path, "wb") as f: f.write(up_file.getbuffer())
                session.add(Evidencia(projeto_id=projeto.id, fase=fase_ev, nome_arquivo=up_file.name, caminho=path))
                session.commit()
                st.success("Evidência anexada!")
        st.divider()
        evs = session.query(Evidencia).filter(Evidencia.projeto_id == projeto.id).all()
        for ev in evs:
            with open(ev.caminho, "rb") as f:
                st.download_button(f"⬇️ {ev.fase}: {ev.nome_arquivo}", f, file_name=ev.nome_arquivo, key=f"dl_{ev.id}")

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
                st.success("Snapshot salvo com sucesso!")
            except Exception as e: st.error(f"Erro ao salvar: {e}")
        else: st.warning("Preencha os campos obrigatórios.")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='font-size: 24px; color: #143264; font-weight: bold;'>📊 Dashboard de Governança Regional</h2>", unsafe_allow_html=True)
    
    query = session.query(Projeto).order_by(desc(Projeto.timestamp)).all()
    if query:
        df = pd.DataFrame([vars(p) for p in query]).drop_duplicates(subset=['nome_projeto'], keep='first')
        df['Progresso %'] = df[list(MAPA_COLUNAS.values())].mean(axis=1).round(1)

        f_gp = st.sidebar.multiselect("Filtrar Gerente", sorted(df['gerente_projeto'].unique()))
        f_reg = st.sidebar.multiselect("Filtrar Regional", sorted(df['regional'].unique()))

        if f_gp: df = df[df['gerente_projeto'].isin(f_gp)]
        if f_reg: df = df[df['regional'].isin(f_reg)]

        if not df.empty:
            df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
            col_view = ['id', 'nome_projeto', 'gerente_projeto', 'regional', 'Progresso %', 'data_auditoria']
            
            st.info("💡 Clique em uma linha para abrir a Auditoria de Rastreabilidade.")
            
            # Seleção de linha
            selecao = st.dataframe(
                df_display[col_view].sort_values(by='Progresso %', ascending=False),
                use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
                column_config={
                    "id": None, 
                    "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")
                }
            )

            # ACIONAMENTO DO POPUP
            if len(selecao["selection"]["rows"]) > 0:
                idx = selecao["selection"]["rows"][0]
                projeto_id = int(df_display.iloc[idx]['id'])
                popup_auditoria(projeto_id)
                    
        else: st.warning("Nenhum projeto encontrado.")
    else: st.info("Nenhum projeto registrado no sistema.")
