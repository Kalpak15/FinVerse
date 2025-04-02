from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# Import the chatbot function from practice.py
# (Ensure that practice.py defines chat_with_ai at module level)
from practice import chat_with_ai, logger, clear_history

app = Flask(__name__)
CORS(app)  # Enable CORS to allow your React frontend to communicate with this API

@app.route('/chat', methods=['POST'])
def chat_api():
    try:
        data = request.get_json()
        user_input = data.get("message")
        if not user_input:
            return jsonify({"error": "No message provided"}), 400

        # Log the incoming request
        logger.info(f"Received chat request: {user_input[:50]}...")
        
        # Use the chat_with_ai function from practice.py to generate a response
        response_text = chat_with_ai(user_input)
        return jsonify({"message": response_text})
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        return jsonify({"error": "An error occurred processing your request"}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history_api():
    try:
        clear_history()
        return jsonify({"message": "Chat history cleared successfully"}), 200
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        return jsonify({"error": "Failed to clear history"}), 500

if __name__ == "__main__":
    # You can set FLASK_PORT in an environment variable or default to 5000
    port = int(os.getenv("FLASK_PORT", 5000))
    print(f"Flask Chatbot API running on port {port}...")
    logger.info(f"Starting Finance Chatbot API server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)