from flask import Flask, jsonify
import os


app = Flask(__name__)


@app.get("/internal/health")
def health():
    return jsonify({"status": "ok", "service": "internal-api"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8081")))
