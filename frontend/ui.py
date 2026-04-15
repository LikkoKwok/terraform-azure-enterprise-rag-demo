import os
import streamlit as st
import requests

st.set_page_config(page_title="Enterprise RAG Platform", layout="wide")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.title("📂Enterprise RAG Platform")
st.sidebar.header("Admin Dashboard")
uploaded_files = st.sidebar.file_uploader("Upload PDF Manuals (Max 100)", accept_multiple_files=True)

if uploaded_files:
    st.sidebar.success(f"Ready: {len(uploaded_files)} files")

if uploaded_files and st.sidebar.button("Ingest PDFs to Azure AI Search"):
    files_payload = [
        ("files", (uploaded_file.name, uploaded_file.getvalue(), "application/pdf"))
        for uploaded_file in uploaded_files
    ]

    try:
        ingest_res = requests.post(
            f"{API_BASE_URL}/ingest",
            files=files_payload,
            timeout=180,
        )
        if ingest_res.status_code == 200:
            result = ingest_res.json()
            st.sidebar.success(
                (
                    f"Indexed {result['chunks_indexed']} chunks from "
                    f"{result['files_processed']} files into {result['index']}."
                )
            )
        else:
            st.sidebar.error(
                f"Ingestion failed ({ingest_res.status_code}): {ingest_res.text}"
            )
    except requests.RequestException as exc:
        st.sidebar.error(f"Cannot reach backend ingestion API: {exc}")

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Enter your question about the manuals..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Calling FastAPI endpoint
        try:
            res = requests.get(
                f"{API_BASE_URL}/query",
                params={"question": prompt},
                timeout=120,
            )
            if res.status_code == 200:
                data = res.json()
                full_res = data["answer"]
                if "eval_score" in data:
                    full_res += f"\n\n---\n*💡 AI Self-Evaluation Score: {data['eval_score']}*"
                st.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
            else:
                st.error("Requests are too frequent or the backend is unavailable, please try again later.")
        except requests.RequestException:
            st.error("Cannot reach backend API. Check API_BASE_URL app setting and backend app health.")
