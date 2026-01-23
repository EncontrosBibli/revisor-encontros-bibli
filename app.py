import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import os
import time

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

# Forçamos o modelo 1.5-flash para garantir estabilidade de cota
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
        # Chamada direta ao modelo estável 1.5-flash
        url = f"https://generativelanguage.googleapis.com/v1/models/{NOME_MODELO_FIXO}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt_texto}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
        }
        res = requests.post(url, json=payload)
        
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        elif res.status_code == 429:
            return "ERRO_COTA: Limite de requisições atingido. Aguardando..."
        else:
            return f"Erro: {res.text}"

    with tab1:
        if st.button("Executar Verificação de Estrutura"):
            with st.spinner("Analisando estrutura..."):
                prompt = f"REVISOR RIGOROSO: Verifique títulos bilingues, resumo (100-250 palavras) e palavras-chave separadas por ponto. Idiomas aceitos: PT, EN, ES.\nTUTORIAL: {texto_tutorial}\nTEXTO: {texto_artigo[:8000]}"
                st.markdown(realizar_analise(prompt))

    with tab2:
        if st.button("Executar Revisão Linguística"):
            with st.spinner("Iniciando revisão por partes..."):
                # Blocos maiores (12k a 15k) reduzem o número de chamadas à API
                tamanho_bloco = 12000 
                blocos = [texto_artigo[i:i + tamanho_bloco] for i in range(0, len(texto_artigo), tamanho_bloco)]
                
                relatorio_final = ""
                progresso = st.progress(0)
                status_text = st.empty()
                
                for idx, bloco in enumerate(blocos):
                    status_text.text(f"Analisando parte {idx+1} de {len(blocos)}...")
                    
                    prompt = f"Atue como Revisor Sênior. Liste ERROS de ortografia/gramática e de citações ABNT (mais de 3 linhas = recuo 4cm, sem aspas). Se tudo estiver certo, diga 'OK'.\nTRECHO: {bloco}"
                    
                    resultado = realizar_analise(prompt)
                    
                    # Se bater na cota, espera 10 segundos e tenta de novo a mesma parte
                    if "ERRO_COTA" in resultado:
                        status_text.warning("Cota atingida! Pausando 10 segundos para retomar...")
                        time.sleep(10)
                        resultado = realizar_analise(prompt)
                    
                    if "OK" not in resultado.upper():
                        relatorio_final += f"\n### Parte {idx+1}\n" + resultado
                    
                    # Pausa de segurança entre requisições bem-sucedidas
                    time.sleep(4) 
                    progresso.progress((idx + 1) / len(blocos))
                
                status_text.empty()
                if relatorio_final:
                    st.markdown(relatorio_final)
                else:
                    st.success("Nenhum erro linguístico detectado.")

    with tab3:
        if st.button("Executar Validação de Referências"):
            with st.spinner("Analisando referências..."):
                # Foca no final do documento (últimos 30%)
                referencias = texto_artigo[int(len(texto_artigo)*0.7):]
                prompt = f"Verifique Referências ABNT NBR 6023. Título em NEGRITO e ordem alfabética são obrigatórios.\nREFERÊNCIAS:\n{referencias}"
                st.markdown(realizar_analise(prompt))
