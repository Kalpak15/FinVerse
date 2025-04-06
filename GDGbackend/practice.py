# ------------------------------------
# Part 1: Imports & Setup
# ------------------------------------
import os
import sys
import json
import re
import time
import fitz  # PyMuPDF for PDF extraction
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime

# ------------------------------------
# Part 2: Environment Variables & API Keys
# ------------------------------------
load_dotenv()


port = int(os.getenv("FLASK_PORT", 5000))

# Replace with your actual keys
os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN")
gemini_api_key = os.getenv("GOOGLE_API_KEY")

# ------------------------------------
# Part 3: Logging Configuration
# ------------------------------------
# Setup logging - Using ASCII symbols instead of Unicode emojis for Windows compatibility
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"finance_chatbot_{datetime.now().strftime('%Y%m%d')}.log")

# Configure file handler with UTF-8 encoding
file_handler = logging.FileHandler(log_file, encoding='utf-8')
console_handler = logging.StreamHandler()

# Set formatter without Unicode characters for better Windows compatibility
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(log_formatter)
console_handler.setFormatter(log_formatter)

# Configure logger
logger = logging.getLogger("finance_chatbot")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ------------------------------------
# Part 4: PDF Extraction
# ------------------------------------
pdf_folder = "books"
output_text_file = "datatext.txt"

def extract_pdfs():
    if not os.path.exists(pdf_folder):
        logger.error("Error: PDF folder not found!")
        return False

    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        logger.error("Error: No PDF files found in the folder!")
        return False

    logger.info("Extracting text from PDFs...")
    with open(output_text_file, "w", encoding="utf-8") as txt_file:
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_folder, pdf_file)
            logger.info(f"Processing: {pdf_file}")
            
            try:
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    text = doc[page_num].get_text()
                    txt_file.write(text + "\n" + "=" * 80 + "\n")
                logger.info(f"[SUCCESS] Extracted text from {pdf_file}")
            except Exception as e:
                logger.error(f"Error opening {pdf_file}: {e}")
                continue
    logger.info(f"All PDFs processed! Extracted text saved in '{output_text_file}'.")
    return True

if not os.path.exists(output_text_file):
    extract_pdfs()
else:
    logger.info(f"Found existing '{output_text_file}'. Skipping PDF extraction.")

# ------------------------------------
# Part 5: Persistent Chat History
# ------------------------------------
history_file = "chat_history.json"

def load_chat_history():
    """Load chat history from JSON file and convert to Human/AI messages."""
    chat_history = ChatMessageHistory()
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history_data = json.load(f)
            
            for msg in history_data:
                if msg.get("type") == "human":
                    chat_history.add_user_message(msg.get("content", ""))
                elif msg.get("type") == "ai":
                    chat_history.add_ai_message(msg.get("content", ""))
            
            logger.info("Loaded existing chat history.")
        except json.JSONDecodeError:
            logger.warning("Chat history file is empty or corrupted. Starting fresh.")
    else:
        logger.info("No previous chat history found. Starting fresh.")
    
    return chat_history

def save_chat_history(history):
    """Save chat history as JSON."""
    history_data = [{"type": "human" if isinstance(msg, HumanMessage) else "ai", "content": msg.content} for msg in history.messages]
    
    with open(history_file, "w") as f:
        json.dump(history_data, f, indent=4)

chat_history = load_chat_history()

# ------------------------------------
# Part 6: Persistent Retriever & Embeddings
# ------------------------------------
def initialize_retriever():
    """Initialize and return the document retriever."""
    if not os.path.exists(output_text_file):
        logger.error(f"Error: Text file '{output_text_file}' not found!")
        return None
        
    loader = TextLoader(output_text_file, encoding="utf-8")
    documents = loader.load()

    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)

    # Embedding and vector store setup
    persist_directory_gemini = "retriever_store_gemini"
    if os.path.exists(persist_directory_gemini) and os.listdir(persist_directory_gemini):
        logger.info("Loaded existing Gemini retriever store.")
        vectorstore = Chroma(persist_directory=persist_directory_gemini, embedding_function=GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=gemini_api_key))
    else:
        logger.info("Creating new Gemini retriever store...")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=gemini_api_key)
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=persist_directory_gemini)
        logger.info("Created and saved new retriever store!")

    return vectorstore.as_retriever(search_kwargs={"k": 5})

retriever = initialize_retriever()
if retriever is None:
    logger.error("Failed to initialize retriever. Exiting.")
    sys.exit(1)

# ------------------------------------
# Part 7: Finance-Specific Intent Detection
# ------------------------------------
def detect_finance_intent(user_input):
    """Detect specific finance intents to provide more targeted responses."""
    # Map of intents to their regex patterns
    intents = {
        "investment_advice": r'\b(invest|stock|bond|etf|portfolio|dividend|market|return|risk|asset)\b',
        "budgeting": r'\b(budget|spend|saving|expense|income|track|money|financial plan|cash flow)\b',
        "debt": r'\b(debt|loan|credit|mortgage|interest|payment|borrow|lend|finance|leverage)\b',
        "retirement": r'\b(retire|401k|ira|pension|social security|annuity|future|nest egg)\b',
        "tax": r'\b(tax|deduction|filing|return|irs|write-off|capital gain|liability|exemption)\b',
        "insurance": r'\b(insurance|policy|coverage|premium|deductible|claim|risk management|protection)\b',
        "financial_planning": r'\b(plan|goal|future|strategy|wealth|net worth|financial freedom|independence)\b',
        "calculator": r'\b(calculate|computation|formula|interest|payment|return|yield|rate|compound)\b',
        "general": r'.*'  # Fallback
    }
    
    # Check each intent pattern against the user input
    for intent, pattern in intents.items():
        if re.search(pattern, user_input.lower()):
            logger.info(f"Detected intent: {intent} for query: {user_input[:50]}...")
            return intent
    
    logger.info(f"No specific intent detected, using general intent for: {user_input[:50]}...")
    return "general"

# ------------------------------------
# Part 8: Custom System Prompts Based on Intent
# ------------------------------------
def get_system_prompt(intent):
    """Return a customized system prompt based on detected intent."""
    base_prompt = (
        "You are FinVerse, an advanced financial assistant specializing in personal finance, investments, and money management. "
        "Respond in a concise, professional manner with useful information and actionable advice. "
    )
    
    intent_prompts = {
        "investment_advice": (
            "Focus on providing balanced investment information. "
            "Always mention that past performance doesn't guarantee future results. "
            "Suggest diversification and long-term horizons when discussing investments. "
            "Never recommend specific stocks or make market predictions. "
            "Use bullet points to highlight key investment principles when appropriate."
        ),
        "budgeting": (
            "Provide practical budgeting advice using common frameworks like 50/30/20. "
            "Suggest tracking methods and expense categories. "
            "Focus on sustainable habits rather than extreme measures. "
            "Recommend automated savings and budgeting tools when relevant."
        ),
        "debt": (
            "Explain debt strategies like snowball vs. avalanche methods. "
            "Prioritize high-interest debt payoff. "
            "Suggest when debt consolidation might make sense. "
            "Emphasize the psychological aspects of debt reduction."
        ),
        "retirement": (
            "Explain retirement account types and contribution limits. "
            "Discuss the power of compound interest and early saving. "
            "Mention the importance of diversification in retirement accounts. "
            "Stress the balance between current lifestyle and future security."
        ),
        "tax": (
            "Provide general tax information while disclaiming that you're not a tax professional. "
            "Suggest common deductions people might overlook. "
            "Recommend consulting a CPA for specific tax situations. "
            "Explain tax concepts in simple terms with examples when possible."
        ),
        "insurance": (
            "Explain insurance concepts clearly and discuss appropriate coverage levels. "
            "Highlight the importance of adequate protection against major risks. "
            "Mention the balance between premiums and coverage. "
            "Stress the importance of reviewing policies regularly."
        ),
        "financial_planning": (
            "Focus on holistic financial planning principles. "
            "Emphasize goal-setting and prioritization of financial objectives. "
            "Discuss emergency funds, insurance, investments, and estate planning together. "
            "Highlight the importance of regular financial check-ups."
        ),
        "calculator": (
            "Provide clear calculations with explanations of the formulas used. "
            "Break down complex financial math into understandable steps. "
            "Include both the numerical result and its practical implications. "
            "Explain how different variables affect the outcome."
        ),
        "general": (
            "Provide clear and concise responses on general financial topics. "
            "Explain financial concepts in simple terms. "
            "Offer educational resources when appropriate. "
            "Balance technical accuracy with practical usefulness."
        )
    }
    
    prompt = base_prompt + intent_prompts.get(intent, intent_prompts["general"])
    prompt += "\n\nUse the retrieved context below to inform your response:\n\n{context}"
    
    return prompt

# ------------------------------------
# Part 9: LLM & Prompt Configuration
# ------------------------------------
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_api_key)

# Default system prompt (will be updated based on intent)
system_prompt = get_system_prompt("general")

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

stuff_chain = create_stuff_documents_chain(llm=llm, prompt=prompt, document_variable_name="context")

# ------------------------------------
# Part 10: Financial Calculator Functions
# ------------------------------------
def compound_interest_calculator(principal, rate, time, compounds_per_year=1):
    """Calculate compound interest: A = P(1 + r/n)^(nt)"""
    rate = rate / 100  # Convert percentage to decimal
    amount = principal * (1 + rate/compounds_per_year)**(compounds_per_year*time)
    return amount

def loan_payment_calculator(principal, rate, years):
    """Calculate monthly loan payment using the formula: PMT = P(r(1+r)^n)/((1+r)^n-1)"""
    rate = rate / 100 / 12  # Monthly interest rate in decimal
    n = years * 12  # Total number of payments
    payment = principal * (rate * (1 + rate)**n) / ((1 + rate)**n - 1)
    return payment

def retirement_calculator(current_savings, monthly_contribution, years, annual_return):
    """Calculate retirement savings with regular contributions"""
    annual_return = annual_return / 100
    monthly_return = annual_return / 12
    months = years * 12
    
    future_value = current_savings * (1 + monthly_return)**months
    
    # Calculate future value of the annuity (monthly contributions)
    annuity_value = monthly_contribution * ((1 + monthly_return)**months - 1) / monthly_return
    
    return future_value + annuity_value

# ------------------------------------
# Part 11: Financial Parameter Extraction
# ------------------------------------
def extract_financial_parameters(user_input):
    """Extract financial parameters from user input for calculator functions."""
    # Extract parameters for compound interest calculation
    compound_pattern = r'(?i)compound\s+interest.*?(\d+[\d,]*\.?\d*).*?(\d+\.?\d*)%.*?(\d+\.?\d*)\s*years?'
    compound_match = re.search(compound_pattern, user_input)
    
    if compound_match:
        principal = float(compound_match.group(1).replace(',', ''))
        rate = float(compound_match.group(2))
        time = float(compound_match.group(3))
        result = compound_interest_calculator(principal, rate, time)
        return f"## Compound Interest Calculation\n\n* Initial principal: ${principal:,.2f}\n* Interest rate: {rate}%\n* Time period: {time} years\n* Final amount: ${result:,.2f}"
    
    # Extract parameters for loan payment calculation
    loan_pattern = r'(?i)loan\s+payment.*?(\d+[\d,]*\.?\d*).*?(\d+\.?\d*)%.*?(\d+\.?\d*)\s*years?'
    loan_match = re.search(loan_pattern, user_input)
    
    if loan_match:
        principal = float(loan_match.group(1).replace(',', ''))
        rate = float(loan_match.group(2))
        years = float(loan_match.group(3))
        payment = loan_payment_calculator(principal, rate, years)
        total_paid = payment * 12 * years
        interest_paid = total_paid - principal
        return f"## Loan Payment Calculation\n\n* Loan amount: ${principal:,.2f}\n* Interest rate: {rate}%\n* Loan term: {years} years\n* Monthly payment: ${payment:,.2f}\n* Total paid: ${total_paid:,.2f}\n* Total interest: ${interest_paid:,.2f}"
    
    # Extract parameters for retirement calculation
    retirement_pattern = r'(?i)retirement\s+savings.*?(\d+[\d,]*\.?\d*).*?(\d+[\d,]*\.?\d*).*?(\d+\.?\d*)\s*years?.*?(\d+\.?\d*)%'
    retirement_match = re.search(retirement_pattern, user_input)
    
    if retirement_match:
        current_savings = float(retirement_match.group(1).replace(',', ''))
        monthly_contribution = float(retirement_match.group(2).replace(',', ''))
        years = float(retirement_match.group(3))
        annual_return = float(retirement_match.group(4))
        result = retirement_calculator(current_savings, monthly_contribution, years, annual_return)
        return f"## Retirement Savings Projection\n\n* Current savings: ${current_savings:,.2f}\n* Monthly contribution: ${monthly_contribution:,.2f}\n* Time period: {years} years\n* Expected annual return: {annual_return}%\n* Projected savings: ${result:,.2f}"
    
    # No financial calculation detected
    return None

# ------------------------------------
# Part 12: Chatbot Core Function
# ------------------------------------
def chat_with_ai(user_input):
    """Generate AI response using LLM and retriever with improved error handling."""
    start_time = time.time()
    try:
        # Check for calculator requests first
        calculation_result = extract_financial_parameters(user_input)
        if calculation_result:
            logger.info(f"Processed calculator request in {time.time() - start_time:.2f}s")
            return calculation_result
        
        # Get intent and customize prompt
        intent = detect_finance_intent(user_input)
        system_prompt = get_system_prompt(intent)
        
        # Update prompt template with intent-specific system prompt
        updated_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Create a new chain with the updated prompt
        custom_chain = create_stuff_documents_chain(llm=llm, prompt=updated_prompt, document_variable_name="context")
        
        # Log the incoming query
        logger.info(f"Processing query with intent '{intent}': {user_input}")
        
        # Get relevant documents
        retrieved_docs = retriever.invoke(user_input)
        processed_docs = [Document(page_content=doc.page_content if hasattr(doc, "page_content") else str(doc)) for doc in retrieved_docs]
        
        # Use a limited chat history to prevent context length issues
        max_history = 4  # Only keep last 4 messages
        trimmed_history = chat_history.messages[-max_history:] if len(chat_history.messages) > max_history else chat_history.messages
        
        # Prepare input data with parameters
        input_data = {
            "input": user_input,
            "context": processed_docs,
            "history": trimmed_history,
            "parameters": {"max_new_tokens": 500, "temperature": 0.7}
        }
        
        # Get response
        response = custom_chain.invoke(input_data)
        response_text = response if isinstance(response, str) else response.content
        
        # Update history
        chat_history.add_user_message(user_input)
        chat_history.add_ai_message(response_text)
        save_chat_history(chat_history)
        
        # Log completion time
        execution_time = time.time() - start_time
        logger.info(f"Generated response in {execution_time:.2f}s")
        
        return response_text
    except Exception as e:
        error_message = f"Error: {str(e)}"
        logger.error(error_message)
        # Log the full error for debugging
        import traceback
        logger.error(traceback.format_exc())
        return "I'm sorry, I encountered an issue processing your request. Please try again with a different question."

# ------------------------------------
# Part 13: Flask API for Frontend
# ------------------------------------
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/chat', methods=['POST'])
def handle_chat():
    """API endpoint to handle chat requests from the frontend."""
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'message': 'Please provide a message.'}), 400
        
        # Generate response
        response = chat_with_ai(user_message)
        
        return jsonify({'message': response})
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({'message': 'An error occurred. Please try again.'}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """API endpoint to clear chat history."""
    try:
        global chat_history
        chat_history = ChatMessageHistory()
        save_chat_history(chat_history)
        return jsonify({'message': 'Chat history cleared successfully.'}), 200
    except Exception as e:
        logger.error(f"Clear history error: {str(e)}")
        return jsonify({'message': 'Error clearing chat history.'}), 500

# ------------------------------------
# Part 14: Main Function
# ------------------------------------
if __name__ == "__main__":
    # Run as API server when executed directly
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Finance Chatbot API server on port {port}")
    print(f"Flask Chatbot API running on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

