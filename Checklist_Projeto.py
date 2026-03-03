import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc, text, inspect
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

if not os.path.exists("evidencias_audit"):
    os.makedirs("evidencias_audit")

class Projeto(Base):
    __tablename__ = 'monitoramento_projetos'
    id = Column(Integer, primary_key=True)
    nome_projeto = Column(String); gerente_projeto = Column(String)
    regional = Column(String); oportunidade = Column(String)
    horas_contratadas = Column(Float); tipo = Column(String)
    data_inicio = Column(String); data_termino = Column(String)
    data_entrada_producao = Column(String); data_auditoria = Column(String)
    responsavel_auditoria = Column(String); timestamp = Column(DateTime, default=datetime.now)
    inicializacao = Column(Float, default=0.0); planejamento = Column(Float, default=0.0)
    workshop_de_processos = Column(Float, default=0.0); construcao = Column(Float, default=0.0)
    go_live = Column(Float, default=0.0); operacao_assistida = Column(Float, default=0.0)
    finalizacao = Column(Float, default=0.0)

class AuditoriaHistorico(Base):
    __tablename__ = 'historico_auditorias'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); data_auditoria = Column(String)
    responsavel = Column(String); progresso_total = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)

class Evidencia(Base):
    __tablename__ = 'evidencias_arquivos'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    nome_arquivo = Column(String); caminho = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

class StatusItem(Base):
    __tablename__ = 'status_itens_detalhado'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    item = Column(String); entregue = Column(Integer)

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

# --- POPUP DE AUDITORIA ---
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    status_db = get_status_itens(proj.id)
    
    st.write(f"### Projeto: {proj.nome_projeto}")
    tab1, tab2, tab3 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico", "📂 Evidências"])
    
    with tab1:
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            fase_concluidos = sum(1 for i in itens if status_db.get((fase, i), False))
            f_perc = (fase_concluidos / len(itens)) * 100
            
            with st.expander(f"{fase} - {f_perc:.0f}% Validado", expanded=(f_perc < 100)):
                # BOTÃO DE PRODUTIVIDADE: Marcar todos da fase
                if st.button(f"✅ Marcar todos em {fase}", key=f"btn_all_{fase}"):
                    for item in itens: status_db[(fase, item)] = True
                    st.rerun()

                st.progress(f_perc / 100)
                for item in itens:
                    val_db = status_db.get((fase, item), False)
                    res = st.checkbox(item, value=val_db, key=f"aud_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        
        p_medio = (total_e / total_i) * 100
        if p_medio == 100:
            st.success("🌟 **PROJETO EM CONFORMIDADE INTEGRAL!**")
            st.balloons()
        
        st.divider()
        c1, c2 = st.columns(2)
        aud = c1.text_input("Analista Auditor MV", value=proj.responsavel_auditoria or "")
        data_aud = c2.date_input("Data da Auditoria", value=datetime.now())
        
        if st.button("🚀 CONSOLIDAR AUDITORIA", use_container_width=True):
            session.query(StatusItem).filter(StatusItem.projeto_id == proj.id).delete()
            for (f, i), v in novos_status.items():
                session.add(StatusItem(projeto_id=proj.id, fase=f, item=i, entregue=1 if v else 0))
            for fase in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[fase] if novos_status.get((fase, it)))
                setattr(proj, MAPA_COLUNAS[f], (count / len(METODOLOGIA[fase])) * 100)
            proj.responsavel_auditoria = aud
            session.add(AuditoriaHistorico(projeto_id=proj.id, data_auditoria=str(data_aud), responsavel=aud, progresso_total=p_medio))
            session.commit(); st.success("Auditoria Atualizada!"); st.rerun()

    with tab2:
        hist = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == proj.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if hist:
            df_hist = pd.DataFrame([{"Data": h.data_auditoria, "Auditor": h.responsavel, "Performance": f"{h.progresso_total:.1f}%"} for h in hist])
            st.table(df_hist)

    with tab3:
        f_ev = st.selectbox("Fase:", list(METODOLOGIA.keys()))
        up = st.file_uploader("Anexar Prova Documental", key="up_audit")
        if st.button("Salvar Evidência"):
            if up:
                path = f"evidencias_audit/{proj.id}_{f_ev}_{up.name}"
                with open(path, "wb") as f: f.write(up.getbuffer())
                session.add(Evidencia(projeto_id=proj.id, fase=f_ev, nome_arquivo=up.name, caminho=path))
                session.commit(); st.success("Arquivo Salvo!")

# --- INTERFACE ---
st.set_page_config(page_title="Hub de Inteligência MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='color: #143264;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    with st.container():
        c1, c2, c3 = st.columns(3)
        nome_p = c1.text_input("Nome do Projeto")
        oportunidade = c2.text_input("CRM")
        gp_p = c3.text_input("Gerente")
        c4, c5, c6 = st.columns(3); reg_p = c6.selectbox("Regional", ["Sul", "Sudeste", "Centro-Oeste", "Nordeste", "Norte", "Internacional"])

    fases_lista = list(METODOLOGIA.keys())
    perc_fases = {}
    tabs = st.tabs(fases_lista)
    checks_operacionais = {}

    for i, fase in enumerate(fases_lista):
        with tabs[i]:
            if i > 0 and perc_fases.get(fases_lista[i-1], 0) < 100:
                st.error(f"🚨 FASE BLOQUEADA: Conclua 100% da fase anterior.")
                perc_fases[fase] = 0.0
            else:
                concluidos = 0
                itens = METODOLOGIA[fase]
                cols = st.columns(2)
                for idx, item in enumerate(itens):
                    res = cols[idx % 2].checkbox(item, key=f"op_{fase}_{item}")
                    checks_operacionais[(fase, item)] = res
                    if res: concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100

    # SPARKLINE ORIGINAL (Com linha e bordas conectadas)
    st.markdown("<h3 style='font-size: 18px; color: #143264;'>🛤️ Linha do Tempo da Metodologia</h3>", unsafe_allow_html=True)
    st.markdown("""<style>.timeline-wrapper { position: relative; margin-bottom: 40px; padding-top: 10px; display: flex; justify-content: space-between; align-items: center; } .timeline-line { position: absolute; top: 35px; left: 5%; right: 5%; height: 3px; background-color: #143264; z-index: 1; } .pie-circle { width: 45px; height: 45px; border-radius: 50%; display: inline-block; position: relative; z-index: 2; background-color: white; }</style>""", unsafe_allow_html=True)
    st.markdown("<div class='timeline-wrapper'><div class='timeline-line'></div>", unsafe_allow_html=True)
    cols_visual = st.columns(len(fases_lista))
    for i, fase in enumerate(fases_lista):
        valor = perc_fases[fase]
        cor_borda = "#143264" if valor > 0 else "#FFD700"
        with cols_visual[i]:
            st.markdown(f"<div style='text-align: center;'><div class='pie-circle' style='background: conic-gradient(#143264 {valor}%, #E0E0E0 0); border: 4px solid {cor_borda};'></div><p style='font-size: 11px; font-weight: bold;'>{fase}</p></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        if nome_p and gp_p:
            novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional=reg_p, **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
            session.add(novo); session.flush()
            for (f, i), v in checks_operacionais.items():
                session.add(StatusItem(projeto_id=novo.id, fase=f, item=i, entregue=1 if v else 0))
            session.commit(); st.success("Salvo com sucesso!")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Governança Regional</h2>", unsafe_allow_html=True)
    projs = session.query(Projeto).all()
    if projs:
        df_list = []
        for p in projs:
            d = vars(p).copy()
            itens = session.query(StatusItem).filter(StatusItem.projeto_id == p.id).all()
            total_metodologia = sum(len(v) for v in METODOLOGIA.values())
            entregues = sum(1 for i in itens if i.entregue)
            d['Progresso %'] = round((entregues / total_metodologia) * 100, 1) if total_metodologia > 0 else 0.0
            df_list.append(d)
        
        df_display = pd.DataFrame(df_list).drop_duplicates(subset=['nome_projeto'])
        selecao = st.dataframe(df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %', 'data_auditoria']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")})
        
        if len(selecao.selection.rows) > 0:
            popup_auditoria(int(df_display.iloc[selecao.selection.rows[0]]['id']))
