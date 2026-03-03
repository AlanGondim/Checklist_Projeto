import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# =========================================================
# 1. CONFIGURAÇÕES E BANCO DE DADOS (MODEL)
# =========================================================
Base = declarative_base()
DB_NAME = 'sqlite:///hub_inteligencia_executivo.db'
engine = create_engine(DB_NAME)
Session = sessionmaker(bind=engine)
session = Session()

# Pasta para armazenar documentos de prova (Judicialização)
if not os.path.exists("attachments"):
    os.makedirs("attachments")

class Projeto(Base):
    __tablename__ = 'monitoramento_projetos'
    id = Column(Integer, primary_key=True)
    nome_projeto = Column(String); gerente_projeto = Column(String)
    regional = Column(String); oportunidade = Column(String)
    horas_contratadas = Column(Float); tipo = Column(String)
    data_inicio = Column(String); data_termino = Column(String)
    data_entrada_producao = Column(String); data_auditoria = Column(String)
    responsavel_auditoria = Column(String); timestamp = Column(DateTime, default=datetime.now)
    # Percentuais das fases
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

class ItemAuditoria(Base):
    __tablename__ = 'itens_auditados'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    item_nome = Column(String); entregue = Column(Integer) # 1 ou 0

class EvidenciaArtefato(Base):
    __tablename__ = 'evidencias_artefatos'
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer); fase = Column(String)
    item_nome = Column(String); arquivo_nome = Column(String)
    arquivo_path = Column(String); timestamp = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)

# =========================================================
# 2. DEFINIÇÕES DA METODOLOGIA (CONTROLLER)
# =========================================================
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

# =========================================================
# 3. FUNÇÕES DE SUPORTE (LOGIC)
# =========================================================
def get_status_itens(projeto_id):
    itens = session.query(ItemAuditoria).filter(ItemAuditoria.projeto_id == projeto_id).all()
    return {(item.fase, item.item_nome): bool(item.entregue) for item in itens}

def salvar_auditoria_completa(projeto_data, novos_status, data_aud, resp_aud):
    projeto_id = int(projeto_data['id'])
    
    # 1. Salvar Itens Individuais
    session.query(ItemAuditoria).filter(ItemAuditoria.projeto_id == projeto_id).delete()
    for (fase, item_nome), entregue in novos_status.items():
        session.add(ItemAuditoria(projeto_id=projeto_id, fase=fase, item_nome=item_nome, entregue=1 if entregue else 0))
    
    # 2. Atualizar Percentuais no Projeto
    total_perc = 0
    proj_db = session.query(Projeto).filter(Projeto.id == projeto_id).first()
    for fase, itens_fase in METODOLOGIA.items():
        concluidos = sum(1 for it in itens_fase if novos_status.get((fase, it)))
        perc = (concluidos / len(itens_fase)) * 100
        setattr(proj_db, MAPA_COLUNAS[fase], perc)
        total_perc += perc
    
    proj_db.data_auditoria = str(data_aud)
    proj_db.responsavel_auditoria = resp_aud
    
    # 3. Registrar no Histórico de Snapshots
    session.add(AuditoriaHistorico(
        projeto_id=projeto_id, data_auditoria=str(data_aud),
        responsavel_auditoria=resp_aud, progresso_total=total_perc / len(METODOLOGIA)
    ))
    session.commit()

# =========================================================
# 4. COMPONENTES DE INTERFACE (VIEW)
# =========================================================
@st.dialog("📋 Auditoria de Rastreabilidade Integral", width="large")
def modal_auditoria(projeto_data):
    projeto_id = int(projeto_data['id'])
    st.write(f"### Projeto: {projeto_data['nome_projeto']}")
    
    status_atual = get_status_itens(projeto_id)
    novos_status = {}
    tab1, tab2, tab3 = st.tabs(["📝 Auditoria Técnica", "📜 Histórico", "📂 Evidências"])

    with tab1:
        st.info("Valide os artefatos. Itens marcados anteriormente são preservados para rastreabilidade.")
        for fase, itens in METODOLOGIA.items():
            with st.expander(f"Fase: {fase}"):
                for item in itens:
                    c1, c2 = st.columns([0.5, 0.5])
                    v_prev = status_atual.get((fase, item), False)
                    res = c1.checkbox(item, value=v_prev, key=f"p_{projeto_id}_{fase}_{item}")
                    novos_status[(fase, item)] = res
                    if res:
                        arquivo = c2.file_uploader("Anexar Prova", key=f"f_{projeto_id}_{fase}_{item}", label_visibility="collapsed")
                        if arquivo:
                            path = os.path.join("attachments", f"{projeto_id}_{fase}_{arquivo.name}")
                            with open(path, "wb") as f: f.write(arquivo.getbuffer())
                            session.add(EvidenciaArtefato(projeto_id=projeto_id, fase=fase, item_nome=item, arquivo_nome=arquivo.name, arquivo_path=path))
                            st.toast(f"Evidência salva: {item}")

        st.divider()
        c1, c2 = st.columns(2)
        d_aud = c1.date_input("Data da Auditoria", format="DD/MM/YYYY")
        r_aud = c2.text_input("Auditor Responsável", value=projeto_data.get('responsavel_auditoria', ''))

        if st.button("💾 Finalizar Auditoria e Salvar Evolução", use_container_width=True):
            salvar_auditoria_completa(projeto_data, novos_status, d_aud, r_aud)
            st.success("Snapshot de auditoria salvo com sucesso!"); st.rerun()

    with tab2:
        hist = session.query(AuditoriaHistorico).filter(AuditoriaHistorico.projeto_id == projeto_id).order_by(desc(AuditoriaHistorico.timestamp)).all()
        for h in hist:
            with st.expander(f"📅 Auditoria em {h.data_auditoria} - {h.progresso_total:.1f}%"):
                st.write(f"**Analista:** {h.responsavel_auditoria}")

    with tab3:
        evidencias = session.query(EvidenciaArtefato).filter(EvidenciaArtefato.projeto_id == projeto_id).all()
        for ev in evidencias:
            with open(ev.arquivo_path, "rb") as f:
                st.download_button(f"⬇️ {ev.item_nome} ({ev.arquivo_nome})", f, file_name=ev.arquivo_nome, key=f"dl_{ev.id}")

# =========================================================
# 5. EXECUÇÃO DA INTERFACE
# =========================================================
st.set_page_config(page_title="Hub de Inteligência MV", layout="wide")
modo = st.sidebar.radio("Navegação", ["Checklist Operacional", "Dashboard Regional"])

if modo == "Checklist Operacional":
    st.markdown("<h2 style='color: #143264;'>🏛️ Hub de Inteligência | Operação</h2>", unsafe_allow_html=True)
    # [Lógica original de cadastro de projetos mantida aqui...]
    # (Inserir campos de input e botão st.button("💾 SALVAR NO HUB") conforme seu código original)

elif modo == "Dashboard Regional":
    st.markdown("<h2 style='color: #143264;'>📊 Dashboard de Governança Regional</h2>", unsafe_allow_html=True)
    query = session.query(Projeto).order_by(desc(Projeto.timestamp)).all()
    if query:
        df = pd.DataFrame([vars(p) for p in query]).drop_duplicates(subset=['nome_projeto'], keep='first')
        df['Progresso %'] = df[list(MAPA_COLUNAS.values())].mean(axis=1).round(1)

        # Filtros
        f_gp = st.sidebar.multiselect("Filtrar por Gerente", sorted(df['gerente_projeto'].unique()))
        if f_gp: df = df[df['gerente_projeto'].isin(f_gp)]

        st.info("💡 **Ação:** Clique em uma linha para auditar detalhadamente os artefatos e anexar provas.")
        df_display = df.rename(columns={v: k for k, v in MAPA_COLUNAS.items()})
        
        event = st.dataframe(
            df_display[['id', 'nome_projeto', 'gerente_projeto', 'regional', 'Progresso %', 'data_auditoria']],
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={"id": None, "Progresso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")}
        )

        if len(event.selection.rows) > 0:
            modal_auditoria(df_display.iloc[event.selection.rows[0]])
