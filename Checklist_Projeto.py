import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc, text
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

class StatusItem(Base):
    __tablename__ = 'status_itens_detalhado'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    item = Column(String); entregue = Column(Integer)

Base.metadata.create_all(engine)

METODOLOGIA = {
    "Inicialização": ["Proposta Técnica", "Contrato assinado", "TAP", "DEP"],
    "Planejamento": ["Evidência de Kick Off", "Ata de Reunião", "Cronograma", "Plano de Projeto"],
    "Workshop de Processos": ["Análise de Gaps", "Business Blue Print", "Configuração", "Termo de Aceite"],
    "Construção": ["Plano de Cutover", "Lista de Presença", "Treinamento", "Homologação"],
    "Go Live": ["Carga Final", "Escala Apoio", "Testes Integrados", "Ata Go/No Go"],
    "Operação Assistida": ["Suporte In Loco", "Ata de Reunião", "Termo de Aceite"],
    "Finalização": ["Reunião de Encerramento", "TEP", "Lições Aprendidas"]
}

MAPA_COLUNAS = {
    "Inicialização": "inicializacao", "Planejamento": "planejamento", 
    "Workshop de Processos": "workshop_de_processos", "Construção": "construcao",
    "Go Live": "go_live", "Operação Assistida": "operacao_assistida", "Finalização": "finalizacao"
}

def calcular_status_ia(d_ini, d_prod, d_fim):
    try:
        hoje = date.today()
        ini = datetime.strptime(d_ini, '%Y-%m-%d').date()
        prod = datetime.strptime(d_prod, '%Y-%m-%d').date()
        fim = datetime.strptime(d_fim, '%Y-%m-%d').date()
        if hoje < ini: return "🔵 Planejamento"
        if hoje >= fim: return "✅ Finalizado"
        if hoje >= prod: return "🚀 Operação Assistida"
        return "⚙️ Em Implantação"
    except: return "⚪ Sem Dados"

@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    itens_salvos = session.query(StatusItem).filter(StatusItem.projeto_id == projeto_id).all()
    status_map = {(i.fase, i.item): bool(i.entregue) for i in itens_salvos}
    st.write(f"### Projeto: {proj.nome_projeto}")
    tab1, tab2 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico"])
    with tab1:
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            f_perc = (sum(1 for i in itens if status_map.get((fase, i), False)) / len(itens)) * 100
            with st.expander(f"{fase} - {f_perc:.0f}% Validado", expanded=(f_perc < 100)):
                if st.button(f"✅ Marcar Tudo: {fase}", key=f"aud_all_{fase}"):
                    for item in itens: session.merge(StatusItem(projeto_id=proj.id, fase=fase, item=item, entregue=1))
                    session.commit(); st.rerun()
                for item in itens:
                    val_db = status_map.get((fase, item), False)
                    res = st.checkbox(item, value=val_db, key=f"aud_chk_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        if st.button("🚀 CONSOLIDAR", use_container_width=True):
            session.query(StatusItem).filter(StatusItem.projeto_id == proj.id).delete()
            for (f, i), v in novos_status.items(): session.add(StatusItem(projeto_id=proj.id, fase=f, item=i, entregue=1 if v else 0))
            for f in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[f] if novos_status.get((f, it)))
                setattr(proj, MAPA_COLUNAS[f], (count / len(METODOLOGIA[f])) * 100)
            session.add(AuditoriaHistorico(projeto_id=proj.id, data_auditoria=str(date.today()), responsavel=proj.gerente_projeto, progresso_total=(total_e / total_i) * 100))
            session.commit(); st.success("Auditado!"); st.rerun()

# --- INTERFACE ---
st.set_page_config(page_title="Hub MV", layout="wide")

# CSS para Azul Marinho (#143264)
st.markdown("""
    <style>
    div[data-baseweb="calendar"] div[aria-selected="true"],
    div[data-baseweb="calendar"] div[data-highlighted="true"] {
        background-color: #143264 !important;
        color: white !important;
    }
    span[data-baseweb="tag"] {
        background-color: #143264 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='color: #143264;'>🏛️ Hub de Inteligência | Operação</h2>")
    with st.container():
        col1, col2, col3 = st.columns(3)
        nome_p = col1.text_input("Projeto")
        gp_p = col2.text_input("Gerente")
        reg_p = col3.selectbox("Regional", ["Sul", "Sudeste", "Centro-Oeste", "Nordeste", "Norte"])
        d_ini = col1.date_input("Início", format="DD/MM/YYYY")
        d_fim = col2.date_input("Término", format="DD/MM/YYYY")
        d_prd = col3.date_input("Produção", format="DD/MM/YYYY")

    fases_lista = list(METODOLOGIA.keys()); perc_fases = {}; checks_ops = {}
    tabs = st.tabs(fases_lista)
    for i, fase in enumerate(fases_lista):
        with tabs[i]:
            if i > 0 and perc_fases.get(fases_lista[i-1], 0) < 100: st.error("Fase Bloqueada")
            else:
                if st.button(f"⚡ Marcar todos: {fase}", key=f"btn_op_{fase}"):
                    for item in METODOLOGIA[fase]: st.session_state[f"chk_op_{fase}_{item}"] = True
                    st.rerun()
                concluidos = 0; itens = METODOLOGIA[fase]; cols = st.columns(2)
                for idx, item in enumerate(itens):
                    res = cols[idx % 2].checkbox(item, key=f"chk_op_{fase}_{item}")
                    checks_ops[(fase, item)] = res
                    if res: concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100

    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional=reg_p, data_inicio=str(d_ini), data_termino=str(d_fim), data_entrada_producao=str(d_prd), **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
        session.add(novo); session.flush()
        for (f, i), v in checks_ops.items(): session.add(StatusItem(projeto_id=novo.id, fase=f, item=i, entregue=1 if v else 0))
        session.commit(); st.success("Salvo!")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Dashboard de Governança</h2>")

    # --- LÓGICA DE FILTROS ---
    def reset_filters():
        st.session_state.d_range = [date.today().replace(day=1), date.today()]
        st.session_state.f_selected = []

    if 'd_range' not in st.session_state: reset_filters()

    with st.expander("🔍 Filtros de Consulta", expanded=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        # Filtro de data vinculado à key do session_state
        data_range_val = c1.date_input("Período", value=st.session_state.d_range, format="DD/MM/YYYY", key="d_range_input")
        # Filtro de fase vinculado à key do session_state
        fase_filtro_val = c2.multiselect("Filtrar Fase", list(METODOLOGIA.keys()), default=st.session_state.f_selected, key="f_selected_input")
        
        c3.markdown("<br>", unsafe_allow_html=True)
        # O botão agora limpa as chaves específicas usadas nos widgets
        if c3.button("Limpar Filtros", use_container_width=True):
            st.session_state.d_range_input = [date.today().replace(day=1), date.today()]
            st.session_state.f_selected_input = []
            st.rerun()

    projs = session.query(Projeto).all()
    if projs:
        df_list = []
        for p in projs:
            d = vars(p).copy()
            ultima_aud = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == p.id).order_by(desc(AuditoriaHistorico.timestamp)).first()
            d['data_raw'] = ultima_aud.data_auditoria if ultima_aud else "0000-00-00"
            d['data_auditoria'] = datetime.strptime(ultima_aud.data_auditoria, '%Y-%m-%d').strftime('%d/%m/%Y') if ultima_aud else "Não Auditado"
            itens = session.query(StatusItem).filter(StatusItem.projeto_id == p.id).all()
            d['Progresso %'] = round((sum(1 for i in itens if i.entregue) / sum(len(v) for v in METODOLOGIA.values())) * 100, 1) if itens else 0.0
            d['Status IA'] = calcular_status_ia(p.data_inicio, p.data_entrada_producao, p.data_termino)
            df_list.append(d)
        
        df = pd.DataFrame(df_list).drop_duplicates(subset=['nome_projeto'])
        
        # Aplicar filtros (Usando os valores atuais dos widgets)
        if len(data_range_val) == 2:
            df = df[(df['data_raw'] >= str(data_range_val[0])) & (df['data_raw'] <= str(data_range_val[1])) | (df['data_auditoria'] == "Não Auditado")]
        if fase_filtro_val:
            df = df[df['Status IA'].apply(lambda x: any(f in x for f in fase_filtro_val))]

        # --- CORREÇÃO DO SELECTION ---
        # Capturamos a seleção diretamente do retorno do dataframe
        selecao = st.dataframe(
            df[['id', 'nome_projeto', 'gerente_projeto', 'Status IA', 'Progresso %', 'data_auditoria']], 
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row", 
            column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(format="%.1f%%", color="#143264")}
        )
        
        # Apuração
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Projetos", len(df))
        m2.metric("Média Performance", f"{df['Progresso %'].mean():.1f}%" if not df.empty else "0%")
        m3.metric("Conformidade 100%", len(df[df['Progresso %'] == 100]))
        
        # Lógica de Popup corrigida (usando o objeto retornado pelo st.dataframe)
        if selecao.selection.rows:
            selected_index = selecao.selection.rows[0]
            popup_auditoria(int(df.iloc[selected_index]['id']))
