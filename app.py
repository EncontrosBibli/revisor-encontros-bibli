import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import os
import time
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 1. GESTÃO DO TUTORIAL (ENDEREÇO FIXO) ---
URL_TUTORIAL = "https://periodicos.ufsc.br/index.php/eb/libraryFiles/downloadPublic/710"
CAMINHO_LOCAL_TUTORIAL = "tutorial_encontros_bibli.pdf"

@st.cache_data(show_spinner=False)
def baixar_e_ler_tutorial():
    """Baixa o tutorial do site da UFSC e extrai o texto."""
    try:
        response = requests.get(URL_TUTORIAL, timeout=15)
        with open(CAMINHO_LOCAL_TUTORIAL, "wb") as f:
            f.write(response.content)
        
        pdf = PdfReader(CAMINHO_LOCAL_TUTORIAL)
        texto = "\n".join([page.extract_text() for page in pdf.pages])
        return texto
    except Exception as e:
        return f"Erro ao acessar diretrizes online: {e}"

# --- 2. FUNÇÕES DE APOIO ---
def limpar_sessao():
    st.session_state.clear()
    st.rerun()

def gerar_docx_download(conteudo, titulo_relatorio):
    """Cria um arquivo .docx a partir do texto de análise."""
    doc_out = Document()
    doc_out.add_heading(titulo_relatorio, 0)
    
    # Adiciona o conteúdo ao Word tratando quebras de linha e títulos simples
    for linha in conteudo.split('\n'):
        if linha.startswith('###'):
            doc_out.add_heading(linha.replace('###', '').strip(), level=1)
        elif linha.strip():
            doc_out.add_paragraph(linha)
            
    buffer = BytesIO()
    doc_out.save(buffer)
    buffer.seek(0)
    return buffer

# Modelo estável
NOME_MODELO_FIXO = "gemini-1.5-flash"

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Revista Encontros Bibli")
st.caption("Sistema de Revisão Técnica, Normativa e Linguística (PT/EN/ES)")

# BARRA LATERAL
with st.sidebar:
    st.header("Configurações")
    api_key = st.text_input("🔑 API Key do Editor:", type="password")
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.info("Utilizando chave mestra do sistema.")
    
    st.divider()
    if st.button("🧹 Limpar e Novo Artigo"):
        limpar_sessao()

if not api_key:
    st.warning("👈 Por favor, insira a API Key para ativar os módulos de IA.")
    st.stop()

# --- FLUXO PRINCIPAL ---
artigo_file = st.file_uploader("📂 Subir Artigo para Revisão (Formato DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Lendo artigo e sincronizando normas da UFSC..."):
        doc = Document(artigo_file)
        texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        texto_tutorial = baixar_e_ler_tutorial()

    st.success("✅ Documentos processados com sucesso!")
    
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura & Formatação", "✍️ Gramática & Citações", "📚 Referências (ABNT)"])

    def realizar_analise(prompt_texto):
        url = f"https://generativelanguage.googleapis.com/v1/models/{NOME_MODELO_FIXO}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt_texto}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
        }
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            elif res.status_code == 429:
                return "ERRO_COTA: Limite atingido."
            else:
                return f"Erro na API: {res.text}"
        except Exception as e:
            return f"Erro de conexão: {e}"

    # --- TAB 1: ESTRUTURA ---
    with tab1:
        if st.button("Executar Verificação de Estrutura", key="btn_tab1"):
            with st.spinner("Analisando estrutura..."):
                prompt = f"REVISOR RIGOROSO: Verifique títulos bilingues, resumo (100-250 palavras) e palavras-chave. Idiomas: PT, EN, ES.\nTUTORIAL: {texto_tutorial}\nTEXTO: {texto_artigo[:8000]}"
                resultado_est = realizar_analise(prompt)
                st.markdown(resultado_est)
                
                st.divider()
                st.download_button(
                    label="📥 Salvar Relatório de Estrutura (.docx)",
                    data=gerar_docx_download(resultado_est, "Relatório de Estrutura e Formatação"),
                    file_name=f"Estrutura_{artigo_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    # --- TAB 2: LINGUÍSTICA ---
    with tab2:
        if st.button("Executar Revisão Linguística", key="btn_tab2"):
            with st.spinner("Iniciando revisão por partes..."):
                tamanho_bloco = 12000 
                blocos = [texto_artigo[i:i + tamanho_bloco] for i in range(0, len(texto_artigo), tamanho_bloco)]
                
                relatorio_ling = ""
                progresso = st.progress(0)
                status_text = st.empty()
                
                for idx, bloco in enumerate(blocos):
                    status_text.text(f"Analisando parte {idx+1} de {len(blocos)}...")
                    prompt = f"Atue como Revisor Sênior. Liste ERROS de ortografia/gramática e de citações ABNT. Se tudo estiver certo, diga 'OK'.\nTRECHO: {bloco}"
                    
                    resultado = realizar_analise(prompt)
                    if "ERRO_COTA" in resultado:
                        time.sleep(10)
                        resultado = realizar_analise(prompt)
                    
                    if "OK" not in resultado.upper():
                        relatorio_ling += f"\n### Parte {idx+1}\n" + resultado
                    
                    time.sleep(4) 
                    progresso.progress((idx + 1) / len(blocos))
                
                status_text.empty()
                if relatorio_ling:
                    st.markdown(relatorio_ling)
                    st.divider()
                    st.download_button(
                        label="📥 Salvar Relatório Linguístico (.docx)",
                        data=gerar_docx_download(relatorio_ling, "Revisão Linguística e Citações"),
                        file_name=f"Linguistica_{artigo_file.name}",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    st.success("Nenhum erro linguístico detectado.")

    # --- TAB 3: REFERÊNCIAS ---
    with tab3:
        if st.button("Executar Validação de Referências", key="btn_tab3"):
            with st.spinner("Analisando referências..."):
                # Pega o final do texto onde costumam estar as referências
                referencias_texto = texto_artigo[int(len(texto_artigo)*0.7):]
                prompt = f"Verifique Referências ABNT NBR 6023. Título em NEGRITO e ordem alfabética obrigatórios.\nREFERÊNCIAS:\n{referencias_texto}"
                resultado_ref = realizar_analise(prompt)
                st.markdown(resultado_ref)
                
                st.divider()
                st.download_button(
                    label="📥 Salvar Relatório de Referências (.docx)",
                    data=gerar_docx_download(resultado_ref, "Validação de Referências ABNT"),
                    file_name=f"Referencias_{artigo_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
