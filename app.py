import streamlit as st
from docx import Document
import google.generativeai as genai
import time
from io import BytesIO

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 2. FUNÇÕES DE APOIO ---
def gerar_docx(conteudo, titulo):
    doc = Document()
    doc.add_heading(titulo, 0)
    for linha in conteudo.split('\n'):
        if linha.strip():
            doc.add_paragraph(linha)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def realizar_analise(prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        # Descoberta dinâmica de modelo para evitar erro 404
        modelos_validos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        nome_modelo = next((m for m in modelos_validos if 'gemini-1.5-flash' in m), modelos_validos[0])
        
        model = genai.GenerativeModel(nome_modelo)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e): return "⚠️ ERRO_COTA: Limite de requisições atingido. Aguarde 60 segundos."
        return f"❌ Erro na API: {str(e)}"

# --- 3. INTERFACE ---
st.title("🛡️ Painel de Editoração - Encontros Bibli")
st.markdown("### Sistema de Revisão Sincronizado (Tutorial 10/04/2025)")

with st.sidebar:
    st.header("Configuração")
    api_key_input = st.text_input("🔑 API Key:", type="password")
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    st.divider()
    if st.button("🧹 Limpar Sessão"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.info("👈 Por favor, insira sua API Key na lateral para ativar o sistema.")
    st.stop()

# --- 4. UPLOAD E PROCESSAMENTO ---
artigo_file = st.file_uploader("📂 Subir Artigo para Revisão (Formato DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Lendo artigo e mapeando diretrizes da UFSC..."):
        try:
            doc = Document(artigo_file)
            texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
            st.success(f"✅ Artigo '{artigo_file.name}' carregado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")
            st.stop()

    tab1, tab2, tab3 = st.tabs(["📐 Maquetação & Forma", "✍️ Gramática & Citações", "📚 Referências (ABNT)"])

    # --- ABA 1: MAQUETAÇÃO (Baseada no Tutorial 2025 e Template) ---
    with tab1:
        st.subheader("Análise de Maquetação e Identidade Visual")
        if st.button("Executar Análise de Forma"):
            with st.spinner("Conferindo fontes, tamanhos e metadados..."):
                prompt_maquetacao = (
                    "Aja como Editor de Layout da Revista Encontros Bibli. Analise o artigo comparando-o "
                    "estritamente com o Template e o Tutorial de Editoração (Atualizado em 10/04/2025):\n\n"
                    "1. PÁGINA INICIAL:\n"
                    "   - Título PT: Deve ser Arial Black, tamanho 16, MAIÚSCULO, Negrito, Alinhado à esquerda.\n"
                    "   - Título EN: Deve ser Arial, tamanho 10, minúsculo, Negrito, Alinhado à esquerda.\n"
                    "2. RESUMO ESTRUTURADO: Deve conter explicitamente Objetivo, Método, Resultado e Conclusões. Fonte Arial 9, Justificado.\n"
                    "3. PALAVRAS-CHAVE: 3 a 5 termos, separadas obrigatoriamente por PONTO (.).\n"
                    "4. LIMPEZA DE METADADOS: Deletar as frases 'uso exclusivo da autoria' e 'Uso exclusivo da revista'.\n"
                    "5. HISTÓRICO: Datas devem estar em ordem dia-mês-ano. Retirar menção a 'uso exclusivo'.\n"
                    "6. EDITORES: Verificar se constam: Edgar Bisset Alvarez, Patrícia Neubert, Genilson Geraldo, "
                    "Camila De Azevedo Gibbon, Jônatas Edison da Silva, Luan Soares Silva, Marcela Reinhardt e Daniela Capri.\n"
                    f"\nTexto do artigo:\n{texto_artigo[:12000]}"
                )
                res = realizar_analise(prompt_maquetacao, api_key)
                st.markdown(res)
                st.download_button("📥 Baixar Relatório de Forma", gerar_docx(res, "Revisao_Maquetacao"), "maquetacao.docx")

    # --- ABA 2: GRAMÁTICA E CITAÇÕES (Multilíngue + Padrão UFSC) ---
    with tab2:
        st.subheader("Revisão Linguística e Normas de Citação")
        if st.button("Executar Revisão Linguística"):
            with st.spinner("Analisando gramática (PT/EN/ES) e NBR 10520..."):
                prompt_gramatica = (
                    "Aja como revisor acadêmico da Encontros Bibli. Detecte o idioma (Português, Inglês ou Espanhol) e realize:\n"
                    "1. REVISÃO GRAMATICAL: Ortografia, pontuação, clareza e estilo científico.\n"
                    "2. CITAÇÕES (ABNT NBR 10520): Verifique o sistema Autor-data.\n"
                    "   - Citações longas (+3 linhas): Recuo de 4cm, fonte Arial 10, sem aspas, espaço simples.\n"
                    "   - Citações curtas: Entre aspas no corpo do texto.\n"
                    "3. PADRÃO REVISTA: Verifique se 'et al.' está em itálico e se as chamadas de autor estão corretas.\n"
                    f"\nTexto do artigo:\n{texto_artigo[1000:12000]}"
                )
                res = realizar_analise(prompt_gramatica, api_key)
                st.markdown(res)
                st.download_button("📥 Baixar Relatório Gramatical", gerar_docx(res, "Revisao_Gramatical"), "gramatica.docx")

    # --- ABA 3: REFERÊNCIAS (ABNT NBR 6023) ---
    with tab3:
        st.subheader("Validação de Referências Bibliográficas")
        if st.button("Validar Referências"):
            with st.spinner("Conferindo negrito, DOI e normas ABNT..."):
                prompt_referencias = (
                    "Aja como Editor da Revista Encontros Bibli. Valide as referências conforme NBR 6023:\n"
                    "1. TÍTULO DA OBRA: Deve estar obrigatoriamente em NEGRITO.\n"
                    "2. DOI: É obrigatório em formato de URL completa (https://doi.org/...).\n"
                    "3. NOMES: Padrão SOBRENOME, Nome (iniciais ou por extenso conforme o artigo).\n"
                    "4. HIGIENE: Aponte referências incompletas ou com pontuação errada.\n"
                    f"\nReferências extraídas:\n{texto_artigo[-8000:]}"
                )
                res = realizar_analise(prompt_referencias, api_key)
                st.markdown(res)
                st.download_button("📥 Baixar Relatório de Referências", gerar_docx(res, "Referencias_ABNT"), "referencias.docx")

