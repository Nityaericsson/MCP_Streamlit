import streamlit as st
import asyncio
import nest_asyncio

nest_asyncio.apply()
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from main import AIService

st.set_page_config(page_title="AI MCP Assistant", layout="centered")

st.title("🤖 AI Assistant (Weather + Stocks)")

# Initialize service
if "ai_service" not in st.session_state:
    st.session_state.ai_service = AIService()

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat input
user_input = st.chat_input("Ask something...")

if user_input:
    st.session_state.messages.append(("user", user_input))

    try:
        response = asyncio.get_event_loop().run_until_complete(
            st.session_state.ai_service.process_query(user_input)
        )
    except Exception as e:
        response = f"❌ Error: {str(e)}"

    st.session_state.messages.append(("assistant", response))
# Display chat
for role, msg in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(msg)