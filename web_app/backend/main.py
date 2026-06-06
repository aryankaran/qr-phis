from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import tensorflow as tf
from urllib.parse import urlparse
import ipaddress
import os

app = FastAPI(title="QR Phishing Detector API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to the TFLite model
MODEL_PATH = "models/model.tflite"

# Global variable for the interpreter
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

import tldextract

def feature_extraction(url):
    """
    Extracts the 9 features used by the original model.
    """
    try:
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}"
        parsed = urlparse(url)
        scheme = parsed.scheme
        path = parsed.path

        # 1. domain_length
        domain_length = len(domain)

        # 2. having ip address
        try:
            ipaddress.ip_address(domain)
            have_ip = 1
        except:
            have_ip = 0

        # 3. having @ symbol
        have_at = 1 if "@" in url else 0

        # 4. url length
        url_length = len(url)
                             
        # 5. url depth
        url_depth = len([x for x in path.split("/") if x != ""])

        # 6. redirection
        redirection = 1 if '//' in path else 0

        # 7. https in domain
        https_domain = 1 if 'https' in scheme else 0

        # 8. tinyurl
        tiny_url = 1 if ('tinyurl' in domain or 'bit.ly' in domain) else 0

        # 9. prefix or suffix in domain
        prefix_suffix = 1 if '-' in domain else 0

        return [
            float(domain_length),
            float(have_ip),
            float(have_at),
            float(url_length),
            float(url_depth),
            float(redirection),
            float(https_domain),
            float(tiny_url),
            float(prefix_suffix)
        ]
    except Exception as e:
        print(f"[ERROR] Failed to parse {url}: {e}")
        return [0.0] * 9

def heuristic_analysis(url):
    """
    Enhanced heuristic rules to optimize detection.
    Returns a dictionary with warnings and a risk score.
    """
    warnings = []
    risk_score = 0
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()
    
    # 1. Suspicious keywords (High Risk)
    high_risk_keywords = ['login', 'verify', 'account', 'secure', 'banking', 'update', 'signin', 'wp-admin', 'cmd', 'auth']
    for kw in high_risk_keywords:
        if kw in url.lower():
            warnings.append(f"High risk keyword detected: '{kw}'")
            risk_score += 2
            
    # 2. Domain complexity (Medium Risk)
    if domain.count('.') > 3:
        warnings.append("Suspiciously deep subdomain structure")
        risk_score += 1
        
    # 3. Digits in domain
    digits = sum(c.isdigit() for c in domain)
    if len(domain) > 0 and (digits / len(domain)) > 0.3:
        warnings.append("High ratio of digits in domain")
        risk_score += 1

    # 4. Sensitive TLDs (Low/Medium Risk depending on context)
    suspicious_tlds = ['.xyz', '.tk', '.ml', '.ga', '.cf', '.gq', '.pw', '.ws', '.icu', '.top']
    for tld in suspicious_tlds:
        if domain.endswith(tld):
            warnings.append(f"Domain uses a suspicious TLD: '{tld}'")
            risk_score += 1
            break

    # 5. HTTPS check for sensitive URLs
    if parsed.scheme != 'https' and any(kw in url.lower() for kw in ['login', 'bank', 'secure']):
        warnings.append("Sensitive URL over non-secure (HTTP) connection")
        risk_score += 2

    return warnings, risk_score

@app.post("/analyze")
async def analyze_url(request: URLRequest):
    url = request.url
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Extract features for ML model
    features = feature_extraction(url)
    
    # Perform ML Inference
    load_model()
    if interpreter is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    input_data = np.array([features], dtype=np.float32)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]['index'])
    probability = float(output_data[0][0])
    is_phishing_ml = probability >= 0.5
    
    # Perform Enhanced Heuristic Analysis
    warnings, risk_score = heuristic_analysis(url)
    
    # Combined result logic:
    # If ML says phishing OR heuristics find significant risk
    is_phishing = is_phishing_ml or risk_score >= 3
    
    return {
        "url": url,
        "prediction": "Phishing" if is_phishing else "Safe",
        "risk_score": risk_score,
        "probability": probability,
        "ml_result": "Phishing" if is_phishing_ml else "Safe",
        "heuristic_warnings": warnings,
        "features": {
            "domain_length": features[0],
            "have_ip": bool(features[1]),
            "have_at": bool(features[2]),
            "url_length": features[3],
            "url_depth": features[4],
            "redirection": bool(features[5]),
            "https_domain": bool(features[6]),
            "tiny_url": bool(features[7]),
            "prefix_suffix": bool(features[8])
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
