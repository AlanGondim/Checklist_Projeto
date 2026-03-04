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

# --- POPUP DE AUDITORIA ---
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    
    # BUSCA INFORMAÇÃO JÁ EXISTENTE (Evita retrabalho)
    itens_salvos = session.query(StatusItem).filter(StatusItem.projeto_id == projeto_id).all()
    status_map = {(i.fase, i.item): bool(i.entregue) for i in itens_salvos}
    
    st.write(f"### Projeto: {proj.nome_projeto}")
    tab1, tab2, tab3 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico", "📂 Evidências"])
    
    with tab1:
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            # Se não houver itens detalhados no DB, usa o percentual da fase do projeto como fallback visual
            f_perc = (sum(1 for i in itens if status_map.get((fase, i), False)) / len(itens)) * 100
            
            with st.expander(f"{fase} - {f_perc:.0f}% Validado", expanded=(f_perc < 100)):
                if st.button(f"✅ Validar Conformidade Total: {fase}", key=f"aud_all_{fase}"):
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
            st.success("🌟 **PROJETO EM CONFORMIDADE INTEGRAL!**")
            st.balloons()
        
        st.divider()
        c1, c2 = st.columns(2)
        aud = c1.text_input("Analista Auditor MV", value=proj.responsavel_auditoria or "")
        data_aud = c2.date_input("Data da Auditoria", value=datetime.now(), format="DD/MM/YYYY")
        
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
                path = f"evidencias_audit/{proj.id}_{up.name}"
                with open(path, "wb") as f: f.write(up.getbuffer())
                session.add(Evidencia(projeto_id=proj.id, fase=f_ev, nome_arquivo=up.name, caminho=path))
                session.commit(); st.success("Arquivo Salvo!")

# --- INTERFACE ---
st.set_page_config(page_title="Hub de Inteligência MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='color: #143264;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    
    # --- ORGANIZAÇÃO DOS CAMPOS EM COLUNAS (3 POR COLUNA) ---
    with st.container():
        col1, col2, col3 = st.columns(3)
        
        # Linha 1
        nome_p = col1.text_input("Nome do Projeto")
        oportunidade = col2.text_input("Oportunidade (CRM)")
        gp_p = col3.text_input("Gerente do Projeto")
        
        # Linha 2
        regional_p = col1.selectbox("Regional", [" ", "Sul", "Sudeste", "Centro-Oeste", "Nordeste", "Norte", "Internacional"])
        horas_cont = col2.number_input("Horas Contratadas", min_value=0.0, step=10.0)
        d_inicio = col3.date_input("Data de Início", format="DD/MM/YYYY")
        
        # Linha 3
        d_termino = col1.date_input("Data de Término", format="DD/MM/YYYY")
        d_producao = col2.date_input("Data de Entrada em Produção", format="DD/MM/YYYY")
        d_auditoria_cad = col3.date_input("Data da Auditoria", format="DD/MM/YYYY")
        
        # Linha 4 (Campo restante centralizado ou na primeira coluna)
        resp_auditoria_cad = col1.text_input("Responsável pela Auditoria")

    fases_lista = list(METODOLOGIA.keys())
    perc_fases = {}
    
    st.markdown("---")
    tabs = st.tabs(fases_lista)
    checks_operacionais = {} # Para salvar o estado detalhado já no primeiro clique

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
        if nome_p and gp_p:
            novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional=regional_p, **{MAPA_COLUNAS[f]: v for f, v in perc_fases.items()})
            session.add(novo); session.flush()
            # SALVA O DETALHAMENTO IMEDIATAMENTE PARA O AUDITOR NÃO TER RETRABALHO
            for (f, i), v in checks_operacionais.items():
                session.add(StatusItem(projeto_id=novo.id, fase=f, item=i, entregue=1 if v else 0))
            session.commit(); st.success("Projeto e Checklist salvos!")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Dashboard de Governança</h2>", unsafe_allow_html=True)
    projs = session.query(Projeto).all()
    if projs:
        # Lógica de cálculo dinâmico para a escala de progresso do dashboard
        df_list = []
        for p in projs:
            d = vars(p).copy()
            itens = session.query(StatusItem).filter(StatusItem.projeto_id == p.id).all()
            if itens:
                d['Progresso %'] = round((sum(1 for i in itens if i.entregue) / sum(len(v) for v in METODOLOGIA.values())) * 100, 1)
            else:
                d['Progresso %'] = 0.0
            df_list.append(d)
            
        df = pd.DataFrame(df_list).drop_duplicates(subset=['nome_projeto'])
        df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
        
        selecao = st.dataframe(
            df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %', 'data_auditoria']], 
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%", color="#143264")}
        )
        if len(selecao.selection.rows) > 0:
            popup_auditoria(int(df_display.iloc[selecao.selection.rows[0]]['id']))












