from flask import Flask
from flask import request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def homepage():
    return "CSUB Procurement Assistant API"

@app.route('/chat', methods = ['POST'])
def chat():
    data = request.get_json()
    user_message = request.json.get("message", "")

    return jsonify({
        "answer": f"Hi I am working: {user_message}"
    })               

if __name__ == "__main__":
    app.run(debug=True, port=5000)