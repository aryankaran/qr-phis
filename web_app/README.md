# 🌐 QR Phishing Detector Web App

This is a simple web application that uses the trained TFLite model from the mobile project to detect phishing URLs from QR codes or manual input.

## Features
- **Live QR Scanning**: Scan QR codes directly from your browser using your camera.
- **ML Detection**: Uses the pre-trained TFLite model for URL analysis.
- **Optimized Heuristics**: Added rule-based checks for common phishing patterns (suspicious keywords, high digit counts, etc.) to enhance the detection accuracy.
- **Responsive UI**: Works on desktop and mobile browsers.

## Project Structure
- `backend/`: FastAPI server for model inference.
- `frontend/`: Simple HTML/JS interface.

## Getting Started

### 1. Start the Backend
Navigate to the backend directory and install dependencies:
```bash
cd web_app/backend
pip install -r requirements.txt
python main.py
```
The API will start at `http://localhost:8000`.

### 2. Start the Frontend
You can serve the frontend using any static file server, for example:
```bash
cd web_app/frontend
python3 -m http.server 8080
```
Then open `http://localhost:8080` in your browser.

## Optimization Notes
In addition to the ML model, we've implemented a **Heuristic Analysis** layer that flags:
- Suspicious keywords like "login", "verify", "secure" in the URL.
- Excessive number of subdomains.
- High density of digits in the domain name.
- Non-HTTPS schemes for sensitive-looking URLs.
