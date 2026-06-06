import cv2
import numpy as np
from pyzbar import pyzbar
import base64
import re
from tqdm import tqdm

def receive_rx():
    """
    Captures webcam feed, decodes QR codes, handles sequence headers, and reconstructs the file.
    """
    # 1. Initialize Webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[!] Error: Could not open webcam /dev/video0")
        return

    # Optimization: Lower resolution can sometimes increase FPS/decoding speed
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    received_data = {}  # Store as {index: data}
    total_chunks = None
    pbar = None

    print("[*] Receiver started. Waiting for first QR code...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 2. Decode QR codes in the current frame
        decoded_objects = pyzbar.decode(frame)
        
        for obj in decoded_objects:
            qr_text = obj.data.decode('utf-8')
            
            # 3. Parse Header: [index/total]data
            # Regex to find [1/5] pattern
            match = re.match(r"\[(\d+)/(\d+)\](.*)", qr_text)
            if match:
                idx = int(match.group(1))
                total = int(match.group(2))
                payload = match.group(3)

                # Initialize state on first successful read
                if total_chunks is None:
                    total_chunks = total
                    pbar = tqdm(total=total_chunks, desc="Receiving Data")
                
                # Store unique chunk
                if idx not in received_data:
                    received_data[idx] = payload
                    if pbar:
                        pbar.update(1)

        # 4. Display Status on Frame
        progress_text = f"Collected: {len(received_data)}/{total_chunks if total_chunks else '??'}"
        cv2.putText(frame, progress_text, (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow("Air-Gap Receiver", frame)

        # 5. Check for Completion
        if total_chunks and len(received_data) == total_chunks:
            print("\n[+] All chunks received successfully!")
            break

        # Manual Exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n[*] Receiver aborted by user.")
            break

    # 6. Reconstruct Data
    cap.release()
    cv2.destroyAllWindows()

    if total_chunks and len(received_data) == total_chunks:
        print("[*] Reassembling payload...")
        try:
            # Sort keys to ensure correct order
            full_b64 = "".join([received_data[i] for i in sorted(received_data.keys())])
            decoded_bytes = base64.b64decode(full_b64)
            
            output_file = "recovered_data.txt"
            with open(output_file, "wb") as f:
                f.write(decoded_bytes)
            
            print(f"[+] Success! Recovered data saved to: {output_file}")
        except Exception as e:
            print(f"[!] Reassembly error: {e}")

if __name__ == "__main__":
    receive_rx()
