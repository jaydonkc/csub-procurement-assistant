from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.get("/")
def homepage():
    return jsonify({"service": "CSUB Procurement Assistant API", "status": "ok"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    user_message = str(data.get("message", "")).strip()

    if not user_message:
        return jsonify({"error": "Message is required."}), 400

    return jsonify({
        "answer": (
            "I can help with CSUB procurement questions. "
            f"You asked: {user_message}"
        )
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
