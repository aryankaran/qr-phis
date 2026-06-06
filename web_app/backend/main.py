import os
import math
import http.client
from urllib.parse import urlparse
import ipaddress
import numpy as np
import tensorflow as tf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import tldextract

# Suppress TensorFlow GPU warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# --- ADVANCED UTILITIES ---

def expand_url(url, depth=0):
    """Recursively follow redirects to find the final destination."""
    if depth > 5: return url # Max redirects
    try:
        parsed = urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=3) if parsed.scheme == 'https' else http.client.HTTPConnection(parsed.netloc, timeout=3)
        conn.request("HEAD", parsed.path or "/")
        res = conn.getresponse()
        if res.status in (301, 302, 303, 307, 308):
            new_url = res.getheader('location')
            if not urlparse(new_url).netloc: # Relative redirect
                new_url = f"{parsed.scheme}://{parsed.netloc}{new_url}"
            return expand_url(new_url, depth + 1)
        return url
    except:
        return url

def calculate_entropy(text):
    """Calculate Shannon entropy to detect random/DGA domains."""
    if not text: return 0
    prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
    return - sum([p * math.log(p) / math.log(2.0) for p in prob])

# --- MODEL CORE ---

MODEL_PATH = "models/model.tflite"
interpreter = None

def load_model():
    global interpreter
    if interpreter is None:
        try:
            interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
            interpreter.allocate_tensors()
            print(f"Model loaded from {MODEL_PATH}")
        except Exception as e:
            print(f"Error loading model: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield

app = FastAPI(title="Advanced QR Phishing Detector", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

class URLRequest(BaseModel):
    url: str

def feature_extraction(url):
    try:
        if not url.startswith(('http://', 'https://')): url = 'http://' + url
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}"
        parsed = urlparse(url)
        
        return [
            float(len(domain)),
            float(1 if any(c.isdigit() for c in domain) else 0), # Simplified for ML format
            float(1 if "@" in url else 0),
            float(len(url)),
            float(len([x for x in parsed.path.split("/") if x])),
            float(1 if '//' in parsed.path else 0),
            float(1 if parsed.scheme == 'https' else 0),
            float(1 if any(s in domain for s in ['tinyurl', 'bit.ly', 't.co', 'goo.gl']) else 0),
            float(1 if '-' in domain else 0)
        ]
    except:
        return [0.0] * 9

def heuristic_analysis(url, original_url):
    warnings = []
    risk_score = 0
    
    parsed = urlparse(url)
    ext = tldextract.extract(url)
    domain = ext.domain
    full_domain = f"{ext.domain}.{ext.suffix}"
    
    # 1. Redirect Detection
    if url != original_url:
        warnings.append(f"Redirect detected: {urlparse(original_url).netloc} -> {parsed.netloc}")
        risk_score += 1

    # 2. Entropy (Gibberish Detection)
    entropy = calculate_entropy(domain)
    if entropy > 3.8:
        warnings.append("Domain name looks randomly generated (High Entropy)")
        risk_score += 2

    # 3. TLD Reputation
    bad_tlds = ['.xyz', '.tk', '.ml', '.ga', '.cf', '.gq', '.pw', '.ws', '.top', '.zip', '.mov']
    if any(full_domain.endswith(t) for t in bad_tlds):
        warnings.append(f"Suspicious top-level domain detected")
        risk_score += 1

    # 4. Deep Path Scrutiny
    path = parsed.path.lower()
    dangerous_ext = ['.exe', '.scr', '.zip', '.rar', '.php', '.html', '.htm']
    if any(path.endswith(e) for e in dangerous_ext):
        warnings.append("URL points to a potentially sensitive file type")
        risk_score += 1

    # 5. Look-alike (Squatting) detection (Simplified)
    keywords = ['google', 'amazon', 'apple', 'microsoft', 'paypal', 'bank', 'login', 'secure']
    for kw in keywords:
        if kw in domain and kw != domain:
            warnings.append(f"Possible brand impersonation detected: '{kw}'")
            risk_score += 2

    return warnings, risk_score

@app.post("/api/detect")
async def analyze_url(request: URLRequest):
    raw_url = request.url.strip()
    if not raw_url: raise HTTPException(status_code=400, detail="Empty URL")

    # Step 1: Expand URL (The Redirect Chaser)
    final_url = expand_url(raw_url if raw_url.startswith('http') else 'http://' + raw_url)
    
    # Step 2: ML Inference
    features = feature_extraction(final_url)
    load_model()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    interpreter.set_tensor(input_details[0]['index'], np.array([features], dtype=np.float32))
    interpreter.invoke()
    prob = float(interpreter.get_tensor(output_details[0]['index'])[0][0])
    
    # Step 3: Heuristics
    warnings, h_score = heuristic_analysis(final_url, raw_url)
    
    # Logic: High ML score OR High Heuristic score
    is_phishing = prob > 0.5 or h_score >= 3
    
    return {
        "url": final_url,
        "original_url": raw_url,
        "prediction": "Phishing" if is_phishing else "Safe",
        "risk_score": min(h_score, 5),
        "probability": prob,
        "ml_result": "Phishing" if prob > 0.5 else "Safe",
        "heuristic_warnings": warnings
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
