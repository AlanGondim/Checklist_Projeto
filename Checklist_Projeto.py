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
    session.expire_all()
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    status_db = get_status_itens(proj.id)
    
    st.write(f"### Projeto: {proj.nome_projeto}")
    
    t1, t2, t3 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico", "📂 Evidências"])
    
    with t1:
        novos_status = {}; total_e = 0; total_i = 0
        for fase, itens in METODOLOGIA.items():
            f_concluidos = sum(1 for i in itens if status_db.get((fase, i), False))
            f_perc = (f_concluidos / len(itens)) * 100
            
            with st.expander(f"{fase} - {f_perc:.0f}% Concluído", expanded=(f_perc < 100)):
                st.progress(f_perc / 100)
                for item in itens:
                    val_previo = status_db.get((fase, item), False)
                    res = st.checkbox(item, value=val_previo, key=f"aud_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_e += 1
                    total_i += 1
        
        p_medio = (total_e / total_i) * 100
        
        # MENSAGEM ESPONTÂNEA DE CONFORMIDADE
        if p_medio == 100:
            st.success("🌟 **CONFORMIDADE INTEGRAL IDENTIFICADA!** Todos os artefatos da metodologia foram validados e o projeto está blindado juridicamente.")
            st.balloons()
        
        st.divider()
        c1, c2 = st.columns(2)
        aud = c1.text_input("Analista Auditor MV", value=proj.responsavel_auditoria or "")
        data_aud = c2.date_input("Data da Auditoria", value=datetime.now())
        
        if st.button("🚀 CONSOLIDAR AUDITORIA", use_container_width=True):
            session.query(StatusItem).filter(StatusItem.projeto_id == proj.id).delete()
            for (f, i), v in novos_status.items():
                session.add(StatusItem(projeto_id=proj.id, fase=f, item=i, entregue=1 if v else 0))
            
            # ATUALIZAÇÃO FORÇADA DAS COLUNAS DE FASE PARA O DASHBOARD
            for fase in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[fase] if novos_status.get((fase, it)))
                setattr(proj, MAPA_COLUNAS[f], (count / len(METODOLOGIA[fase])) * 100)
            
            proj.responsavel_auditoria = aud
            session.add(AuditoriaHistorico(projeto_id=proj.id, data_auditoria=str(data_aud), responsavel=aud, progresso_total=p_medio))
            session.commit()
            st.success("Auditoria Consolidada!"); st.rerun()

    with t2:
        hist = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == proj.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if hist:
            df_hist = pd.DataFrame([{"Data": h.data_auditoria, "Auditor": h.responsavel, "Performance": f"{h.progresso_total:.1f}%"} for h in hist])
            st.table(df_hist)
        else: st.info("Sem histórico.")

    with t3:
        # Lógica de evidências simplificada
        f_ev = st.selectbox("Fase:", list(METODOLOGIA.keys()))
        up = st.file_uploader("Upload", key="up_audit")
        if st.button("Salvar Arquivo"):
            if up:
                path = f"evidencias_audit/{proj.id}_{up.name}"
                with open(path, "wb") as f: f.write(up.getbuffer())
                session.add(Evidencia(projeto_id=proj.id, fase=f_ev, nome_arquivo=up.name, caminho=path))
                session.commit(); st.success("Salvo!")

# --- DASHBOARD REGIONAL ---
st.set_page_config(page_title="Hub MV PRO", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.header("🏛️ Operação de Projetos")
    nome_p = st.text_input("Nome do Projeto")
    gp_p = st.text_input("Gerente de Projeto")
    if st.button("💾 SALVAR NO HUB"):
        if nome_p and gp_p:
            novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p)
            session.add(novo); session.commit(); st.success("Registrado!")

elif modo == "Dashboard Regional":
    st.header("📊 Dashboard de Governança Regional")
    projs = session.query(Projeto).all()
    
    if projs:
        data = []
        for p in projs:
            p_dict = vars(p)
            # CALCULO EM TEMPO REAL BASEADO NA AUDITORIA TÉCNICA (ITENS DETALHADOS)
            status_itens = get_status_itens(p.id)
            if status_itens:
                total_itens = sum(len(v) for v in METODOLOGIA.values())
                concluidos = sum(1 for v in status_itens.values() if v)
                progresso_real = (concluidos / total_itens) * 100
            else:
                # Fallback para média das fases reportadas se não houver auditoria técnica
                progresso_real = np.mean([p.inicializacao, p.planejamento, p.workshop_de_processos, p.construcao, p.go_live, p.operacao_assistida, p.finalizacao])
            
            p_dict['Progresso %'] = round(progresso_real, 1)
            data.append(p_dict)
            
        df = pd.DataFrame(data).drop_duplicates(subset=['nome_projeto'])
        df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
        
        st.info("💡 **Dica:** O Progresso % agora reflete a validação real dos artefatos auditados.")
        
        sel = st.dataframe(
            df_display[['id', 'nome_projeto', 'gerente_projeto', 'Progresso %', 'data_auditoria']], 
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={
                "id": None, 
                "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")
            }
        )
        
        if len(sel.selection.rows) > 0:
            idx = sel.selection.rows[0]
            popup_auditoria(int(df_display.iloc[idx]['id']))
