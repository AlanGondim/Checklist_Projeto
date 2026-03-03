import streamlit as st
import pandas as pd
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
    
    t1, t2, t3 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico", "📂 Evidências"])
    
    with t1:
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            f_concluidos = sum(1 for i in itens if status_db.get((fase, i), False))
            f_perc = (f_concluidos / len(itens)) * 100
            
            with st.expander(f"{fase} - {f_perc:.0f}% Auditado", expanded=(f_perc < 100)):
                st.progress(f_perc / 100)
                for item in itens:
                    val_check = status_db.get((fase, item), False)
                    res = st.checkbox(item, value=val_check, key=f"aud_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        
        p_medio = (total_e / total_i) * 100
        if p_medio == 100:
            st.success("🌟 **CONFORMIDADE INTEGRAL IDENTIFICADA!** O projeto atende 100% dos requisitos.")
            st.balloons()
        
        st.divider()
        aud = st.text_input("Analista Auditor MV", value=proj.responsavel_auditoria or "")
        if st.button("🚀 CONSOLIDAR AUDITORIA", use_container_width=True):
            session.query(StatusItem).filter(StatusItem.projeto_id == proj.id).delete()
            for (f, i), v in novos_status.items():
                session.add(StatusItem(projeto_id=proj.id, fase=f, item=i, entregue=1 if v else 0))
            for fase in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[fase] if novos_status.get((fase, it)))
                setattr(proj, MAPA_COLUNAS[f], (count / len(METODOLOGIA[fase])) * 100)
            proj.responsavel_auditoria = aud
            session.add(AuditoriaHistorico(projeto_id=proj.id, data_auditoria=str(datetime.now().date()), responsavel=aud, progresso_total=p_medio))
            session.commit(); st.success("Auditado!"); st.rerun()

    with t2:
        hist = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == proj.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if hist:
            df_hist = pd.DataFrame([{"Data": h.data_auditoria, "Auditor": h.responsavel, "Performance": f"{h.progresso_total:.1f}%"} for h in hist])
            st.table(df_hist)

    with t3:
        # [Espaço para upload e visualização de anexos conforme solicitado]
        f_ev = st.selectbox("Vincular à fase:", list(METODOLOGIA.keys()))
        up = st.file_uploader("Upload de evidência")
        if st.button("Salvar Anexo"):
            if up:
                path = f"evidencias_audit/{proj.id}_{f_ev}_{up.name}"
                with open(path, "wb") as f: f.write(up.getbuffer())
                session.add(Evidencia(projeto_id=proj.id, fase=f_ev, nome_arquivo=up.name, caminho=path))
                session.commit(); st.success("Anexado!")

# --- INTERFACE ---
st.set_page_config(page_title="Hub de Inteligência MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='color: #143264;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    # [Campos de input originais mantidos aqui...]
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Nome do Projeto")
    oportunidade = c2.text_input("CRM")
    gp_p = c3.text_input("Gerente")

    fases_lista = list(METODOLOGIA.keys())
    perc_fases = {}
    tabs = st.tabs(fases_lista)
    checks_ops = {}

    for i, fase in enumerate(fases_lista):
        with tabs[i]:
            if i > 0 and perc_fases.get(fases_lista[i-1], 0) < 100:
                st.error(f"🚨 FASE BLOQUEADA")
                perc_fases[fase] = 0.0
            else:
                concluidos = 0
                itens = METODOLOGIA[fase]
                cols = st.columns(2)
                for idx, item in enumerate(itens):
                    res = cols[idx % 2].checkbox(item, key=f"op_{fase}_{item}")
                    checks_ops[(fase, item)] = res
                    if res: concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100

    # SPARKLINE FIEL AO ORIGINAL
    st.markdown("<h3 style='font-size: 18px; color: #143264;'>🛤️ Linha do Tempo da Metodologia</h3>", unsafe_allow_html=True)
    st.markdown("""<style>.timeline-wrapper { position: relative; margin-bottom: 40px; padding-top: 10px; display: flex; justify-content: space-between; align-items: center; } .timeline-line { position: absolute; top: 38px; left: 5%; right: 5%; height: 3px; background-color: #143264; z-index: 1; } .pie-circle { width: 45px; height: 45px; border-radius: 50%; display: inline-block; position: relative; z-index: 2; background-color: white; }</style>""", unsafe_allow_html=True)
    st.markdown("<div class='timeline-wrapper'><div class='timeline-line'></div>", unsafe_allow_html=True)
    cols_v = st.columns(len(fases_lista))
    for i, fase in enumerate(fases_lista):
        v = perc_fases[fase]
        cor_borda = "#143264" if v > 0 else "#FFD700"
        with cols_v[i]:
            st.markdown(f"<div style='text-align: center;'><div class='pie-circle' style='background: conic-gradient(#143264 {v}%, #E0E0E0 0); border: 4px solid {cor_borda};'></div><p style='font-size: 11px; font-weight: bold;'>{fase}</p></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional="Sul", oportunidade=oportunidade, **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
        session.add(novo); session.flush()
        for (f, i), v in checks_ops.items(): session.add(StatusItem(projeto_id=novo.id, fase=f, item=i, entregue=1 if v else 0))
        session.commit(); st.success("Salvo!")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Dashboard de Governança</h2>", unsafe_allow_html=True)
    projs = session.query(Projeto).all()
    if projs:
        # Cálculo dinâmico para escala de progresso real
        df_list = []
        for p in projs:
            d = vars(p).copy()
            itens = session.query(StatusItem).filter(StatusItem.projeto_id == p.id).all()
            d['Progresso %'] = round((sum(1 for i in itens if i.entregue) / sum(len(v) for v in METODOLOGIA.values())) * 100, 1) if itens else 0.0
            df_list.append(d)
        df_display = pd.DataFrame(df_list).drop_duplicates(subset=['nome_projeto'])
        sel = st.dataframe(df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(format="%.1f%%")})
        if len(sel.selection.rows) > 0:
            popup_auditoria(int(df_display.iloc[sel.selection.rows[0]]['id']))
