from xmlrpc.client import Boolean
from flask import Flask, request
import pigpio
import atexit
import logging
import time
from datetime import date, datetime, timedelta
from threading import Thread

last_heartbeat = datetime.now()
active_heartbeat = False

def map(x):
    x = int(abs(x) * 255/75)
    if x < 20:
        x = 0
    elif x < 50:
        x = 50
    elif x > 255:
        x = 255
    return x

pi = pigpio.pi()
if not pi.connected:
    print("Error, can't connect to pigpiod service")
    exit()

atexit.register(pi.stop)

pin_enable_gauche = 24
pin_enable_droite = 4
pin_reculer_gauche = 25
pin_reculer_droite = 17
pin_avancer_gauche = 23
pin_avancer_droite = 22
pin_servo_pitch = 18
current_pitch = 1200

pi.set_mode(pin_enable_gauche, pigpio.OUTPUT)
pi.set_mode(pin_enable_droite, pigpio.OUTPUT)
pi.set_mode(pin_avancer_gauche, pigpio.OUTPUT)
pi.set_mode(pin_avancer_droite, pigpio.OUTPUT)
pi.set_mode(pin_reculer_gauche, pigpio.OUTPUT)
pi.set_mode(pin_reculer_droite, pigpio.OUTPUT)

pi.set_mode(pin_servo_pitch, pigpio.OUTPUT)
pi.set_PWM_frequency(pin_servo_pitch, 50)
pi.set_servo_pulsewidth(pin_servo_pitch, current_pitch)

pi.set_PWM_frequency(pin_avancer_gauche, 50)
pi.set_PWM_dutycycle(pin_avancer_gauche, 0)
pi.set_PWM_frequency(pin_avancer_droite, 50)
pi.set_PWM_dutycycle(pin_avancer_droite, 0)
pi.set_PWM_frequency(pin_reculer_gauche, 50)
pi.set_PWM_dutycycle(pin_reculer_gauche, 0)
pi.set_PWM_frequency(pin_reculer_droite, 50)
pi.set_PWM_dutycycle(pin_reculer_droite, 0)

pi.write(pin_enable_droite, pigpio.HIGH)
pi.write(pin_enable_gauche, pigpio.HIGH)

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.disabled = True

@app.route("/")
def hello_world():
    return("<p>Hello, World!</p>")

@app.route("/camera")
def camera():
    global current_pitch
    pitch = float(request.args.get('pitch'))
    current_pitch += pitch
    current_pitch = int(current_pitch) 
    if current_pitch > 2200:
        current_pitch = 2200
    if current_pitch < 500:
        current_pitch = 500
    pi.set_servo_pulsewidth(pin_servo_pitch, current_pitch)
    return("Ok")

@app.route("/heartbeat")
def heartbeat():
    global last_heartbeat
    last_heartbeat = datetime.now()
    return ("Ok")

@app.route("/command")
def command():
    axis_left_right = float(request.args.get('x'))
    axis_up_down = float(request.args.get('y'))
    heartbeat = Boolean(request.args.get('heartbeat'))

    # If heartbeat is activated
    global last_heartbeat, active_heartbeat
    if heartbeat:
        last_heartbeat = datetime.now()
        active_heartbeat = True
    else:
        active_heartbeat = False

    if axis_up_down < -15:  # Si on avance
            puissance_gauche = abs(axis_up_down)
            puissance_droite = abs(axis_up_down)
            puissance_gauche += axis_left_right
            puissance_droite -= axis_left_right
            pi.set_PWM_dutycycle(pin_avancer_gauche, map(puissance_gauche))
            pi.set_PWM_dutycycle(pin_avancer_droite, map(puissance_droite))
            pi.set_PWM_dutycycle(pin_reculer_gauche, 0)
            pi.set_PWM_dutycycle(pin_reculer_droite, 0)
    elif axis_up_down > 15:  # Si on recule
            puissance_gauche = axis_up_down
            puissance_droite = axis_up_down
            puissance_gauche -= axis_left_right
            puissance_droite += axis_left_right
            pi.set_PWM_dutycycle(pin_reculer_gauche, map(puissance_gauche))
            pi.set_PWM_dutycycle(pin_reculer_droite, map(puissance_droite))
            pi.set_PWM_dutycycle(pin_avancer_gauche, 0)
            pi.set_PWM_dutycycle(pin_avancer_droite, 0)
    else: # Si on fait du surplace
        if axis_left_right > 15:  # Si on tourne à droite
            pi.set_PWM_dutycycle(pin_avancer_gauche, map(axis_left_right/3))
            pi.set_PWM_dutycycle(pin_avancer_droite, 0)
            pi.set_PWM_dutycycle(pin_reculer_gauche, 0)
            pi.set_PWM_dutycycle(pin_reculer_droite, map(axis_left_right/3))
        elif axis_left_right < -15:  # Si on tourne à gauche
            pi.set_PWM_dutycycle(pin_avancer_gauche, 0)
            pi.set_PWM_dutycycle(pin_avancer_droite, map(axis_left_right/3))
            pi.set_PWM_dutycycle(pin_reculer_gauche, map(axis_left_right/3))
            pi.set_PWM_dutycycle(pin_reculer_droite, 0)
        else:  # Si on est à l'arrêt
            pi.set_PWM_dutycycle(pin_avancer_gauche, 0)
            pi.set_PWM_dutycycle(pin_avancer_droite, 0)
            pi.set_PWM_dutycycle(pin_reculer_gauche, 0)
            pi.set_PWM_dutycycle(pin_reculer_droite, 0)
    return("Ok")

def heartbeat_check():
    global last_heartbeat
    global active_heartbeat
    while True:
        # If heartbeat is active and the last one is older than 3 seconds, we stop the robot
        if active_heartbeat and last_heartbeat + timedelta(seconds=3) < datetime.now():
            pi.set_PWM_dutycycle(pin_avancer_gauche, 0)
            pi.set_PWM_dutycycle(pin_avancer_droite, 0)
            pi.set_PWM_dutycycle(pin_reculer_gauche, 0)
            pi.set_PWM_dutycycle(pin_reculer_droite, 0)
            active_heartbeat = False
            print("Hearbeat is older than 3 seconds, stopping esieabot.")
        time.sleep(1)

print("Starting esieabot-api")
heartbeat_thread = Thread(target=heartbeat_check, daemon=True)
heartbeat_thread.start()