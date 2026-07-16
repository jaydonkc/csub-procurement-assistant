import json
from types import SimpleNamespace
from uuid import uuid4

from flask import Flask, Response, request
from flask_cors import CORS
from dotenv import load_dotenv

from backend.lambda_function import handler

load_dotenv()

app = Flask(__name__)
CORS(app)

def _invoke_lambda(path: str) -> Response:
    event = {
        "requestContext": {"http": {"method": request.method, "path": path}},
        "rawPath": path,
    }
    if request.method == "POST":
        event["body"] = json.dumps(request.get_json(silent=True) or {})
    result = handler(
        event,
        SimpleNamespace(aws_request_id=f"local-{uuid4()}"),
    )
    headers = dict(result.get("headers") or {})
    return Response(
        result.get("body", ""),
        status=result.get("statusCode", 500),
        headers=headers,
    )


@app.get("/")
def homepage():
    return _invoke_lambda("/")


@app.get("/v1/health")
def health():
    return _invoke_lambda("/v1/health")


@app.route("/v1/chat", methods=["POST", "OPTIONS"])
def chat():
    return _invoke_lambda("/v1/chat")


if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False, port=5002)
