from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2, mediapipe as mp, numpy as np, base64, time

app = Flask(__name__)
CORS(app)

# inicializa MediaPipe
mp_face_mesh = mp.solutions.face_mesh
facemesh = mp_face_mesh.FaceMesh(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# índices do FaceMesh (olhos e boca)
p_left_eye = [385, 380, 387, 373, 362, 263]
p_right_eye = [160, 144, 158, 153, 33, 133]
p_mouth = [82, 87, 13, 14, 312, 317, 78, 308]

# thresholds
ear_limiar = 0.3     
mar_limiar = 0.6     
tempo_sono = 1.5      

# variáveis
sleeping = 0
blink_count = 0
t_initial = 0.0

def calculate_ear(face, p_right_eye, p_left_eye):
    try:
        face = np.array([[coord.x, coord.y] for coord in face])
        face_left, face_right = face[p_left_eye, :], face[p_right_eye, :]
        ear_left = (np.linalg.norm(face_left[0]-face_left[1]) +
                    np.linalg.norm(face_left[2]-face_left[3])) / \
                   (2*np.linalg.norm(face_left[4]-face_left[5]))
        ear_right = (np.linalg.norm(face_right[0]-face_right[1]) +
                     np.linalg.norm(face_right[2]-face_right[3])) / \
                    (2*np.linalg.norm(face_right[4]-face_right[5]))
    except:
        return 0.0
    return (ear_left+ear_right)/2


def calculate_mar(face, p_mouth):
    try:
        face = np.array([[coord.x, coord.y] for coord in face])
        m = face[p_mouth, :]
        mar = (np.linalg.norm(m[0]-m[1]) +
               np.linalg.norm(m[2]-m[3]) +
               np.linalg.norm(m[4]-m[5])) / \
              (2*np.linalg.norm(m[6]-m[7]))
    except:
        return 0.0
    return mar

# rota de reset
@app.route("/reset", methods=["POST"])
def reset():
    global sleeping, blink_count, t_initial
    sleeping = 0
    blink_count = 0
    t_initial = 0.0
    return jsonify({"status": "reset ok"})

# rota de processar dados
@app.route("/process_frame", methods=["POST"])
def process_frame():
    global sleeping, blink_count, t_initial

    # recebe frame do Angular (base64)
    data = request.json["image"]
    img_bytes = base64.b64decode(data.split(",")[1])
    frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

    results = facemesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if not results.multi_face_landmarks:
        return jsonify({"ear": 0, "mar": 0, "blinks": blink_count, "time_closed": 0, "sleepy": False})

    face = results.multi_face_landmarks[0].landmark
    ear, mar = calculate_ear(face, p_right_eye, p_left_eye), calculate_mar(face, p_mouth)

    h, w, _ = frame.shape
    points_eye = []
    points_mouth = []

    for idx in p_left_eye + p_right_eye:
        points_eye.append({"x": int(face[idx].x * w), "y": int(face[idx].y * h)})

    for idx in p_mouth:
        points_mouth.append({"x": int(face[idx].x * w), "y": int(face[idx].y * h)})

    # lógica de piscada / olhos fechados
    if ear < ear_limiar:  
        # olho fechado
        if sleeping == 0:
            t_initial = time.time()
            blink_count += 1
        sleeping = 1
    else:
        sleeping = 0

    # tempo com olhos fechados
    tempo = (time.time() - t_initial) if sleeping else 0.0

    # boolean
    sleepy = bool((tempo >= tempo_sono) or (mar >= mar_limiar))

    return jsonify({
        "ear": round(ear, 2),
        "mar": round(mar, 2),
        "blinks": blink_count,
        "time_closed": round(tempo, 2),
        "sleepy": sleepy,
        "eyes": points_eye,
        "mouth": points_mouth,
        "frame_width": w,
        "frame_height": h
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
