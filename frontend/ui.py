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
                timeout=30,
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
