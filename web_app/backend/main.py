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
    Additional heuristic rules to optimize detection beyond the ML model.
    """
    warnings = []
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Check for suspicious keywords in domain or path
    suspicious_keywords = ['login', 'verify', 'account', 'secure', 'banking', 'update', 'signin']
    for kw in suspicious_keywords:
        if kw in url.lower():
            warnings.append(f"Contains suspicious keyword: '{kw}'")
            
    # Check for long subdomains
    if domain.count('.') > 3:
        warnings.append("High number of subdomains detected")
        
    # Check for digits in domain
    digits = sum(c.isdigit() for c in domain)
    if digits > 5:
        warnings.append("High number of digits in domain")

    return warnings

class URLRequest(BaseModel):
    url: str

@app.on_event("startup")
async def startup_event():
    load_model()

@app.get("/")
async def root():
    return {"message": "QR Phishing Detector API is running"}

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

    # Prepare input data [1, 9]
    input_data = np.array([features], dtype=np.float32)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]['index'])
    probability = float(output_data[0][0])
    is_phishing_ml = probability >= 0.5
    
    # Perform Heuristic Analysis
    warnings = heuristic_analysis(url)
    
    # Combined result
    result = "Phishing" if (is_phishing_ml or len(warnings) > 2) else "Safe"
    
    return {
        "url": url,
        "prediction": result,
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
