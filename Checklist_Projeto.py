import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
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

# Diretório para evidências físicas
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
    inicializacao = Column(Float); planejamento = Column(Float)
    workshop_de_processos = Column(Float); construcao = Column(Float)
    go_live = Column(Float); operacao_assistida = Column(Float)
    finalizacao = Column(Float)

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

# Criar tabelas se não existirem
Base.metadata.create_all(engine)

# --- BLOCO DE MIGRAÇÃO AUTOMÁTICA (Resolve o OperationalError) ---
def realizar_migracao():
    inspector = inspect(engine)
    colunas = [c['name'] for c in inspector.get_columns('historico_auditorias')]
    
    with engine.connect() as conn:
        if 'responsavel' not in colunas:
            conn.execute(text("ALTER TABLE historico_auditorias ADD COLUMN responsavel TEXT"))
        if 'progresso_total' not in colunas:
            conn.execute(text("ALTER TABLE historico_auditorias ADD COLUMN progresso_total FLOAT"))
        conn.commit()

realizar_migracao()

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
    st.write(f"### Projeto: {proj.nome_projeto}")
    
    status_db = get_status_itens(proj.id)
    t1, t2, t3 = st.tabs(["🔍 Auditoria Técnica (Gaps)", "📜 Histórico", "📂 Evidências"])
    
    with t1:
        st.info("Artefatos com ✅ foram validados. Itens desmarcados são pendências.")
        novos_status = {}
        total_e = 0; total_i = 0
        
        for fase, itens in METODOLOGIA.items():
            f_concluidos = sum(1 for i in itens if status_db.get((fase, i), False))
            f_perc = (f_concluidos / len(itens)) * 100
            
            with st.expander(f"{fase} - {f_perc:.0f}% Concluído"):
                st.progress(f_perc / 100)
                for item in itens:
                    val_previo = status_db.get((fase, item), False)
                    res = st.checkbox(item, value=val_previo, key=f"aud_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        
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
            p_medio = (total_e / total_i) * 100
            session.add(AuditoriaHistorico(projeto_id=proj.id, data_auditoria=str(datetime.now().date()), responsavel=aud, progresso_total=p_medio))
            session.commit()
            st.success("Auditoria Consolidada!"); st.rerun()

    with t2:
        st.write("### Linha do Tempo de Performance")
        hist = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == proj.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if hist:
            df_hist = pd.DataFrame([{"Data": h.data_auditoria, "Auditor": h.responsavel, "Performance": f"{h.progresso_total:.1f}%"} for h in hist])
            st.table(df_hist)
        else: st.info("Sem histórico.")

    with t3:
        st.write("### 📎 Depósito de Evidências")
        f_ev = st.selectbox("Fase:", list(METODOLOGIA.keys()))
        up = st.file_uploader("Upload", key="up_audit")
        if st.button("Salvar Arquivo"):
            if up:
                path = f"evidencias_audit/{proj.id}_{f_ev}_{up.name}"
                with open(path, "wb") as f: f.write(up.getbuffer())
                session.add(Evidencia(projeto_id=proj.id, fase=f_ev, nome_arquivo=up.name, caminho=path))
                session.commit(); st.success("Salvo!")
        st.divider()
        evs = session.query(Evidencia).filter(Evidencia.projeto_id == proj.id).all()
        for ev in evs:
            with st.expander(f"📄 {ev.fase}: {ev.nome_arquivo}"):
                if ev.nome_arquivo.lower().endswith(('png', 'jpg', 'jpeg')): st.image(ev.caminho)
                with open(ev.caminho, "rb") as f: st.download_button("Baixar", f, file_name=ev.nome_arquivo, key=f"dl_{ev.id}")

# --- INTERFACE ---
st.set_page_config(page_title="Hub MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.header("🏛️ Operação")
    # Lógica de cadastro simplificada
    with st.container():
        n_p = st.text_input("Nome Projeto")
        g_p = st.text_input("Gerente")
        if st.button("💾 SALVAR NO HUB"):
            novo = Projeto(nome_projeto=n_p, gerente_projeto=g_p)
            session.add(novo); session.commit(); st.success("Salvo!")

elif modo == "Dashboard Regional":
    st.header("📊 Dashboard Regional")
    projs = session.query(Projeto).all()
    if projs:
        df = pd.DataFrame([vars(p) for p in projs]).drop_duplicates(subset=['nome_projeto'])
        df['Progresso %'] = df[list(MAPA_COLUNAS.values())].mean(axis=1).round(1)
        df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
        
        sel = st.dataframe(df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %']], 
                           use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
                           column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")})
        
        if len(sel.selection.rows) > 0:
            idx = sel.selection.rows[0]
            popup_auditoria(int(df_display.iloc[idx]['id']))
