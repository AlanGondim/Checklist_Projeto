import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date # Importação corrigida para evitar NameError
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

def analisar_fase_ideal(p):
    hoje = date.today()
    try:
        d_ini = datetime.strptime(p.data_inicio, '%Y-%m-%d').date()
        d_prod = datetime.strptime(p.data_entrada_producao, '%Y-%m-%d').date()
        d_fim = datetime.strptime(p.data_termino, '%Y-%m-%d').date()
        if hoje < d_ini: return "Pré-Início", ["TAP"]
        elif d_ini <= hoje < d_prod: return "Workshop/Construção", ["Business Blue Print", "Carga Precursora"]
        elif d_prod <= hoje < d_fim: return "Go Live/Operação Assistida", ["Ata de Go/No Go", "Termo de Aceite"]
        else: return "Finalização", ["TEP", "Lições Aprendidas"]
    except: return "Data N/D", []

def get_status_itens(projeto_id):
    itens = session.query(StatusItem).filter(StatusItem.projeto_id == projeto_id).all()
    return {(i.fase, i.item): bool(i.entregue) for i in itens}

# --- POPUP DE AUDITORIA ---
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    status_map = get_status_itens(proj.id)
    
    st.write(f"### Projeto: {proj.nome_projeto}")
    fase_sugerida, docs_obrigatorios = analisar_fase_ideal(proj)
    st.warning(f"🤖 **Análise de IA:** Fase Sugerida: **{fase_sugerida}**. Documentos Críticos: {', '.join(docs_obrigatorios)}.")

    tab1, tab2, tab3 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico", "📂 Evidências"])
    
    with tab1:
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            f_salvos = sum(1 for i in itens if status_map.get((fase, i), False))
            f_perc = (f_salvos / len(itens)) * 100
            
            with st.expander(f"{fase} - {f_perc:.0f}% Validado", expanded=(f_perc < 100)):
                # LINHA 82: Funcionalidade de marcar todos na Auditoria Técnica
                if st.button(f"✅ Marcar todos em {fase}", key=f"aud_all_{fase}"):
                    for item in itens:
                        session.merge(StatusItem(projeto_id=proj.id, fase=fase, item=item, entregue=1))
                    session.commit()
                    st.rerun()

                st.progress(f_perc / 100)
                for item in itens:
                    val_db = status_map.get((fase, item), False)
                    res = st.checkbox(item, value=val_db, key=f"aud_chk_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        
        p_medio = (total_e / total_i) * 100
        if p_medio == 100:
            st.success("🌟 **PROJETO EM CONFORMIDADE INTEGRAL!**"); st.balloons()
        
        st.divider()
        c1, c2 = st.columns(2)
        aud = c1.text_input("Analista Auditor MV", value=proj.responsavel_auditoria or "")
        data_aud = c2.date_input("Data da Auditoria", value=date.today(), format="DD/MM/YYYY")
        
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
        up = st.file_uploader("Anexar Evidência", key="up_audit")
        if st.button("Salvar Arquivo"):
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
        col1, col2, col3 = st.columns(3)
        nome_p = col1.text_input("Nome do Projeto")
        oportunidade = col2.text_input("Oportunidade (CRM)")
        gp_p = col3.text_input("Gerente do Projeto")
        col4, col5, col6 = st.columns(3)
        regional_p = col4.selectbox("Regional", [" ", "Sul", "Sudeste", "Centro-Oeste", "Nordeste", "Norte", "Internacional"])
        horas_cont = col5.number_input("Horas Contratadas", min_value=0.0, step=10.0)
        d_inicio = col6.date_input("Data de Início", format="DD/MM/YYYY")
        col7, col8, col9 = st.columns(3)
        d_termino = col7.date_input("Data de Término", format="DD/MM/YYYY")
        d_producao = col8.date_input("Data de Entrada em Produção", format="DD/MM/YYYY")
        d_auditoria_cad = col9.date_input("Data da Auditoria", format="DD/MM/YYYY")
        resp_auditoria_cad = st.text_input("Responsável pela Auditoria")

    fases_lista = list(METODOLOGIA.keys())
    perc_fases = {}; checks_operacionais = {}
    st.markdown("---")
    tabs = st.tabs(fases_lista)

    for i, fase in enumerate(fases_lista):
        with tabs[i]:
            if i > 0 and perc_fases.get(fases_lista[i-1], 0) < 100:
                st.error(f"🚨 FASE BLOQUEADA: Conclua 100% da fase anterior.")
                perc_fases[fase] = 0.0
            else:
                if st.button(f"⚡ Marcar todos: {fase}", key=f"btn_op_{fase}"):
                    for item in METODOLOGIA[fase]: st.session_state[f"chk_op_{fase}_{item}"] = True
                    st.rerun()
                
                concluidos = 0
                itens = METODOLOGIA[fase]
                cols = st.columns(2)
                for idx, item in enumerate(itens):
                    res = cols[idx % 2].checkbox(item, key=f"chk_op_{fase}_{item}")
                    checks_operacionais[(fase, item)] = res
                    if res: concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100

    st.markdown("<h3 style='font-size: 18px; color: #143264;'>🛤️ Linha do Tempo da Metodologia</h3>", unsafe_allow_html=True)
    st.markdown("""<style>.timeline-wrapper { position: relative; margin-bottom: 40px; padding-top: 10px; display: flex; justify-content: space-between; align-items: center; } .timeline-line { position: absolute; top: 38px; left: 5%; right: 5%; height: 3px; background-color: #143264; z-index: 1; } .pie-circle { width: 45px; height: 45px; border-radius: 50%; display: inline-block; position: relative; z-index: 2; background-color: white; }</style>""", unsafe_allow_html=True)
    st.markdown("<div class='timeline-wrapper'><div class='timeline-line'></div>", unsafe_allow_html=True)
    cols_visual = st.columns(len(fases_lista))
    for i, fase in enumerate(fases_lista):
        valor = perc_fases[fase]
        cor_borda = "#143264" if valor > 0 else "#FFD700"
        with cols_visual[i]:
            st.markdown(f"<div style='text-align: center; position: relative; z-index: 2;'><div class='pie-circle' style='background: conic-gradient(#143264 {valor}%, #E0E0E0 0); border: 4px solid {cor_borda};'></div><p style='font-size: 11px; font-weight: bold; color: #143264; margin-top: 5px;'>{fase}</p><p style='font-size: 13px; color: #143264;'>{valor:.0f}%</p></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        if nome_p and gp_p:
            novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional=regional_p, oportunidade=oportunidade, data_inicio=str(d_inicio), data_entrada_producao=str(d_producao), data_termino=str(d_termino), responsavel_auditoria=resp_auditoria_cad, **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
            session.add(novo); session.flush()
            for (f, i), v in checks_operacionais.items():
                session.add(StatusItem(projeto_id=novo.id, fase=f, item=i, entregue=1 if v else 0))
            session.commit(); st.success("Dossiê salvo!"); st.rerun()

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Dashboard de Governança</h2>", unsafe_allow_html=True)
    projs = session.query(Projeto).all()
    if projs:
        df_list = []
        for p in projs:
            d = vars(p).copy()
            itens = session.query(StatusItem).filter(StatusItem.projeto_id == p.id).all()
            total_m = sum(len(v) for v in METODOLOGIA.values())
            entregues = sum(1 for i in itens if i.entregue)
            valor_v = (entregues / total_m) * 100 if total_m > 0 else 0.0
            d['Progresso %'] = round(valor_v, 1)
            hoje = date.today()
            try:
                d_fim = datetime.strptime(p.data_termino, '%Y-%m-%d').date()
                if valor_v >= 100: d['Farol'] = "🟢 Conforme"
                elif valor_v < 100 and hoje > d_fim: d['Farol'] = "🔴 Crítico (Atraso)"
                else: d['Farol'] = "🟡 Em Andamento"
            except: d['Farol'] = "⚪ Sem Data"
            d['cor_prog'] = "red" if valor_v <= 50 else "#FFD700" if valor_v <= 75 else "#143264"
            df_list.append(d)
        
        df_display = pd.DataFrame(df_list).drop_duplicates(subset=['nome_projeto']).rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
        selecao = st.dataframe(df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %', 'Farol', 'cor_prog']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", column_config={"id": None, "cor_prog": None, "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%", color="cor_prog"), "Farol": st.column_config.TextColumn("Conformidade (Farol)")})
        if len(selecao.selection.rows) > 0:
            popup_auditoria(int(df_display.iloc[selecao.selection.rows[0]]['id']))
