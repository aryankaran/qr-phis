import qrcode
import base64
import os
import math
import cv2
import numpy as np
import sys

# Protocol: INDEX|TOTAL|FILENAME|DATA
CHUNK_SIZE = 450 # Optimal for QR version 10-15 without being too dense

def chunk_file(file_path):
    if not os.path.exists(file_path):
        print(f"[!] File {file_path} not found.")
        sys.exit(1)
        
    with open(file_path, "rb") as f:
        data = f.read()
    
    encoded_data = base64.b64encode(data).decode('ascii')
    total_chunks = math.ceil(len(encoded_data) / CHUNK_SIZE)
    filename = os.path.basename(file_path)
    
    chunks = []
    for i in range(total_chunks):
        chunk_data = encoded_data[i*CHUNK_SIZE : (i+1)*CHUNK_SIZE]
        payload = f"{i}|{total_chunks}|{filename}|{chunk_data}"
        chunks.append(payload)
    return chunks

def transmit(file_path, fps=10):
    chunks = chunk_file(file_path)
    print(f"[*] Transmitting {file_path} ({len(chunks)} chunks) at {fps} FPS")
    
    cv2.namedWindow("QR Air-Gap Sender", cv2.WINDOW_NORMAL)
    delay = int(1000 / fps)
    
    while True: # Loop until 'q' is pressed
        for i, payload in enumerate(chunks):
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
            qr.add_data(payload)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # HUD
            cv2.putText(img_cv, f"CHUNK {i+1}/{len(chunks)}", (10, 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            cv2.imshow("QR Air-Gap Sender", img_cv)
            if cv2.waitKey(delay) & 0xFF == ord('q'):
                print("[*] Transmission stopped.")
                return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sender.py <file_path> [fps]")
    else:
        fps = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        transmit(sys.argv[1], fps)
