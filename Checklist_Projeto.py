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

def format_date_br(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        return date_str

def analisar_status_ia(proj):
    hoje = date.today()
    try:
        d_ini = datetime.strptime(proj.data_inicio, '%Y-%m-%d').date()
        d_prod = datetime.strptime(proj.data_entrada_producao, '%Y-%m-%d').date()
        d_ter = datetime.strptime(proj.data_termino, '%Y-%m-%d').date()
        if hoje < d_ini: return "Inicialização", ["TAP", "Proposta"]
        elif d_ini <= hoje < d_prod: return "Workshop / Construção", ["Blueprint", "Carga Precursora"]
        elif d_prod <= hoje < d_ter: return "Go Live / Operação Assistida", ["Ata Go/No Go", "Termo Aceite"]
        else: return "Finalização", ["TEP", "Lições Aprendidas"]
    except: return "Datas Pendentes", ["Cronograma"]

@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    itens_db = session.query(StatusItem).filter(StatusItem.projeto_id == projeto_id).all()
    status_map = {(i.fase, i.item): bool(i.entregue) for i in itens_db}
    
    st.markdown(f"### 📑 Dossiê do Projeto: {proj.nome_projeto}")
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**CRM:** {proj.oportunidade}")
        c2.write(f"**Gerente:** {proj.gerente_projeto}")
        c3.write(f"**Regional:** {proj.regional}")
        c4, c5, c6 = st.columns(3)
        c4.write(f"**Horas:** {proj.horas_contratadas}h")
        c5.write(f"**Início:** {format_date_br(proj.data_inicio)}")
        c6.write(f"**Término:** {format_date_br(proj.data_termino)}")
        c7, c8, c9 = st.columns(3)
        c7.write(f"**Produção:** {format_date_br(proj.data_entrada_producao)}")
        c8.write(f"**Status IA:** {analisar_status_ia(proj)[0]}")

    tab1, tab2 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico"])
    
    with tab1:
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            f_salvos = sum(1 for i in itens if status_map.get((fase, i), False))
            f_perc = (f_salvos / len(itens)) * 100
            
            with st.expander(f"{fase} - {f_perc:.0f}% Validado", expanded=(f_perc < 100)):
                # LÓGICA CORRIGIDA: BOTÃO MARCAR/DESMARCAR AUDITORIA
                col_btn, _ = st.columns([1, 2])
                label_btn = "❌ Desmarcar todos" if f_perc == 100 else "✅ Marcar todos"
                if col_btn.button(label_btn, key=f"aud_btn_{fase}"):
                    val_to_set = 0 if f_perc == 100 else 1
                    # Remove anteriores e insere novos estados para garantir sincronia
                    session.query(StatusItem).filter(StatusItem.projeto_id == proj.id, StatusItem.fase == fase).delete()
                    for item in itens:
                        session.add(StatusItem(projeto_id=proj.id, fase=fase, item=item, entregue=val_to_set))
                    session.commit()
                    st.rerun()

                st.progress(f_perc / 100)
                for item in itens:
                    val_db = status_map.get((fase, item), False)
                    res = st.checkbox(item, value=val_db, key=f"aud_chk_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        
        st.divider()
        if st.button("🚀 CONSOLIDAR AUDITORIA", use_container_width=True):
            session.query(StatusItem).filter(StatusItem.projeto_id == proj.id).delete()
            for (f, i), v in novos_status.items():
                session.add(StatusItem(projeto_id=proj.id, fase=f, item=i, entregue=1 if v else 0))
            for f in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[f] if novos_status.get((f, it)))
                setattr(proj, MAPA_COLUNAS[f], (count / len(METODOLOGIA[f])) * 100)
            proj.data_auditoria = str(date.today())
            session.commit(); st.success("Dossiê atualizado!"); st.rerun()

    with tab2:
        hist = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == proj.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if hist: st.table(pd.DataFrame([{"Data": h.data_auditoria, "Auditor": h.responsavel, "Performance": f"{h.progresso_total:.1f}%"} for h in hist]))

# --- INTERFACE PRINCIPAL ---
st.set_page_config(page_title="Hub MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='color: #143264;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns(3)
        nome_p = col1.text_input("Nome do Projeto")
        oportunidade = col2.text_input("CRM")
        gp_p = col3.text_input("Gerente")
        reg_p = col1.selectbox("Regional", [" ", "Sul", "Sudeste", "Centro-Oeste", "Nordeste", "Norte", "Internacional"])
        horas_cont = col2.number_input("Horas Contratadas", min_value=0.0)
        d_inicio = col3.date_input("Data de Início", format="DD/MM/YYYY")
        d_termino = col1.date_input("Data de Término", format="DD/MM/YYYY")
        d_producao = col2.date_input("Data de Entrada em Produção", format="DD/MM/YYYY")

    fases_lista = list(METODOLOGIA.keys()); perc_fases = {}; checks_ops = {}
    tabs = st.tabs(fases_lista)
    for i, fase in enumerate(fases_lista):
        with tabs[i]:
            if i > 0 and perc_fases.get(fases_lista[i-1], 0) < 100:
                st.error("Fase Bloqueada"); perc_fases[fase] = 0.0
            else:
                # LÓGICA MARCAR/DESMARCAR OPERACIONAL
                concluidos_at = sum(1 for it in METODOLOGIA[fase] if st.session_state.get(f"op_chk_{fase}_{it}", False))
                label_op = "❌ Desmarcar todos" if concluidos_at == len(METODOLOGIA[fase]) else "⚡ Marcar todos"
                if st.button(label_op, key=f"op_btn_{fase}"):
                    val_to_set = False if concluidos_at == len(METODOLOGIA[fase]) else True
                    for item in METODOLOGIA[fase]: st.session_state[f"op_chk_{fase}_{item}"] = val_to_set
                    st.rerun()
                
                concluidos = 0; itens = METODOLOGIA[fase]; cols = st.columns(2)
                for item in itens:
                    res = cols[itens.index(item)%2].checkbox(item, key=f"op_chk_{fase}_{item}")
                    checks_ops[(fase, item)] = res
                    if res: concluidos += 1
                perc_fases[fase] = (concluidos / len(itens)) * 100

   # --- SPARKLINE COMPLETO (Com linha e borda condicional) ---
    st.markdown("<h3 style='font-size: 18px; color: #143264;'>🛤️ Linha do Tempo da Metodologia</h3>", unsafe_allow_html=True)
    st.markdown("""
        <style>
        .timeline-wrapper { position: relative; margin-bottom: 40px; padding-top: 10px; display: flex; justify-content: space-between; align-items: center; }
        .timeline-line { position: absolute; top: 38px; left: 5%; right: 5%; height: 3px; background-color: #143264; z-index: 1; }
        .pie-circle { 
            width: 45px; height: 45px; border-radius: 50%; display: inline-block; 
            position: relative; z-index: 2; background-color: white; 
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='timeline-wrapper'>", unsafe_allow_html=True)
    st.markdown("<div class='timeline-line'></div>", unsafe_allow_html=True)
    cols_visual = st.columns(len(fases_lista))
    for i, fase in enumerate(fases_lista):
        valor = perc_fases[fase]
        # Borda: Azul marinho se preenchido, Amarela se vazio
        cor_borda = "#143264" if valor > 0 else "#FFD700"
        with cols_visual[i]:
            st.markdown(f"""
                <div style='text-align: center; position: relative; z-index: 2;'>
                    <div class='pie-circle' style='background: conic-gradient(#143264 {valor}%, #E0E0E0 0); border: 4px solid {cor_borda};'></div>
                    <p style='font-size: 11px; font-weight: bold; color: #143264; margin-top: 5px;'>{fase}</p>
                    <p style='font-size: 13px; color: #143264;'>{valor:.0f}%</p>
                </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("💾 SALVAR NO HUB", use_container_width=True):
        novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional=reg_p, oportunidade=oportunidade, data_inicio=str(d_inicio), data_termino=str(d_termino), data_entrada_producao=str(d_producao), **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
        session.add(novo); session.flush()
        for (f, i), v in checks_ops.items(): session.add(StatusItem(projeto_id=novo.id, fase=f, item=i, entregue=1 if v else 0))
        session.commit(); st.success("Salvo!"); st.rerun()

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
            try:
                d_fim = datetime.strptime(p.data_termino, '%Y-%m-%d').date()
                d['Farol'] = "🟢 Conforme" if v_perc >= 100 else "🔴 Crítico" if date.today() > d_fim else "🟡 No Prazo"
            except: d['Farol'] = "⚪ N/D"
            df_list.append(d)
        df_display = pd.DataFrame(df_list).drop_duplicates(subset=['nome_projeto'])
        sel = st.dataframe(df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %', 'Farol']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(format="%.1f%%", color="#143264")})
        if len(sel.selection.rows) > 0: popup_auditoria(int(df_display.iloc[sel.selection.rows[0]]['id']))



