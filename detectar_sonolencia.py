import cv2
import mediapipe as mp
import numpy as np
import time

# MediaPipe
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# Indices do FaceMesh
p_left_eye = [385, 380, 387, 373, 362, 263]
p_right_eye = [160, 144, 158, 153, 33, 133]
p_eyes = p_left_eye + p_right_eye

p_mouth = [82, 87, 13, 14, 312, 317, 78, 308] 

def calculate_ear(face, p_right_eye, p_left_eye):
    try:
        face = np.array([[coord.x, coord.y] for coord in face])
        face_left = face[p_left_eye,:]
        face_right = face[p_right_eye,:]

        # calculando distância *euclidiana* a partir da fórmula EAR
        ear_left = (np.linalg.norm(face_left[0] - face_left[1]) + np.linalg.norm(face_left[2] - face_left[3])) / (2 * (np.linalg.norm(face_left[4] - face_left[5])))
        ear_right = (np.linalg.norm(face_right[0] - face_right[1]) + np.linalg.norm(face_right[2] - face_right[3])) / (2 * (np.linalg.norm(face_right[4] - face_right[5])))
    except:
        ear_left = 0.0
        ear_right = 0.0
    mean_ear = (ear_left + ear_right)/2
    return mean_ear

def calculate_mar(face, p_mouth):
    try:
        face = np.array([[coord.x, coord.y] for coord in face])
        face_mouth = face[p_mouth,:]

        mar = (np.linalg.norm(face_mouth[0] - face_mouth[1]) + np.linalg.norm(face_mouth[2] - face_mouth[3]) + np.linalg.norm(face_mouth[4] - face_mouth[5])) / (2 * (np.linalg.norm(face_mouth[6] - face_mouth[7])))
    except:
        mar = 0.0
    return mar

def draw_centered_text_box(frame, texto, x1, y1, x2, y2, 
                           rect_color=(161,11,98), text_color=(255,255,255),
                           font=cv2.FONT_HERSHEY_DUPLEX, scale=0.85, thickness=1):
    
    (tw, th), _ = cv2.getTextSize(texto, font, scale, thickness)
    
    x_text = x1 + (x2 - x1 - tw) // 2
    y_text = y1 + (y2 - y1 + th) // 2
    
    
    cv2.rectangle(frame, (x1, y1), (x2, y2), rect_color, -1)
    cv2.putText(frame, texto, (x_text, y_text), font, scale, text_color, thickness)

ear_limiar = 0.25
mar_limiar = 0.1
sleeping = 0
blink_count = 0
c_time = 0
count_temp = 0
count_list = []

# counting blinks per minute (beginning)
t_blinks = time.time()

cam = cv2.VideoCapture(0)

with mp_face_mesh.FaceMesh(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as facemesh:
    while cam.isOpened():
        success, frame = cam.read()
        if not success:
            print("ignoring empty frame")
            continue
        length, width, _ = frame.shape

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result_facemesh = facemesh.process(frame)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        try:
            for face_landmarks in result_facemesh.multi_face_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    face_landmarks,
                    mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec = mp_drawing.DrawingSpec(color=(168, 114, 133), thickness=1, circle_radius=1),
                    connection_drawing_spec = mp_drawing.DrawingSpec(color=(250, 155, 255), thickness=2, circle_radius=1))
                face = face_landmarks.landmark

                for id_coord, coord_xyz in enumerate(face):
                    # coordenadas dos olhos
                    if id_coord in p_eyes:
                        coord_cv = mp_drawing._normalized_to_pixel_coordinates(coord_xyz.x, coord_xyz.y, width, length)
                        cv2.circle(frame, coord_cv, 3, (150, 77, 9), -1)
                    # coordenadas da boca
                    if id_coord in p_mouth:
                        coord_cv = mp_drawing._normalized_to_pixel_coordinates(coord_xyz.x, coord_xyz.y, width, length)
                        cv2.circle(frame, coord_cv, 3, (55, 8, 158), -1)

                ear = calculate_ear(face, p_right_eye, p_left_eye)
                cv2.rectangle(frame, (0,1), (285,106), (0,0,0), -1)
                cv2.putText(frame, f"EAR: {round(ear, 2):.2f} {'Opened' if ear >= ear_limiar else 'Closed'}" , (1, 24), # arredonda e deixa com 2 casas decimais
                                cv2.FONT_HERSHEY_DUPLEX,
                                0.9, (255, 255, 255), 1)
                
                mar = calculate_mar(face, p_mouth)
                cv2.putText(frame, f"MAR: {round(mar, 2):.2f} {'Opened' if mar >= mar_limiar else 'Closed'}" , (1, 50), 
                                cv2.FONT_HERSHEY_DUPLEX,
                                0.9, (255, 255, 255), 1)

                if ear < ear_limiar and mar < mar_limiar:
                    if sleeping == 0:
                        t_initial = time.time()
                        blink_count = blink_count + 1
                    else:
                        t_initial
                        blink_count
                    sleeping = 1
                if (sleeping == 1 and ear >= ear_limiar) or (ear <= ear_limiar and mar >= mar_limiar):
                    sleeping = 0
                t_final = time.time()
                # counting blinks per minute
                time_elapsed = t_final - t_blinks

                # 1 second 
                if time_elapsed >= (c_time+1):  
                    c_time = time_elapsed
                    blinks_per_sec = blink_count - count_temp
                    count_temp = blink_count
                    count_list.append(blinks_per_sec)
                    count_list = count_list if (len(count_list)<=60) else count_list[-60:]

                # average between 15 and 20 (blinks per minute)
                blinks_per_minute = 15 if time_elapsed <= 60 else sum(count_list)
                
                if sleeping == 1:
                    tempo = (t_final - t_initial)
                else:
                    tempo = 0.0
                cv2.putText(frame, f"Time: {round(tempo, 3):.3f}" , (1, 76), 
                                cv2.FONT_HERSHEY_DUPLEX,
                                0.9, (255, 255, 255), 1)
                
                cv2.putText(frame, f"Blinks: {blink_count}" , (1, 102), 
                                                cv2.FONT_HERSHEY_DUPLEX,
                                                0.9, (250, 155, 255), 1)

                # alert message
                if blinks_per_minute < 10 or tempo >= 1.5:
                    draw_centered_text_box(frame, "sleepiness detected", 30, 400, 610, 452)
        
        except:
            pass

        cv2.imshow("Camera", frame)
        if(cv2.waitKey(10) & 0xFF == ord('c')):
            break

cam.release()
cv2.destroyAllWindows()