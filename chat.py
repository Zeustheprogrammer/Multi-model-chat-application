import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from PIL import Image
import requests
import speech_recognition as sr

# Page configuration
st.set_page_config(
    page_title="Intelligent Chat",
    page_icon="artificial-chat-ai-chat-chat-message-communication-artificial-intelligence-icon-130207-256.png",
    layout="wide",
)

st.caption("Multi-model chat application")

#------------------------------------------------------------
# FUNCTIONS
def extract_graphviz_info(text: str) -> list:
    """Extracts graphviz code blocks from the given text."""
    graphviz_info = text.split('```')
    return [graph for graph in graphviz_info if ('graph' in graph or 'digraph' in graph) and ('{' in graph and '}' in graph)]

def append_message(message: dict) -> None:
    """Appends a message to the chat session."""
    st.session_state.chat_session.append({'user': message})

@st.cache_resource
def load_model() -> genai.GenerativeModel:
    """Loads the generative model for text tasks."""
    model = genai.GenerativeModel('gemini-pro')
    return model

@st.cache_resource
def load_modelvision() -> genai.GenerativeModel:
    """Loads the generative model for vision tasks."""
    model = genai.GenerativeModel('gemini-pro-vision')
    return model

#------------------------------------------------------------
# CONFIGURATION
api_key = st.secrets["api_key"]
genai.configure(api_key=api_key)

model = load_model()
vision = load_modelvision()

if 'chat' not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

if 'chat_session' not in st.session_state:
    st.session_state.chat_session = []

#------------------------------------------------------------
# CHAT INTERFACE
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'welcome' not in st.session_state:
    welcome = model.generate_content('''
    Welcome message to the user describing what the chatbot can do.
    You can describe images, answer questions, read text files, read tables, generate Graphviz graphs, etc.
    ''')
    welcome.resolve()
    st.session_state.welcome = welcome
    with st.chat_message('ai'):
        st.write(st.session_state.welcome.text)
else:
    with st.chat_message('ai'):
        st.write(st.session_state.welcome.text)

if len(st.session_state.chat_session) > 0:
    for message in st.session_state.chat_session:
        if message['user']['role'] == 'model':
            with st.chat_message('ai'):
                st.write(message['user']['parts'])
                graphs = extract_graphviz_info(message['user']['parts'])
                if graphs:
                    for graph in graphs:
                        st.graphviz_chart(graph, use_container_width=False)
                        with st.expander("View text"):
                            st.code(graph, language='dot')
        else:
            with st.chat_message('user'):
                st.write(message['user']['parts'][0])
                if len(message['user']['parts']) > 1:
                    st.image(message['user']['parts'][1], width=200)

#------------------------------------------------------------
# ATTACHMENT HANDLING
#
#cols = st.columns(3)
#with cols[0]:
#    image_attachment = st.toggle("Attach image", value=False)
#with cols[1]:
#    text_attachment = st.toggle("Attach text file", value=False)
#with cols[2]:
#    audio_input = st.toggle("Audio Input", value=False)

#"""
cols = st.columns(4)
with cols[0]:
    image_attachment = st.toggle("Attach image", value=False)
with cols[1]:
    text_attachment = st.toggle("Attach text file", value=False)
with cols[2]:
    csv_excel_attachment = st.toggle("Attach CSV or Excel", value=False)
with cols[3]:
    audio_input = st.toggle("Audio Input", value=False)


if image_attachment:
    image = st.file_uploader("Upload your image", type=['png', 'jpg', 'jpeg'])
    url = st.text_input("Or paste your image URL")
else:
    image = None
    url = ''

if text_attachment:
    txtattachment = st.file_uploader("Upload your text file", type=['txt'])
else:
    txtattachment = None

if csv_excel_attachment:
    csvexcelattachment = st.file_uploader("Upload your CSV or Excel file", type=['csv', 'xlsx'])
else:
    csvexcelattachment = None

if audio_input:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Speak now...")
        audio = r.listen(source)
    try:
        prompt = r.recognize_google(audio)
    except sr.UnknownValueError:
        st.warning("Sorry, I couldn't understand what you said.")
        prompt = None
else:
    prompt = st.chat_input("Write your message")


#if Graphviz_input:
   # image = st.file_uploader("Upload your image", type=['png', 'jpg', 'jpeg'])
   # url = st.text_input("Or paste your image URL")
#else:
    #image = None
   # url = ''


if prompt:
    txt = ''
    if txtattachment:
        txt = txtattachment.getvalue().decode("utf-8")
        txt = '   Text file: \n' + txt

    if len(txt) > 5000:
        txt = txt[:5000] + '...'

    if image or url:
        if url:
            img = Image.open(requests.get(url, stream=True).raw)
        else:
            img = Image.open(image)
        prmt = {'role': 'user', 'parts': [prompt + txt, img]}
    else:
        prmt = {'role': 'user', 'parts': [prompt + txt]}

    append_message(prmt)

    with st.spinner("Wait a moment, I am thinking..."):
        if len(prmt['parts']) > 1:
            response = vision.generate_content(prmt['parts'], stream=True, safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"},
            ])
            response.resolve()
        else:
            response = st.session_state.chat.send_message(prmt['parts'][0])

        try:
            append_message({'role': 'model', 'parts': response.text})
        except Exception as e:
            append_message({'role': 'model', 'parts': f'{type(e).__name__}: {e}'})

        st.rerun()
    