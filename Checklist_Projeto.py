import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# --- DATABASE SETUP ---
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia_executivo.db'
engine = create_engine(DB_NAME)
Session = sessionmaker(bind=engine)
session = Session()

# Pasta física para anexos (Prints de e-mail, PDFs, etc)
if not os.path.exists("evidencias_projetos"):
    os.makedirs("evidencias_projetos")

class Projeto(Base):
    __tablename__ = 'monitoramento_projetos'
    id = Column(Integer, primary_key=True)
    nome_projeto = Column(String); gerente_projeto = Column(String)
    regional = Column(String); oportunidade = Column(String)
    horas_contratadas = Column(Float); tipo = Column(String)
    data_inicio = Column(String); data_termino = Column(String)
    data_entrada_producao = Column(String); data_auditoria = Column(String)
    responsavel_auditoria = Column(String); timestamp = Column(DateTime, default=datetime.now)
    # Colunas de Percentual
    inicializacao = Column(Float); planejamento = Column(Float)
    workshop_de_processos = Column(Float); construcao = Column(Float)
    go_live = Column(Float); operacao_assistida = Column(Float)
    finalizacao = Column(Float)

class AuditoriaHistorico(Base):
    __tablename__ = 'historico_auditorias'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); data_auditoria = Column(String)
    responsavel_auditoria = Column(String); progresso_total = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)

class ItemEntregue(Base):
    __tablename__ = 'rastreabilidade_entregaveis'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    item_nome = Column(String); entregue = Column(Integer) # 1 ou 0

class EvidenciaArquivo(Base):
    __tablename__ = 'evidencias_arquivos'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    arquivo_nome = Column(String); arquivo_path = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

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

# --- FUNÇÕES DE APOIO ---
def get_status_items(projeto_id):
    items = session.query(ItemEntregue).filter(ItemEntregue.projeto_id == projeto_id).all()
    return {(i.fase, i.item_nome): bool(i.entregue) for i in items}

# --- POPUP AUDITORIA DE RASTREABILIDADE ---
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def modal_auditoria(projeto_data):
    projeto_id = int(projeto_data['id'])
    status_db = get_status_items(projeto_id)
    novos_status = {}
    
    tab1, tab2, tab3 = st.tabs(["🔍 Auditoria Técnica", "📜 Histórico de Auditorias", "📂 Evidências (Prints/Docs)"])
    
    with tab1:
        st.info("Selecione os itens validados. Itens já entregues aparecem marcados para rastreabilidade.")
        total_entregue = 0
        total_itens = 0
        
        for fase, itens in METODOLOGIA.items():
            with st.expander(f"Fase: {fase}"):
                for item in itens:
                    val_anterior = status_db.get((fase, item), False)
                    res = st.checkbox(item, value=val_anterior, key=f"check_{projeto_id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res: total_entregue += 1
                    total_itens += 1
        
        st.divider()
        c1, c2 = st.columns(2)
        d_aud = c1.date_input("Data da Auditoria Técnica", format="DD/MM/YYYY")
        resp_aud = c2.text_input("Analista MV Responsável")
        
        if st.button("💾 CONSOLIDAR AUDITORIA", use_container_width=True):
            # 1. Atualizar Itens
            session.query(ItemEntregue).filter(ItemEntregue.projeto_id == projeto_id).delete()
            for (f, i), val in novos_status.items():
                session.add(ItemEntregue(projeto_id=projeto_id, fase=f, item_nome=i, entregue=1 if val else 0))
            
            # 2. Atualizar Percentuais no Projeto
            proj_db = session.query(Projeto).filter(Projeto.id == projeto_id).first()
            progresso_medio = (total_entregue / total_itens) * 100
            for fase in METODOLOGIA.keys():
                concluidos = sum(1 for it in METODOLOGIA[fase] if novos_status.get((fase, it)))
                setattr(proj_db, MAPA_COLUNAS[fase], (concluidos / len(METODOLOGIA[fase])) * 100)
            
            proj_db.data_auditoria = str(d_aud)
            proj_db.responsavel_auditoria = resp_aud
            
            # 3. Salvar Snapshot no Histórico
            session.add(AuditoriaHistorico(projeto_id=projeto_id, data_auditoria=str(d_aud), responsavel_auditoria=resp_aud, progresso_total=progresso_medio))
            session.commit()
            st.success("Auditoria Consolidada! Risco de judicialização mitigado."); st.rerun()

    with tab2:
        historico = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == projeto_id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        if historico:
            for h in historico:
                st.write(f"📅 **{h.data_auditoria}** - Progresso: **{h.progresso_total:.1f}%** | Auditor: {h.responsavel_auditoria}")
                st.divider()
        else: st.info("Sem histórico de auditorias.")

    with tab3:
        st.write("### 📎 Depósito de Evidências")
        fase_ev = st.selectbox("Fase da Evidência", list(METODOLOGIA.keys()))
        up_file = st.file_uploader("Arraste prints de e-mail ou documentos aqui", key="uploader")
        
        if st.button("📤 Salvar Evidência"):
            if up_file:
                path = os.path.join("evidencias_projetos", f"{projeto_id}_{up_file.name}")
                with open(path, "wb") as f: f.write(up_file.getbuffer())
                session.add(EvidenciaArquivo(projeto_id=projeto_id, fase=fase_ev, arquivo_nome=up_file.name, arquivo_path=path))
                session.commit(); st.success("Arquivo anexado com sucesso!")
        
        st.divider()
        docs = session.query(EvidenciaArquivo).filter(EvidenciaArquivo.projeto_id == projeto_id).all()
        for d in docs:
            st.write(f"📄 {d.fase}: {d.arquivo_nome}")

# --- INTERFACE PRINCIPAL ---
st.set_page_config(page_title="Hub de Inteligência MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='color: #143264;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    # [Mantido o bloco de inputs original do usuário para cadastro]
    with st.container():
        c1, c2, c3 = st.columns(3)
        nome_p = c1.text_input("Nome do Projeto")
        oportunidade = c2.text_input("Oportunidade (CRM)")
        gp_p = c3.text_input("Gerente de Projeto")
        # ... (Campos d_inicio, d_termino etc)
        # Ao salvar o projeto pela primeira vez:
        if st.button("💾 SALVAR NOVO PROJETO", use_container_width=True):
            novo = Projeto(nome_projeto=nome_p, gerente_projeto=gp_p, regional="Sul", oportunidade=oportunidade)
            session.add(novo); session.commit(); st.success("Projeto criado!")

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Dashboard de Governança Regional</h2>", unsafe_allow_html=True)
    
    query = session.query(Projeto).order_by(desc(Projeto.timestamp)).all()
    if query:
        df = pd.DataFrame([vars(p) for p in query]).drop_duplicates(subset=['nome_projeto'], keep='first')
        df['Progresso %'] = df[list(MAPA_COLUNAS.values())].mean(axis=1).round(1)
        
        st.info("💡 **Ação:** Clique em um projeto na tabela abaixo para abrir a **Rastreabilidade Integral**.")
        
        # Tabela Interativa
        event = st.dataframe(
            df[['id', 'nome_projeto', 'gerente_projeto', 'regional', 'Progresso %', 'data_auditoria']],
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")}
        )

        if len(event.selection.rows) > 0:
            modal_auditoria(df.iloc[event.selection.rows[0]])
