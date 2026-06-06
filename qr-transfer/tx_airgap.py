import qrcode
import cv2
import base64
import os
import sys
import numpy as np
import time

def generate_tx(file_path, chunk_size=100, fps=10):
    """
    Reads a file, converts it to Base64, chunks it, and displays as an animated QR flipbook.
    
    Args:
        file_path (str): Path to the payload file.
        chunk_size (int): Characters per QR code (keep low for reliability).
        fps (int): Frames per second for the flipbook.
    """
    if not os.path.exists(file_path):
        print(f"[!] Error: File '{file_path}' not found.")
        return

    # 1. Read and Encode Data
    with open(file_path, "rb") as f:
        raw_data = f.read()
    b64_data = base64.b64encode(raw_data).decode('utf-8')
    
    # 2. Chunking Logic
    # We use a header format: [INDEX/TOTAL]DATA
    total_chunks = (len(b64_data) + chunk_size - 1) // chunk_size
    chunks = []
    for i in range(total_chunks):
        start = i * chunk_size
        end = start + chunk_size
        chunk_payload = b64_data[start:end]
        # Header format: [1/5]...
        headered_chunk = f"[{i+1}/{total_chunks}]{chunk_payload}"
        chunks.append(headered_chunk)

    print(f"[*] Payload size: {len(raw_data)} bytes")
    print(f"[*] Base64 size: {len(b64_data)} chars")
    print(f"[*] Total QR chunks: {total_chunks}")
    print(f"[*] Running at {fps} FPS. Press 'q' in the window to stop.")

    # 3. Display Loop (Flipbook)
    cv2.namedWindow("Air-Gap Transmitter", cv2.WINDOW_NORMAL)
    delay = int(1000 / fps)
    
    while True:
        for idx, payload in enumerate(chunks):
            # Generate QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(payload)
            qr.make(fit=True)
            
            # Convert PIL image to OpenCV format
            img_pil = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            # Visual Feedback on screen
            cv2.putText(img_cv, f"Chunk {idx+1}/{total_chunks}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            cv2.imshow("Air-Gap Transmitter", img_cv)
            
            # Exit check
            if cv2.waitKey(delay) & 0xFF == ord('q'):
                print("[*] Transmitter stopped by user.")
                cv2.destroyAllWindows()
                return

if __name__ == "__main__":
    # Default parameters: payload.txt, 100 char chunks, 7 FPS
    target_file = "payload.txt"
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    
    # Create a dummy payload if it doesn't exist for the demo
    if not os.path.exists(target_file):
        with open(target_file, "w") as f:
            f.write("HACKATHON_HARDWARE_INTEGRITY_LOG_2026_SECRET_KEY_BEEFCAFE")
            f.write("\n" + "X" * 500) # Add some bulk
            
    generate_tx(target_file, chunk_size=100, fps=7)
