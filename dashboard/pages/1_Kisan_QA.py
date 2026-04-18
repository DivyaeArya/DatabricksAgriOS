import streamlit as st
import os
import io
import time
import base64
from groq import Groq
from databricks.vector_search.client import VectorSearchClient
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment

# API Keys and endpoints
GROQ_API_KEY = "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"
DATABRICKS_HOST = "https://dbc-a6b1b203-95b7.cloud.databricks.com"
DATABRICKS_TOKEN = "dapi9ae9552ee49526db039a9f8dff3eb100"

st.set_page_config(page_title="Kisan Q&A Assistant", page_icon="🌾", layout="centered")

st.markdown("""
<style>
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
try:
    with col1:
        st.page_link("pages/0_Setup.py", label="Setup & Location", icon="🏠")
    with col2:
        st.page_link("pages/2_Dashboard.py", label="Simulation Dashboard", icon="📊")
    with col3:
        st.page_link("pages/1_Kisan_QA.py", label="Kisan Q&A", icon="🌾")
except Exception:
    st.warning("⚠️ Navigation Disabled: Please run `streamlit run app.py` from the dashboard directory to enable multipage routing.")
st.markdown("---")

@st.cache_resource
def get_clients():
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        groq_client = None
        st.error(f"Groq Init Error: {e}")
        
    try:
        vsc = VectorSearchClient(
            workspace_url=DATABRICKS_HOST,
            personal_access_token=DATABRICKS_TOKEN
        )
        index = vsc.get_index(
            endpoint_name="kisanqna",
            index_name="workspace.default.kisanindex"
        )
    except Exception as e:
        index = None
    return groq_client, index

client, index = get_clients()

def speech_to_text(audio_file_like):
    """Converts audio to Hindi text using SpeechRecognition"""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file_like) as source:
            # Adjusting for noise slightly
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='hi-IN')
            return text
    except sr.UnknownValueError:
        return "Could not understand the audio."
    except Exception as e:
        st.error(f"STT Error: {str(e)}")
        return ""

def text_to_speech(text, lang='hi'):
    """Converts text to speech and returns an audio file stream"""
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception as e:
        st.error(f"TTS Error: {str(e)}")
        return None

def ask_farming_question_with_rag(question, language="hindi", num_results=3, image_base64=None):
    context_text = "No relevant context found."
    if index:
        try:
            results = index.similarity_search(
                query_text=question,
                columns=["id", "questions", "answers"],
                num_results=num_results
            )
            context_parts = []
            if results and 'result' in results and 'data_array' in results['result']:
                for result in results['result']['data_array']:
                    if isinstance(result, list) and len(result) >= 4:
                        q = result[1]
                        a = result[2]
                        context_parts.append(f"Q: {q}\nA: {a}")
            if context_parts:
                context_text = "\n\n".join(context_parts)
        except Exception:
            pass

    system_prompt = """You are a helpful farming assistant with expertise in agriculture, 
    crops, fertilizers, pest control, and farming techniques. 
    
    Use the provided context from the knowledge base to answer the question accurately. 
    If the context is relevant, base your answer on it. If not, use your general knowledge.
    Provide practical and accurate advice to farmers."""
    
    if language == "hindi":
        system_prompt += "\n\nIMPORTANT: Please respond in Hindi (Devanagari script)."
    else:
        system_prompt += "\n\nIMPORTANT: Please respond in English."
        
    user_message = f"""Context from knowledge base:
{context_text}

Question: {question}

Please provide a helpful answer based on the context above."""

    if client:
        try:
            if image_base64:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_message},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ]
                # Using the latest experimental Llama-4 Scout which actively supports Groq Vision tasks!
                model_to_use = "meta-llama/llama-4-scout-17b-16e-instruct"
            else:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
                model_to_use = "llama-3.3-70b-versatile"

            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model_to_use,
                temperature=0.7,
                max_tokens=1024
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    else:
        return "Groq client is not initialized."


# --- UI Setup ---
st.title("🌾 Kisan Q&A Assistant")
st.markdown("Ask farming questions via voice or text, and get AI-powered insights.")

st.markdown("---")
# Toggle for output language
output_lang = st.radio("Select Text Output Language:", ["Hindi", "English"], horizontal=True)

st.markdown("### 📷 Add Optional Image")
uploaded_image = st.file_uploader("Upload an image (optional) to analyze crops/leaves:", type=["jpg", "jpeg", "png"])
image_base64 = None
if uploaded_image:
    st.image(uploaded_image, width=300)
    image_base64 = base64.b64encode(uploaded_image.getvalue()).decode("utf-8")

st.markdown("### 🎤 Ask your question")
input_option = st.radio("Choose input method:", ["Record Audio", "Upload Audio", "Type Text"], horizontal=True)

question = None

if input_option == "Record Audio":
    st.info("Please speak your question in Hindi.")
    recorded_audio = st.audio_input("Record Question:")
    if recorded_audio:
        st.audio(recorded_audio)
        if st.button("Submit Recording"):
            with st.spinner("Transcribing your audio..."):
                transcription = speech_to_text(recorded_audio)
                if transcription and "Could not understand" not in transcription:
                    st.success(f"**Transcribed:** {transcription}")
                    question = transcription
                else:
                    st.warning("Could not transcribe audio. Please try again.")

elif input_option == "Upload Audio":
    st.info("Upload your Hindi question (WAV format recommended).")
    uploaded_audio = st.file_uploader("Upload Audio", type=["wav"])
    if uploaded_audio:
        st.audio(uploaded_audio)
        if st.button("Submit Uploaded File"):
            with st.spinner("Transcribing your audio..."):
                transcription = speech_to_text(uploaded_audio)
                if transcription and "Could not understand" not in transcription:
                    st.success(f"**Transcribed:** {transcription}")
                    question = transcription
                else:
                    st.warning("Could not transcribe audio. Please try again.")

elif input_option == "Type Text":
    text_input = st.text_input("Type your question (Hindi perfectly fine!):")
    if st.button("Submit Question"):
        if text_input:
            question = text_input
        elif image_base64:
            question = "कृपया इस तस्वीर का विश्लेषण करें और खेती से संबंधित सलाह दें।" if output_lang == "Hindi" else "Please analyze this image and provide crop farming advice."

st.markdown("---")

if question:
    st.markdown("### 💬 Answer")
    
    with st.spinner(f"Generating answer in {output_lang}..."):
        lang_str = "hindi" if output_lang == "Hindi" else "english"
        
        # 1. Answer Generation
        answer_text = ask_farming_question_with_rag(question, language=lang_str, image_base64=image_base64)
        st.write(answer_text)
        
    with st.spinner("Generating Hindi TTS Audio..."):
        # Always run Hindi TTS by default
        # If output is in English, we generate a separate translation for the Hindi TTS to avoid 
        # poor robotic pronunciation of English text by a Hindi TTS voice
        
        hindi_answer = answer_text
        if lang_str == "english":
            # If text is English, generate a quick Hindi translation specifically for the audio component
            try:
                trans_msg = f"Translate the following text to Hindi exactly: '{answer_text}'"
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": trans_msg}],
                    model="llama-3.3-70b-versatile",
                    temperature=0.3,
                    max_tokens=1024
                )
                hindi_answer = completion.choices[0].message.content
            except Exception:
                pass

        audio_fp = text_to_speech(hindi_answer, lang='hi')
        
        if audio_fp:
            st.success("Audio Generated! 🔊")
            st.audio(audio_fp, format="audio/mp3", autoplay=True)
            st.caption("Auto-playing Hindi TTS...")
        else:
            st.error("Could not generate TTS audio.")
