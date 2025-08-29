from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import base64
import time

app = Flask(__name__)
CORS(app)  # permite que o angular acesse a api

# mediaPipe
mp_face_mesh = mp.solutions.face_mesh

# indices/pontos do facemesh
p_left_eye = [385, 380, 387, 373, 362, 263]
p_right_eye = [160, 144, 158, 153, 33, 133]
p_mouth = [82, 87, 13, 14, 312, 317, 78, 308]

# parâmetros
ear_limiar = 0.25
mar_limiar = 0.1
sleeping = 0
blink_count = 0
t_blinks = time.time()
c_time = 0
count_temp = 0
count_list = []
t_initial = 0.0

def calculate_ear(face, p_right_eye, p_left_eye):
    try:
        face = np.array([[coord.x, coord.y] for coord in face])
        face_left = face[p_left_eye, :]
        face_right = face[p_right_eye, :]

        ear_left = (np.linalg.norm(face_left[0] - face_left[1]) +
                    np.linalg.norm(face_left[2] - face_left[3])) / \
                   (2 * np.linalg.norm(face_left[4] - face_left[5]))
        ear_right = (np.linalg.norm(face_right[0] - face_right[1]) +
                     np.linalg.norm(face_right[2] - face_right[3])) / \
                    (2 * np.linalg.norm(face_right[4] - face_right[5]))
    except:
        ear_left, ear_right = 0.0, 0.0

    return (ear_left + ear_right) / 2

def calculate_mar(face, p_mouth):
    try:
        face = np.array([[coord.x, coord.y] for coord in face])
        face_mouth = face[p_mouth, :]
        mar = (np.linalg.norm(face_mouth[0] - face_mouth[1]) +
               np.linalg.norm(face_mouth[2] - face_mouth[3]) +
               np.linalg.norm(face_mouth[4] - face_mouth[5])) / \
              (2 * np.linalg.norm(face_mouth[6] - face_mouth[7]))
    except:
        mar = 0.0
    return mar


@app.route("/process_frame", methods=["POST"])
def process_frame():
    global sleeping, blink_count, t_blinks, c_time, count_temp, count_list, t_initial

    # recebe imagem base64 do angular
    data = request.json["image"]
    img_bytes = base64.b64decode(data.split(",")[1])
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    with mp_face_mesh.FaceMesh(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as facemesh:
        results = facemesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if not results.multi_face_landmarks:
            return jsonify({"ear": 0, "mar": 0, "blinks": blink_count, "time_closed": 0, "sleepy": False})

        face = results.multi_face_landmarks[0].landmark

        ear = calculate_ear(face, p_right_eye, p_left_eye)
        mar = calculate_mar(face, p_mouth)

        # lógica de piscadas e tempo olho fechado
        if ear < ear_limiar and mar < mar_limiar:
            if sleeping == 0:
                t_initial = time.time()
                blink_count += 1
            sleeping = 1
        if (sleeping == 1 and ear >= ear_limiar) or (ear <= ear_limiar and mar >= mar_limiar):
            sleeping = 0

        t_final = time.time()
        tempo = (t_final - t_initial) if sleeping == 1 else 0.0

        # contar piscadas por minuto
        time_elapsed = t_final - t_blinks
        if time_elapsed >= (c_time + 1):
            c_time = time_elapsed
            blinks_per_sec = blink_count - count_temp
            count_temp = blink_count
            count_list.append(blinks_per_sec)
            count_list = count_list if (len(count_list) <= 60) else count_list[-60:]

        blinks_per_minute = 15 if time_elapsed <= 60 else sum(count_list)

        # critério de sonolência
        sleepy = tempo >= 1.5 or blinks_per_minute < 10

        return jsonify({
            "ear": round(ear, 2),
            "mar": round(mar, 2),
            "blinks": blink_count,
            "time_closed": round(tempo, 2),
            "sleepy": sleepy
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
