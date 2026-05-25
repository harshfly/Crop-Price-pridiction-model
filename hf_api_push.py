import json
import urllib.request
import base64

token = "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"
repo_id = "haarsh0910/krishimitra-ai"
url = f"https://huggingface.co/api/spaces/{repo_id}/commit/main"

with open("Dockerfile", "rb") as f:
    content = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "commit_message": "Fix HF Space port issue (8000 to 7860)",
    "operations": [
        {
            "operation": "addOrUpdate",
            "path": "Dockerfile",
            "content": content,
            "encoding": "base64"
        }
    ]
}

req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Content-Type", "application/json")

try:
    with urllib.request.urlopen(req) as response:
        print("Success:", response.read().decode("utf-8"))
except Exception as e:
    print("Error:", str(e))
    if hasattr(e, "read"):
        print("Response:", e.read().decode("utf-8"))
