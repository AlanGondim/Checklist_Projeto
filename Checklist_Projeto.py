import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
import os

# --- DATABASE SETUP ---
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia_executivo.db'
engine = create_engine(DB_NAME, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
session = Session()

if not os.path.exists("evidencias_audit"):
    os.makedirs("evidencias_audit")

class Projeto(Base):
    __tablename__ = 'monitoramento_projetos'
    id = Column(Integer, primary_key=True)
    nome_projeto = Column(String); gerente_projeto = Column(String)
    regional = Column(String); oportunidade = Column(String)
    horas_contratadas = Column(Float)
    data_inicio = Column(String); data_termino = Column(String)
    data_entrada_producao = Column(String); data_auditoria = Column(String)
    responsavel_auditoria = Column(String); timestamp = Column(DateTime, default=datetime.now)
    inicializacao = Column(Float, default=0.0); planejamento = Column(Float, default=0.0)
    workshop_de_processos = Column(Float, default=0.0); construcao = Column(Float, default=0.0)
    go_live = Column(Float, default=0.0); operacao_assistida = Column(Float, default=0.0)
    finalizacao = Column(Float, default=0.0)

class StatusItem(Base):
    __tablename__ = 'status_itens_detalhado'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    item = Column(String); entregue = Column(Integer)

class AuditoriaHistorico(Base):
    __tablename__ = 'historico_auditorias'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); data_auditoria = Column(String)
    responsavel = Column(String); progresso_total = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)

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
        if hoje < d_ini: return "Inicialização", ["Proposta", "TAP"]
        elif d_ini <= hoje < d_prod: return "Workshop/Construção", ["Blueprint", "Homologação"]
        elif d_prod <= hoje <= d_fim: return "Go Live/Operação", ["Ata Go/No Go", "Termo Aceite"]
        else: return "Finalização", ["TEP", "Lições Aprendidas"]
    except: return "Planejamento", ["Cronograma"]

@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    itens_salvos = session.query(StatusItem).filter(StatusItem.projeto_id == projeto_id).all()
    status_map = {(i.fase, i.item): bool(i.entregue) for i in itens_salvos}
    
    fase_sugerida, docs_criticos = analisar_fase_ideal(proj)
    st.info(f"🤖 **Insight IA:** O projeto deveria estar em **{fase_sugerida}**. Verifique: {', '.join(docs_criticos)}.")

    tab1, tab2 = st.tabs(["Auditoria Técnica", "Histórico"])
    with tab1:
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            f_perc = (sum(1 for i in itens if status_map.get((fase, i), False)) / len(itens)) * 100
            with st.expander(f"{fase} - {f_perc:.0f}%", expanded=(f_perc < 100)):
                if st.button(f"✅ Validar Tudo: {fase}", key=f"aud_all_{fase}"):
                    for item in itens: session.merge(StatusItem(projeto_id=proj.id, fase=fase, item=item, entregue=1))
                    session.commit(); st.rerun()
                
                for item in itens:
                    v = status_map.get((fase, item), False)
                    res = st.checkbox(item, value=v, key=f"chk_aud_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        
        if st.button("🚀 CONSOLIDAR AUDITORIA", use_container_width=True):
            session.query(StatusItem).filter(StatusItem.projeto_id == proj.id).delete()
            for (f, i), v in novos_status.items(): session.add(StatusItem(projeto_id=proj.id, fase=f, item=i, entregue=1 if v else 0))
            for f in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[f] if novos_status.get((f, it)))
                setattr(proj, MAPA_COLUNAS[f], (count / len(METODOLOGIA[f])) * 100)
            proj.data_auditoria = str(date.today())
            session.commit(); st.success("Auditado!"); st.rerun()

st.set_page_config(page_title="Hub MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("## 🏛️ Hub de Inteligência | Operação")
    c1, c2, c3 = st.columns(3)
    nome_p = c1.text_input("Nome do Projeto"); oportunidade = c2.text_input("Oportunidade (CRM)"); gp_p = c3.text_input("Gerente")
    reg_p = c1.selectbox("Regional", ["Sul", "Sudeste", "Centro-Oeste", "Nordeste", "Norte", "Internacional"])
    horas = c2.number_input("Horas", min_value=0.0); d_ini = c3.date_input("Início", format="DD/MM/YYYY")
    d_ter = c1.date_input("Término", format="DD/MM/YYYY"); d_ent = c2.date_input("Produção", format="DD/MM/YYYY")

    fases_lista = list(METODOLOGIA.keys()); perc_fases = {}; checks_ops = {}
    tabs = st.tabs(fases_lista)
    for i, fase in enumerate(fases_lista):
        with tabs[i]:
            if i > 0 and perc_fases.get(fases_lista[i-1], 0) < 100: st.error("Fase Bloqueada"); perc_fases[fase] = 0.0
            else:
                if st.button(f"⚡ Marcar todos: {fase}", key=f"op_all_{fase}"):
                    for item in METODOLOGIA[fase]: st.session_state[f"chk_op_{fase}_{item}"] = True
                    st.rerun()
                concluidos = 0; itens = METODOLOGIA[fase]; cols = st.columns(2)
                for item in itens:
                    res = cols[itens.index(item)%2].checkbox(item, key=f"chk_op_{fase}_{item}")
                    checks_ops[(fase, item)] = res
                    if res: concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100

    # SPARKLINE ORIGINAL CONECTADO
    st.markdown("""<style>.timeline-wrapper { position: relative; display: flex; justify-content: space-between; align-items: center; margin: 40px 0; } .timeline-line { position: absolute; top: 22px; left: 5%; right: 5%; height: 3px; background-color: #143264; z-index: 1; } .pie-circle { width: 45px; height: 45px; border-radius: 50%; z-index: 2; position: relative; background: white; }</style>""", unsafe_allow_html=True)
    st.markdown("<div class='timeline-wrapper'><div class='timeline-line'></div>", unsafe_allow_html=True)
    cols_v = st.columns(len(fases_lista))
    for i, fase in enumerate(fases_lista):
        v = perc_fases[fase]
        cor = "#143264" if v > 0 else "#FFD700"
        with cols_v[i]: st.markdown(f"<div style='text-align:center'><div class='pie-circle' style='background: conic-gradient(#143264 {v}%, #eee 0); border: 4px solid {cor}'></div><p style='font-size:10px'>{fase}</p></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional=reg_p, oportunidade=oportunidade, data_inicio=str(d_ini), data_termino=str(d_ter), data_entrada_producao=str(d_ent), **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
        session.add(novo); session.flush()
        for (f, i), v in checks_ops.items(): session.add(StatusItem(projeto_id=novo.id, fase=f, item=i, entregue=1 if v else 0))
        session.commit(); st.success("Salvo!")

elif modo == "Dashboard Regional":
    st.markdown("## 📊 Dashboard de Governança")
    projs = session.query(Projeto).all()
    if projs:
        df_list = []
        for p in projs:
            d = vars(p).copy()
            itens = session.query(StatusItem).filter(StatusItem.projeto_id == p.id).all()
            total_m = sum(len(v) for v in METODOLOGIA.values())
            entregues = sum(1 for i in itens if i.entregue)
            v_perc = (entregues / total_m) * 100 if total_m > 0 else 0.0
            d['Progresso %'] = round(v_perc, 1)
            # LOGICA DO FAROL
            try:
                d_fim = datetime.strptime(p.data_termino, '%Y-%m-%d').date()
                if v_perc >= 100: d['Farol'] = "🟢 Conforme"
                elif date.today() > d_fim: d['Farol'] = "🔴 Crítico (Atraso)"
                else: d['Farol'] = "🟡 No Prazo"
            except: d['Farol'] = "⚪ N/D"
            df_list.append(d)
        
        df_display = pd.DataFrame(df_list).drop_duplicates(subset=['nome_projeto'])
        # CORREÇÃO: Removido 'color="cor_prog"' que causava o erro
        sel = st.dataframe(
            df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %', 'Farol']], 
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={
                "id": None, 
                "Progresso %": st.column_config.ProgressColumn(format="%.1f%%", color="#143264"), # Cor fixa para estabilidade
                "Farol": st.column_config.TextColumn("Status (Farol)")
            }
        )
        if len(sel.selection.rows) > 0: popup_auditoria(int(df_display.iloc[sel.selection.rows[0]]['id']))

