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

Base.metadata.create_all(engine)

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

# --- POPUP DE AUDITORIA (DASHBOARD REGIONAL) ---
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    st.write(f"## Auditoria Técnica: {proj.nome_projeto}")
    status_db = get_status_itens(proj.id)
    
    t1, t2, t3 = st.tabs(["🔍 Auditoria Técnica (Gaps)", "📜 Histórico", "📂 Evidências"])
    
    with t1:
        st.info("Artefatos validados em auditorias anteriores aparecem com ✅.")
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            entregues_count = sum(1 for i in itens if status_db.get((fase, i), False))
            perc = (entregues_count / len(itens)) * 100
            with st.expander(f"{fase} - {perc:.0f}% Entregue", expanded=(perc < 100)):
                st.progress(perc / 100)
                for item in itens:
                    val_anterior = status_db.get((fase, item), False)
                    res = st.checkbox(item, value=val_anterior, key=f"aud_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        
        st.divider()
        c1, c2 = st.columns(2)
        auditor = c1.text_input("Analista Auditor MV", value=proj.responsavel_auditoria or "")
        data_aud = c2.date_input("Data da Auditoria", value=datetime.now())
        
        if st.button("🚀 CONSOLIDAR AUDITORIA", use_container_width=True):
            session.query(StatusItem).filter(StatusItem.projeto_id == proj.id).delete()
            for (f, i), v in novos_status.items():
                session.add(StatusItem(projeto_id=proj.id, fase=f, item=i, entregue=1 if v else 0))
            for fase in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[fase] if novos_status.get((fase, it)))
                setattr(proj, MAPA_COLUNAS[f], (count / len(METODOLOGIA[fase])) * 100)
            proj.responsavel_auditoria = auditor
            p_medio = (total_e / total_i) * 100
            session.add(AuditoriaHistorico(projeto_id=proj.id, data_auditoria=str(data_aud), responsavel=auditor, progresso_total=p_medio))
            session.commit(); st.success("Auditoria Consolidada!"); st.rerun()

    with t2:
        hist = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == proj.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if hist:
            df_hist = pd.DataFrame([{"Data": h.data_auditoria, "Auditor": h.responsavel, "Performance": f"{h.progresso_total:.1f}%"} for h in hist])
            st.table(df_hist)
        else: st.info("Sem histórico registrado.")

    with t3:
        st.write("### 📎 Depósito de Evidências (Prints/PDFs)")
        f_ev = st.selectbox("Fase:", list(METODOLOGIA.keys()))
        up = st.file_uploader("Upload de evidências", key="up_audit")
        if st.button("Salvar Arquivo"):
            if up:
                path = f"evidencias_audit/{proj.id}_{f_ev}_{up.name}"
                with open(path, "wb") as f: f.write(up.getbuffer())
                session.add(Evidencia(projeto_id=proj.id, fase=f_ev, nome_arquivo=up.name, caminho=path))
                session.commit(); st.success("Evidência arquivada!")
        st.divider()
        evs = session.query(Evidencia).filter(Evidencia.projeto_id == proj.id).all()
        for ev in evs:
            with st.expander(f"📄 {ev.fase}: {ev.nome_arquivo}"):
                if ev.nome_arquivo.lower().endswith(('png', 'jpg', 'jpeg')): st.image(ev.caminho)
                with open(ev.caminho, "rb") as f: st.download_button("Baixar", f, file_name=ev.nome_arquivo, key=f"dl_{ev.id}")

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
            # REGRA DE NEGÓCIO ORIGINAL: BLOQUEIO POR FASE PENDENTE
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

    # SPARKLINE ORIGINAL PRESERVADO
    
    st.markdown("<h3 style='font-size: 18px; color: #143264;'>🛤️ Linha do Tempo da Metodologia</h3>", unsafe_allow_html=True)
    st.markdown("""
        <style>
        .timeline-wrapper { position: relative; margin-bottom: 40px; padding-top: 10px; }
        .timeline-line { position: absolute; top: 38px; left: 5%; right: 5%; height: 3px; background-color: #143264; z-index: 1; }
        .pie-circle { width: 45px; height: 45px; border-radius: 50%; display: inline-block; position: relative; z-index: 2; background-color: white; border: 3px solid #143264; }
        </style>
    """, unsafe_allow_html=True)
    
    cols_visual = st.columns(len(fases_lista))
    for i, fase in enumerate(fases_lista):
        valor = perc_fases[fase]
        with cols_visual[i]:
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div class='pie-circle' style='background: conic-gradient(#143264 {valor}%, #E0E0E0 0);'></div>
                    <p style='font-size: 11px; font-weight: bold;'>{fase}</p>
                    <p style='font-size: 14px;'>{valor:.0f}%</p>
                </div>
            """, unsafe_allow_html=True)

    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        if nome_p and gp_p:
            novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional=reg_p, oportunidade=oportunidade,
                           data_inicio=str(d_inicio), data_termino=str(d_termino), **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
            session.add(novo); session.commit(); st.success("Salvo!")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Dashboard Regional</h2>", unsafe_allow_html=True)
    query = session.query(Projeto).order_by(desc(Projeto.timestamp)).all()
    if query:
        df = pd.DataFrame([vars(p) for p in query]).drop_duplicates(subset=['nome_projeto'])
        df['Progresso %'] = df[list(MAPA_COLUNAS.values())].mean(axis=1).round(1)
        
        # Filtros de Dashboard
        f_gp = st.sidebar.multiselect("Gerente", sorted(df['gerente_projeto'].unique()))
        if f_gp: df = df[df['gerente_projeto'].isin(f_gp)]

        st.info("💡 Clique em uma linha da tabela abaixo para gerenciar Gaps, Histórico e Provas Documentais.")
        
        df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
        selecao = st.dataframe(
            df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %', 'data_auditoria']],
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")}
        )

        if len(selecao.selection.rows) > 0:
            popup_auditoria(int(df_display.iloc[selecao.selection.rows[0]]['id']))
