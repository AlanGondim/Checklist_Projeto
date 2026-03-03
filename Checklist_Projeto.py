import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc
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

# Garantir diretório de evidências
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
    projeto_id = Column(Integer)
    data_auditoria = Column(String)
    responsavel = Column(String) # Coluna que estava faltando no seu DB físico
    progresso_total = Column(Float)
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

# --- POPUP DE AUDITORIA CORRIGIDO ---
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def popup_auditoria(projeto_id):
    # Re-consulta para garantir sessão ativa
    proj = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    st.write(f"### Projeto: {proj.nome_projeto}")
    
    status_db = get_status_itens(proj.id)
    t1, t2, t3 = st.tabs(["🔍 Auditoria Técnica (Gaps)", "📜 Histórico", "📂 Evidências"])
    
    with t1:
        st.info("Artefatos validados aparecem com ✅. Itens desmarcados são pendências.")
        novos_status = {}
        total_entregue = 0
        total_itens = 0
        
        for fase, itens in METODOLOGIA.items():
            fase_concluidos = sum(1 for i in itens if status_db.get((fase, i), False))
            perc_fase = (fase_concluidos / len(itens)) * 100
            
            with st.expander(f"{fase} - {perc_fase:.0f}% Concluído", expanded=(perc_fase < 100)):
                st.progress(perc_fase / 100)
                for item in itens:
                    entregue_antes = status_db.get((fase, item), False)
                    res = st.checkbox(item, value=entregue_antes, key=f"aud_{proj.id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_entregue += 1
                    total_itens += 1
        
        st.divider()
        c1, c2 = st.columns(2)
        auditor = c1.text_input("Analista Auditor MV", value=proj.responsavel_auditoria if proj.responsavel_auditoria else "")
        data_aud = c2.date_input("Data da Auditoria", value=datetime.now())
        
        if st.button("🚀 CONSOLIDAR AUDITORIA", use_container_width=True):
            # 1. Salvar itens individuais
            session.query(StatusItem).filter(StatusItem.projeto_id == proj.id).delete()
            for (f, i), val in novos_status.items():
                session.add(StatusItem(projeto_id=proj.id, fase=f, item=i, entregue=1 if val else 0))
            
            # 2. Atualizar Projeto
            for fase in METODOLOGIA.keys():
                count = sum(1 for it in METODOLOGIA[fase] if novos_status.get((fase, it)))
                setattr(proj, MAPA_COLUNAS[fase], (count / len(METODOLOGIA[fase])) * 100)
            
            proj.data_auditoria = str(data_aud)
            proj.responsavel_auditoria = auditor
            
            # 3. Histórico (Rastreabilidade Jurídica)
            prog_total = (total_entregue / total_itens) * 100
            session.add(AuditoriaHistorico(projeto_id=proj.id, data_auditoria=str(data_aud), responsavel=auditor, progresso_total=prog_total))
            
            session.commit()
            st.success("Auditoria Consolidada!"); st.rerun()

    with t2:
        st.write("### Histórico de Snapshots")
        historico = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == proj.id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if historico:
            df_hist = pd.DataFrame([{
                "Data": h.data_auditoria,
                "Auditor": h.responsavel,
                "Performance": f"{h.progresso_total:.1f}%",
                "Hora Registro": h.timestamp.strftime("%H:%M")
            } for h in historico])
            st.table(df_h if 'df_h' in locals() else df_hist)
        else: st.info("Sem histórico registrado.")

    with t3:
        st.write("### 📎 Depósito de Evidências (Prints/PDFs)")
        f_ev = st.selectbox("Fase:", list(METODOLOGIA.keys()))
        up_file = st.file_uploader("Upload", key="up_file_audit")
        if st.button("Salvar Arquivo"):
            if up_file:
                path = os.path.join("evidencias_audit", f"{proj.id}_{f_ev}_{up_file.name}")
                with open(path, "wb") as f: f.write(up_file.getbuffer())
                session.add(Evidencia(projeto_id=proj.id, fase=f_ev, nome_arquivo=up_file.name, caminho=path))
                session.commit(); st.success("Evidência salva!")
        
        st.divider()
        evs = session.query(Evidencia).filter(Evidencia.projeto_id == proj.id).all()
        for ev in evs:
            with st.expander(f"📄 {ev.fase}: {ev.nome_arquivo}"):
                if ev.nome_arquivo.lower().endswith(('png', 'jpg', 'jpeg')):
                    st.image(ev.caminho)
                with open(ev.caminho, "rb") as f:
                    st.download_button("Baixar", f, file_name=ev.nome_arquivo, key=f"dl_{ev.id}")

# --- INTERFACE PRINCIPAL ---
st.set_page_config(page_title="Hub MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='color: #143264;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    # [Lógica de cadastro original]
    with st.container():
        c1, c2, c3 = st.columns(3)
        nome_p = c1.text_input("Projeto")
        gp_p = c2.text_input("Gerente")
        oportunidade = c3.text_input("CRM")
        if st.button("💾 SALVAR PROJETO"):
            if nome_p and gp_p:
                novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, oportunidade=oportunidade)
                session.add(novo); session.commit(); st.success("Salvo!")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Dashboard Regional</h2>", unsafe_allow_html=True)
    projs = session.query(Projeto).order_by(desc(Projeto.timestamp)).all()
    if projs:
        df = pd.DataFrame([vars(p) for p in projs]).drop_duplicates(subset=['nome_projeto'], keep='first')
        df['Progresso %'] = df[list(MAPA_COLUNAS.values())].mean(axis=1).round(1)
        
        df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
        col_v = ['id', 'nome_projeto', 'gerente_projeto', 'Progresso %', 'data_auditoria']
        
        st.info("💡 Clique em uma linha para abrir a Auditoria de Rastreabilidade.")
        selecao = st.dataframe(
            df_display[col_v],
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)}
        )

        if len(selecao["selection"]["rows"]) > 0:
            idx = selecao["selection"]["rows"][0]
            p_id = int(df_display.iloc[idx]['id'])
            popup_auditoria(p_id)
