"""
User Service API
Incorrectly states password is stored in plain text, but code hashes it.
"""
from flask import Flask, request

app = Flask(__name__)

# User registration endpoint
@app.route("/register", methods=["POST"])
def register():
    # BUG: Documentation says plain storage, but actually hashes
    data = request.json
    password = hash(data["password"])
    return {"status": "registered"}
