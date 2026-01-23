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
        if linha.startswith('###'):
            doc.add_heading(linha.replace('###', '').strip(), level=1)
        elif linha.strip():
            doc.add_paragraph(linha)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def realizar_analise(prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        
        # Descoberta automática do modelo para evitar Erro 404
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        nome_modelo = next((m for m in modelos if 'gemini-1.5-flash' in m), None)
        
        if not nome_modelo:
            if modelos:
                nome_modelo = modelos[0]
            else:
                return "Erro: Nenhum modelo disponível nesta chave API."

        model = genai.GenerativeModel(nome_modelo)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e): return "ERRO_COTA"
        return f"Erro na API: {str(e)}"

# --- 3. INTERFACE ---
st.title("🛡️ Painel de Editoração - Encontros Bibli")
st.caption("Versão atualizada com as normas do Tutorial de Normalização da UFSC/EB.")

with st.sidebar:
    st.header("Configuração")
    api_key_input = st.text_input("🔑 API Key:", type="password")
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    st.divider()
    if st.button("🧹 Limpar Sessão"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.info("👈 Por favor, insira a API Key na barra lateral.")
    st.stop()

arquivo = st.file_uploader("📂 Suba o artigo em DOCX", type="docx")

if arquivo:
    doc_file = Document(arquivo)
    texto_completo = "\n".join([p.text for p in doc_file.paragraphs if p.text.strip()])
    
    st.success(f"Artigo '{arquivo.name}' carregado!")

    tab1, tab2, tab3 = st.tabs(["📐 Estrutura EB", "✍️ Revisão Textual", "📚 Normas ABNT/EB"])

    with tab1:
        st.subheader("📐 Revisão de Forma e Maquetação (Template & Tutorial 2025)")
        if st.button("Executar Análise de Estrutura e Maquetação"):
            with st.spinner("Sincronizando com o Template e Tutorial..."):
                # PROMPT MELHORADO COM BASE NOS ARQUIVOS ENVIADOS
                prompt_maquetacao = (
                    "Aja como Editor de Layout da Revista Encontros Bibli. Analise o artigo comparando-o "
                    "estritamente com o Template e o Tutorial de Editoração (Atualizado em 10/04/2025):\n\n"
                    
                    "1. PÁGINA INICIAL (ITENS 2.1.1 e 2.1.2):\n"
                    "   - TIPOLOGIA: Deve estar no topo (Artigo Original, Ensaio, etc.). Se o texto for em inglês/espanhol, a tipologia deve estar traduzida.\n"
                    "   - TÍTULO PT: Arial Black, tamanho 16, MAIÚSCULO, Negrito, alinhado à esquerda.\n"
                    "   - TÍTULO EN: Arial, tamanho 10, minúsculo (apenas iniciais/nomes próprios), Negrito, alinhado à esquerda.\n\n"
                    
                    "2. RESUMO E ESTRUTURA (ITEM 2.3):\n"
                    "   - CORPO: Arial 9, Justificado, Simples, sem parágrafo. Mínimo 150, máx 250 palavras.\n"
                    "   - ELEMENTOS OBRIGATÓRIOS: Deve conter explicitamente Objetivo, Método, Resultado e Conclusões.\n"
                    "   - PALAVRAS-CHAVE: 3 a 5 termos, obrigatoriamente separadas por PONTO (.).\n\n"
                    
                    "3. CORPO DO TEXTO E ELEMENTOS GRÁFICOS:\n"
                    "   - SEÇÕES: Arial 12, Negrito. Primárias em MAIÚSCULO. Secundárias em minúsculo.\n"
                    "   - ILUSTRAÇÕES/TABELAS: Título acima (Arial 10). Fonte/Nota abaixo (Arial 9).\n\n"
                    
                    "4. LIMPEZA DE METADADOS DA REVISTA (PÁG 16 DO TUTORIAL):\n"
                    "   - Deletar as frases: 'Uso exclusivo da autoria' e 'Uso exclusivo da revista'.\n"
                    "   - No HISTÓRICO: Verificar se as datas estão em ordem PT-BR (dia-mês-ano). Retirar 'uso exclusivo da revista' do cabeçalho do histórico.\n"
                    "   - EDITORES: Verificar se constam os nomes: Edgar Bisset Alvarez, Patrícia Neubert, Genilson Geraldo, "
                    "Camila De Azevedo Gibbon, Jônatas Edison da Silva, Luan Soares Silva, Marcela Reinhardt e Daniela Capri.\n\n"
                    
                    "Aponte as divergências em relação ao Template e ao Tutorial. NÃO RESUMA O ARTIGO.\n"
                    f"Texto para análise: {texto_artigo[:15000]}"
                )
                
                res = model.generate_content(prompt_maquetacao).text
                st.markdown(res)
                
                st.download_button(
                    label="📥 Baixar Relatório de Maquetação",
                    data=gerar_docx(res, "Relatório de Revisão de Forma e Maquetação"),
                    file_name=f"Revisao_Maquetacao_{artigo_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    with tab2:
        st.subheader("✍️ Revisão Gramatical, Estilo e Citações (PT/EN/ES)")
        if st.button("Executar Revisão Profunda"):
            # Dividindo o texto em blocos para manter a precisão da análise gramatical
            blocos = [texto_artigo[i:i+12000] for i in range(0, len(texto_artigo), 12000)]
            relatorio_final = ""
            progresso = st.progress(0)
            
            for idx, bloco in enumerate(blocos):
                st.write(f"Analisando bloco {idx+1} de {len(blocos)}...")
                
                prompt_gramatica = (
                    "Aja como um revisor acadêmico sênior e tradutor técnico. "
                    "Analise o texto a seguir considerando que ele pode estar em PORTUGUÊS, INGLÊS ou ESPANHOL.\n\n"
                    
                    "1. REVISÃO IDIOMÁTICA:\n"
                    "   - Identifique erros ortográficos, gramaticais e de pontuação no idioma detectado.\n"
                    "   - Melhore a fluidez e a coesão textual, eliminando repetições e ambiguidades.\n"
                    "   - Garanta o uso de terminologia técnica adequada à Ciência da Informação.\n\n"
                    
                    "2. CITAÇÕES (ABNT NBR 10520 - DIRETRIZES UFSC):\n"
                    "   - Verifique citações diretas curtas (até 3 linhas): Devem estar no corpo do texto entre aspas.\n"
                    "   - Verifique citações diretas longas (mais de 3 linhas): Recuo de 4cm, fonte Arial 10, sem aspas, espaçamento simples.\n"
                    "   - Formato Autor-Data: Verifique o uso correto de (AUTOR, ano) dentro dos parênteses e 'Autor (ano)' fora dos parênteses.\n"
                    "   - Verifique o uso de 'et al.' para mais de 3 autores (em itálico conforme a revista).\n\n"
                    
                    "3. TRADUÇÃO DE APOIO:\n"
                    "   - Caso encontre termos em idiomas diferentes do principal sem tradução, aponte a necessidade de ajuste.\n\n"
                    
                    "Apresente os erros encontrados em uma tabela (Erro | Sugestão | Justificativa). "
                    "NÃO RESUMA O TEXTO.\n\n"
                    f"Bloco de texto para análise:\n{bloco}"
                )
                
                try:
                    r = model.generate_content(prompt_gramatica).text
                    if "ERRO_COTA" in r:
                        st.warning("Aguardando cota da API...")
                        time.sleep(60)
                        r = model.generate_content(prompt_gramatica).text
                    
                    relatorio_final += f"\n### Análise do Bloco {idx+1}\n{r}\n"
                    time.sleep(4) # Delay de segurança para a API
                except Exception as e:
                    relatorio_final += f"\nErro no bloco {idx+1}: {str(e)}\n"
                
                progresso.progress((idx+1)/len(blocos))
            
            st.markdown(relatorio_final)
            if relatorio_final:
                st.download_button(
                    label="📥 Baixar Relatório de Gramática e Citações",
                    data=gerar_docx(relatorio_final, "Relatório de Revisão Gramatical e Citações"),
                    file_name=f"Revisao_Gramatical_{artigo_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    with tab3:
        st.subheader("Referências NBR 6023 (Tutorial UFSC)")
        if st.button("Validar Referências"):
            with st.spinner("Analisando ABNT..."):
                prompt_ref = (
                    "Aja como bibliotecário da UFSC. Valide as referências conforme o tutorial da revista Encontros Bibli: "
                    "1. O título da obra deve estar em NEGRITO. "
                    "2. Nomes de autores devem seguir o padrão: SOBRENOME, Nome. "
                    "3. Verifique se o link DOI foi incluído e se está no formato correto (https://doi.org/...). "
                    "4. Verifique a pontuação entre cidade, editora e ano. "
                    "Indique as correções necessárias. "
                    f"\n\nReferências:\n{texto_completo[-8000:]}"
                )
                res = realizar_analise(prompt_ref, api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar Relatório", gerar_docx(res, "Referencias_EB"), f"Ref_EB_{arquivo.name}")

