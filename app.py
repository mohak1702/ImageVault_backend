# from flask import Flask, request, send_file, jsonify
# import hashlib
# from flask_cors import CORS
# import cv2
# import numpy as np
# import os
# from io import BytesIO

# app = Flask(__name__)
# CORS(app)  # Enable CORS for React frontend

# # Encrypt endpoint
# @app.route("/encrypt", methods=["POST"])
# def encrypt():
#     image_file = request.files.get("image")
#     text = request.form.get("text") + chr(0)
#     pin = request.form.get("pin")

#     if not image_file or not text or not pin:
#         return jsonify({"error": "Missing image, text, or pin"}), 400

#     # Read image into OpenCV
#     file_bytes = np.frombuffer(image_file.read(), np.uint8)
#     img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
#     if img is None:
#         return jsonify({"error": "Invalid image"}), 400

#     # Encryption mapping
#     d = {chr(i): i for i in range(255)}
#     kl = 0
#     n = 0
#     m = 0
#     l = len(text)
#     z = 0

#     for i in range(l):
#         img[n, m, z] = d[text[i]] ^ d[pin[kl]]
#         n += 1
#         m += 1
#         m = m % img.shape[1]
#         kl = (kl + 1) % len(pin)
#         z = (z + 1) % 3
#         if n >= img.shape[0]:
#             n = 0

#     # Save encrypted image to temporary file
#     encrypted_path = "encrypted_temp.png"
#     cv2.imwrite(encrypted_path, img)

#     return send_file(encrypted_path, mimetype="image/png", as_attachment=True, download_name="encrypted_image.png")

# # Decrypt endpoint
# @app.route("/decrypt", methods=["POST"])
# def decrypt():
#     image_file = request.files.get("image")
#     pin = request.form.get("pin")

#     if not image_file or not pin:
#         return jsonify({"error": "Missing image or pin"}), 400

#     file_bytes = np.frombuffer(image_file.read(), np.uint8)
#     img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
#     if img is None:
#         return jsonify({"error": "Invalid image"}), 400

#     # Dictionaries for mapping
#     d = {chr(i): i for i in range(255)}
#     c = {i: chr(i) for i in range(255)}

#     decrypted_text = ""
#     kl, n, m, z = 0, 0, 0, 0
#     max_len = 1000  # safe upper bound

#     for i in range(max_len):
#         pixel_val = int(img[n, m, z])  # ensure int
#         pin_val = d[pin[kl]]
#         val = int(pixel_val ^ pin_val)

#         if val == 0:  # stop at null terminator
#             break

#         # Safe lookup in c
#         if val in c:
#             decrypted_text += c[val]
#         else:
#             break  # stop if garbage value appears

#         # move pointers
#         n += 1
#         m += 1
#         m = m % img.shape[1]
#         kl = (kl + 1) % len(pin)
#         z = (z + 1) % 3
#         if n >= img.shape[0]:
#             break

#     return jsonify({"text": decrypted_text})


# if __name__ == "__main__":
#     app.run(debug=True)
from flask import Flask, request, send_file, jsonify
import hashlib
from flask_cors import CORS
import cv2
import numpy as np
import os
from io import BytesIO

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://image-vault-frontend-opal.vercel.app/"}})

# Utility to hash pin (shortened)
def pin_hash(pin):
    return hashlib.sha256(pin.encode()).hexdigest()[:16]

# Encrypt endpoint
@app.route("/encrypt", methods=["POST"])
def encrypt():
    image_file = request.files.get("image")
    text = request.form.get("text")
    pin = request.form.get("pin")

    if not image_file or not text or not pin:
        return jsonify({"error": "Missing image, text, or pin"}), 400

    # Add PIN hash to the text for verification during decryption
    secret_text = pin_hash(pin) + "|" + text + chr(0)

    # Read image into OpenCV
    file_bytes = np.frombuffer(image_file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"error": "Invalid image"}), 400

    # Encryption mapping
    d = {chr(i): i for i in range(255)}
    kl = n = m = z = 0
    l = len(secret_text)

    for i in range(l):
        img[n, m, z] = d[secret_text[i]] ^ d[pin[kl]]
        n += 1
        m += 1
        m = m % img.shape[1]
        kl = (kl + 1) % len(pin)
        z = (z + 1) % 3
        if n >= img.shape[0]:
            n = 0

    # Save encrypted image to temporary file
    encrypted_path = "encrypted_temp.png"
    cv2.imwrite(encrypted_path, img)

    return send_file(
        encrypted_path,
        mimetype="image/png",
        as_attachment=True,
        download_name="encrypted_image.png",
    )

# Decrypt endpoint
@app.route("/decrypt", methods=["POST"])
def decrypt():
    image_file = request.files.get("image")
    pin = request.form.get("pin")

    if not image_file or not pin:
        return jsonify({"error": "Missing image or pin"}), 400

    file_bytes = np.frombuffer(image_file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"error": "Invalid image"}), 400

    # Dictionaries for mapping
    d = {chr(i): i for i in range(255)}
    c = {i: chr(i) for i in range(255)}

    decrypted_text = ""
    kl, n, m, z = 0, 0, 0, 0
    max_len = 2000  # safe upper bound

    for i in range(max_len):
        pixel_val = int(img[n, m, z])  # ensure int
        pin_val = d[pin[kl]]
        val = int(pixel_val ^ pin_val)

        if val == 0:  # stop at null terminator
            break

        if val in c:
            decrypted_text += c[val]
        else:
            break

        # move pointers
        n += 1
        m += 1
        m = m % img.shape[1]
        kl = (kl + 1) % len(pin)
        z = (z + 1) % 3
        if n >= img.shape[0]:
            break

    # ✅ Verify PIN by checking stored hash
    if "|" not in decrypted_text:
        return jsonify({"text": "Wrong PIN"}), 200

    stored_hash, real_message = decrypted_text.split("|", 1)
    if stored_hash != pin_hash(pin):
        return jsonify({"text": "Wrong PIN"}), 200

    return jsonify({"text": real_message})


if __name__ == "__main__":
    app.run(debug=True)
