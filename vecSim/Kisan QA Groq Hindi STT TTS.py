# Databricks notebook source
# DBTITLE 1,System Overview
# MAGIC %md
# MAGIC # 🌾 Kisan Q&A System with RAG
# MAGIC
# MAGIC ## System Architecture
# MAGIC
# MAGIC This notebook implements a complete **Retrieval Augmented Generation (RAG)** pipeline for farming Q&A with Hindi language support:
# MAGIC
# MAGIC ### Components:
# MAGIC
# MAGIC 1. **Vector Search (Retrieval)** 🔍
# MAGIC    - Searches knowledge base (kisanindex) for relevant farming Q&A pairs
# MAGIC    - Returns top-k similar questions and answers based on semantic similarity
# MAGIC    - Endpoint: `kisanqna`
# MAGIC    - Index: `workspace.default.kisanindex`
# MAGIC
# MAGIC 2. **Groq LLM (Generation)** 🤖
# MAGIC    - Model: `llama-3.3-70b-versatile`
# MAGIC    - Uses retrieved context to generate accurate, contextual answers
# MAGIC    - Supports Hindi (Devanagari script) responses
# MAGIC
# MAGIC 3. **Hindi Text-to-Speech (TTS)** 🎤
# MAGIC    - Converts Hindi text answers to audio (MP3)
# MAGIC    - Uses gTTS (Google Text-to-Speech)
# MAGIC    - Saves to: `/Workspace/.../kisanQuery/audio_output/`
# MAGIC
# MAGIC 4. **Hindi Speech-to-Text (STT)** 🎧
# MAGIC    - Converts Hindi audio questions to text
# MAGIC    - Uses Google Speech Recognition
# MAGIC
# MAGIC ### Workflow:
# MAGIC ```
# MAGIC Question → Vector Search → Retrieve Context → Groq LLM → Hindi Answer → TTS → Audio
# MAGIC ```
# MAGIC
# MAGIC ### Usage:
# MAGIC
# MAGIC **RAG-powered Q&A:**
# MAGIC ```python
# MAGIC answer = ask_farming_question_with_rag("Your question here", language="hindi")
# MAGIC ```
# MAGIC
# MAGIC **With Audio Output:**
# MAGIC ```python
# MAGIC answer = ask_farming_question_with_rag("Your question", language="hindi")
# MAGIC audio_file = text_to_speech_hindi(answer, filename="my_audio.mp3")
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC **Run all cells in order, then use the custom question cells at the bottom to ask your own questions!**

# COMMAND ----------

# DBTITLE 1,Install Required Packages
# MAGIC %pip install groq gtts SpeechRecognition pydub databricks-vectorsearch
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Setup Groq LLM Client
from groq import Groq
import os

# Initialize Groq client with API key
GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

def ask_farming_question(question, language="hindi"):
    """
    Ask farming-related questions using Groq LLM
    """
    system_prompt = """You are a helpful farming assistant with expertise in agriculture, 
    crops, fertilizers, pest control, and farming techniques. Provide practical and 
    accurate advice to farmers."""
    
    if language == "hindi":
        system_prompt += " Please respond in Hindi (Devanagari script)."
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            model="llama-3.3-70b-versatile",  # Using Groq's fast LLM
            temperature=0.7,
            max_tokens=1024
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

print("✓ Groq LLM client initialized successfully!")

# COMMAND ----------

# DBTITLE 1,Setup Vector Search for RAG
from databricks.vector_search.client import VectorSearchClient

# Initialize the Vector Search client
vsc = VectorSearchClient(
    workspace_url="https://dbc-a6b1b203-95b7.cloud.databricks.com",
    personal_access_token="dapi9ae9552ee49526db039a9f8dff3eb100"
)

# Configuration
endpoint_name = "kisanqna"
index_name = "workspace.default.kisanindex"

# Get the index
index = vsc.get_index(
    endpoint_name=endpoint_name,
    index_name=index_name
)

# Check index status
status = index.describe()
index_status = status.get('status', {}).get('state', status.get('index_status', 'ONLINE'))
num_rows = status.get('num_indexed_rows', 0)

print("✓ Vector Search client initialized!")
print(f"  Index: {index_name}")
print(f"  Status: {index_status}")
print(f"  Indexed rows: {num_rows}")

# COMMAND ----------

# DBTITLE 1,RAG Function: Retrieve + Generate
def ask_farming_question_with_rag(question, language="hindi", num_results=3):
    """
    RAG-powered farming Q&A:
    1. Retrieve relevant context from Vector Search
    2. Generate answer using Groq LLM with context
    """
    print(f"🔍 Searching knowledge base for: {question}")
    
    # Step 1: Retrieve relevant context
    try:
        results = index.similarity_search(
            query_text=question,
            columns=["id", "questions", "answers"],
            num_results=num_results
        )
        
        # Extract context from results
        context_parts = []
        if results and 'result' in results and 'data_array' in results['result']:
            print(f"✓ Found {len(results['result']['data_array'])} relevant Q&A pairs")
            
            for i, result in enumerate(results['result']['data_array'], 1):
                if isinstance(result, list) and len(result) >= 4:
                    q = result[1]  # Question
                    a = result[2]  # Answer
                    score = result[3]  # Similarity score
                    
                    context_parts.append(f"Q: {q}\nA: {a}")
                    print(f"  [{i}] Score: {score:.4f}")
        else:
            print("⚠️ No results found in knowledge base")
            context_parts = []
    
    except Exception as e:
        print(f"⚠️ Vector search error: {str(e)}")
        context_parts = []
    
    # Step 2: Build context for LLM
    context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found."
    
    # Step 3: Generate answer with Groq LLM
    print(f"\n🤖 Generating answer with Groq LLM...")
    
    system_prompt = """You are a helpful farming assistant with expertise in agriculture, 
    crops, fertilizers, pest control, and farming techniques. 
    
    Use the provided context from the knowledge base to answer the question accurately. 
    If the context is relevant, base your answer on it. If not, use your general knowledge 
    but mention that you're providing general advice.
    
    Provide practical and accurate advice to farmers."""
    
    if language == "hindi":
        system_prompt += "\n\nIMPORTANT: Please respond in Hindi (Devanagari script)."
    
    user_message = f"""Context from knowledge base:
{context_text}

Question: {question}

Please provide a helpful answer based on the context above."""
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024
        )
        answer = chat_completion.choices[0].message.content
        print("✓ Answer generated successfully!\n")
        return answer
    except Exception as e:
        return f"Error generating answer: {str(e)}"

print("✓ RAG function ready! (Retrieve + Generate)")
print("  Use: ask_farming_question_with_rag(question, language='hindi')")
print("  This will search your knowledge base and generate contextual answers.")

# COMMAND ----------

# DBTITLE 1,Setup Hindi Text-to-Speech (TTS)
from gtts import gTTS
import io
from pydub import AudioSegment
from pydub.playback import play
import os

# Create output directory for audio files
output_dir = "/Workspace/Users/ee240002029@iiti.ac.in/Agri-OS/kisanQuery/audio_output"
os.makedirs(output_dir, exist_ok=True)

def text_to_speech_hindi(text, filename=None):
    """
    Convert Hindi text to speech using gTTS
    Saves to workspace directory for easy download
    """
    try:
        # Create TTS object for Hindi
        tts = gTTS(text=text, lang='hi', slow=False)
        
        # Generate filename if not provided
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hindi_audio_{timestamp}.mp3"
        
        # Ensure .mp3 extension
        if not filename.endswith('.mp3'):
            filename += '.mp3'
        
        # Full path in workspace
        save_path = os.path.join(output_dir, filename)
        
        # Save to file
        tts.save(save_path)
        print(f"✓ Audio saved to: {save_path}")
        print(f"✓ You can download this file from the workspace file browser")
        return save_path
    except Exception as e:
        print(f"TTS Error: {str(e)}")
        return None

print("✓ Hindi TTS function ready!")
print(f"✓ Audio files will be saved to: {output_dir}")

# COMMAND ----------

# DBTITLE 1,Setup Hindi Speech-to-Text (STT)
import speech_recognition as sr

def speech_to_text_hindi(audio_file_path):
    """
    Convert Hindi speech to text using SpeechRecognition
    """
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_file_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            # Record the audio
            audio_data = recognizer.record(source)
            
            # Recognize speech using Google Speech Recognition with Hindi language
            text = recognizer.recognize_google(audio_data, language='hi-IN')
            return text
    except sr.UnknownValueError:
        return "Could not understand the audio"
    except sr.RequestError as e:
        return f"Could not request results; {e}"
    except Exception as e:
        return f"STT Error: {str(e)}"

print("✓ Hindi STT function ready!")

# COMMAND ----------

# DBTITLE 1,Test Farming Q&A with Groq LLM
# Test farming questions
test_questions = [
    "फसलों में कीटों को कैसे नियंत्रित करें?",  # How to control pests in crops?
    "गेहूं के लिए सबसे अच्छा उर्वरक कौन सा है?",  # What is the best fertilizer for wheat?
    "फसल की उपज कैसे बढ़ाएं?"  # How to increase crop yield?
]

print("="*80)
print("GROQ LLM FARMING Q&A TEST (Hindi)")
print("="*80)

for i, question in enumerate(test_questions, 1):
    print(f"\n{'='*80}")
    print(f"प्रश्न #{i}: {question}")
    print('='*80)
    
    # Get answer from Groq LLM
    answer = ask_farming_question(question, language="hindi")
    print(f"\nउत्तर:\n{answer}")
    print()

print(f"\n{'='*80}")
print("✓ Test completed!")
print('='*80)

# COMMAND ----------

# DBTITLE 1,Complete Demo: Question → LLM → TTS
# Complete workflow demonstration
print("="*80)
print("COMPLETE DEMO: Question → Groq LLM → Hindi TTS")
print("="*80)

# Sample question
question = "टमाटर की फसल में पानी कितनी बार देना चाहिए?"  # How often should tomatoes be watered?
print(f"\nप्रश्न: {question}")

# Step 1: Get answer from Groq LLM
print("\n[Step 1] Querying Groq LLM...")
answer = ask_farming_question(question, language="hindi")
print(f"\nउत्तर:\n{answer}")

# Step 2: Convert answer to speech
print("\n[Step 2] Converting answer to Hindi speech...")
audio_file = text_to_speech_hindi(answer, filename="tomato_watering_advice.mp3")

if audio_file:
    print(f"\n✓ Complete workflow successful!")
    print(f"\n📢 Download your audio file from:")
    print(f"   {audio_file}")
    print("\n📂 Navigate to: Agri-OS/kisanQuery/audio_output/ folder in workspace")
else:
    print("\n✗ TTS conversion failed")

print("\n" + "="*80)

# COMMAND ----------

# DBTITLE 1,Ask Your Own Question (Custom)
# === CUSTOMIZE YOUR QUESTION HERE ===
my_question = "धान की फसल के लिए सबसे अच्छा समय कौन सा है?"  # What is the best time for rice crop?
audio_filename = "rice_planting_time.mp3"  # Name for your audio file
# ====================================

print("🌾 KISAN Q&A SYSTEM 🌾")
print("="*80)
print("")
print(f"💬 Question: {my_question}")
print("")

# Get answer from Groq LLM
print("⏳ Getting answer from Groq AI...")
answer = ask_farming_question(my_question, language="hindi")

print("")
print("✅ Answer:")
print('-'*80)
print(answer)
print('-'*80)

# Generate audio
print("")
print("🎤 Generating Hindi audio...")
audio_path = text_to_speech_hindi(answer, filename=audio_filename)

if audio_path:
    print("")
    print("✅ SUCCESS! Audio file ready for download:")
    print(f"   📂 {audio_path}")
    print("")
    print("👉 To download: Workspace > Agri-OS > kisanQuery > audio_output")
else:
    print("")
    print("❌ Failed to generate audio")

print("")
print("="*80)

# COMMAND ----------

# DBTITLE 1,Test RAG System (Retrieve + Generate)
# Test RAG with farming questions
test_questions = [
    "How to control pests in crops?",
    "What is the best fertilizer for wheat?",
    "How to increase crop yield?"
]

print("🌾" * 40)
print("RAG SYSTEM TEST: Vector Search + Groq LLM")
print("🌾" * 40)
print()

for i, question in enumerate(test_questions, 1):
    print(f"\n{'='*80}")
    print(f"TEST #{i}: {question}")
    print('='*80)
    print()
    
    # Use RAG to get answer
    answer = ask_farming_question_with_rag(question, language="hindi")
    
    print(f"\n💬 Final Answer:")
    print('-'*80)
    print(answer)
    print('-'*80)
    print()

print(f"\n{'='*80}")
print("✓ RAG test completed!")
print('='*80)

# COMMAND ----------

# DBTITLE 1,Ask Your Own Question with RAG
# ============================================
# CUSTOMIZE YOUR QUESTION HERE
# ============================================
my_question = "What are the best practices for rice cultivation?"
audio_filename = "custom_farming_advice.mp3"
# ============================================

print("🌾" * 40)
print("KISAN Q&A SYSTEM WITH RAG")
print("🌾" * 40)
print()
print(f"💬 Your Question: {my_question}")
print("="*80)
print()

# Step 1: Search knowledge base + Generate answer with RAG
print("🚀 Processing with RAG (Vector Search + Groq LLM)...")
print()
answer = ask_farming_question_with_rag(my_question, language="hindi", num_results=3)

print(f"\n✅ Answer (in Hindi):")
print('-'*80)
print(answer)
print('-'*80)

# Step 2: Generate audio
print("\n🎤 Generating Hindi audio...")
audio_path = text_to_speech_hindi(answer, filename=audio_filename)

if audio_path:
    print("\n✅ SUCCESS! Your farming advice is ready!")
    print(f"\n📢 Audio saved to:")
    print(f"   📂 {audio_path}")
    print("\n👉 Download from: Workspace > Agri-OS > kisanQuery > audio_output")
else:
    print("\n❌ Failed to generate audio")

print("\n" + "="*80)
print("✨ Powered by: Vector Search + Groq LLM + gTTS")
print("="*80)

# COMMAND ----------

# DBTITLE 1,Complete RAG Demo: Retrieve → Generate → TTS
# Complete RAG workflow with audio output
print("🌾" * 40)
print("COMPLETE RAG WORKFLOW: Vector Search + Groq + Hindi TTS")
print("🌾" * 40)
print()

# Sample question
question = "How should I water tomato crops?"  
print(f"💬 Question: {question}")
print("="*80)
print()

# Step 1: RAG (Retrieve + Generate)
print("🚀 Starting RAG process...")
print()
answer = ask_farming_question_with_rag(question, language="hindi")

print(f"\n📝 Answer in Hindi:")
print('-'*80)
print(answer)
print('-'*80)

# Step 2: Convert to speech
print("\n🎤 Converting to Hindi speech...")
audio_file = text_to_speech_hindi(answer, filename="rag_tomato_advice.mp3")

if audio_file:
    print(f"\n✅ COMPLETE WORKFLOW SUCCESSFUL!")
    print(f"\n📢 Audio file saved:")
    print(f"   {audio_file}")
    print("\n📂 Download from: Agri-OS/kisanQuery/audio_output/")
else:
    print("\n❌ TTS conversion failed")

print("\n" + "="*80)