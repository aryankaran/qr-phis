# 🛡️ QR Phishing Detector Roadmap

## Phase 1: Enhancement & Optimization (Backend)
- [ ] **Advanced Feature Engineering**:
    - Add features like TLD analysis, digit-to-letter ratio, presence of sensitive keywords (e.g., 'login', 'verify', 'bank'), and subdomain depth.
    - Use `tldextract` for more accurate domain parsing.
- [ ] **Model Upgrading**:
    - Evaluate Random Forest, XGBoost, or LightGBM which often outperform MLPs for tabular URL features.
    - Implement cross-validation for more robust performance metrics.
- [ ] **Inference Service**:
    - Create a lightweight FastAPI backend to serve the model predictions.

## Phase 2: Web Application Development
- [ ] **Modern Frontend Interface**:
    - Build a clean, responsive web interface using a modern framework (or clean HTML/CSS/JS).
- [ ] **QR Code Integration**:
    - Implement browser-based QR code scanning using `jsQR` or `html5-qrcode`.
    - Support both live camera scanning and image file uploads.
- [ ] **Real-time Feedback**:
    - Provide instant safety ratings and detailed feature breakdowns for scanned URLs.

## Phase 3: Deployment & Security
- [ ] **Security Headers & HTTPS**:
    - Ensure the web app is served over HTTPS to allow camera access in browsers.
- [ ] **Rate Limiting**:
    - Protect the API from abuse.
- [ ] **Feedback Mechanism**:
    - Allow users to report misclassifications to help improve the model over time.
