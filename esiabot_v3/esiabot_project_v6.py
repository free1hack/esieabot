#!/usr/bin/python3
import time
import pigpio
from collections import namedtuple
import discord
from discord.ext import commands
import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
#from classcameraesiabot import *
import threading

pin_right_forward = 22
pin_left_forward = 23

pin_right_backward = 17
pin_left_backward = 25

# Gets or creates a logger
logger = logging.getLogger(__name__)
# set log level
logger.setLevel(logging.DEBUG)
# define file handler and set formatter
file_handler = logging.FileHandler('esieabot.log')
formatter    = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)
# add file handler to logger
logger.addHandler(file_handler)

#pin_right_bakwards
# the solution was found here: https://stackoverflow.com/questions/73458847/discord-py-error-message-discord-ext-commands-bot-privileged-message-content-i
intents = discord.Intents.all()

bot = commands.Bot(intents=intents , command_prefix="/")

pi = pigpio.pi()
if not pi.connected:
    print("Error, can't connect to pigpiod service")
    logger.error("Error, can't connect to pigpiod service")
    exit()

logger.info('settigng the mode for pigpio on OUTPUT')
pi.set_mode(pin_right_forward, pigpio.OUTPUT)
pi.set_mode(pin_left_forward, pigpio.OUTPUT) 
pi.set_mode(pin_right_backward, pigpio.OUTPUT)
pi.set_mode(pin_left_backward, pigpio.OUTPUT)

@bot.event
async def on_ready():
    print("Discordbot is ready")
    logger.info('Discordbot is ready')
    #await ctx.send("to go go forward please type /forward")
    
    
@bot.command()
async def forward(ctx):
    logger.info('moving forward')
    pi.write(pin_right_forward, 1)
    pi.write(pin_left_forward, 1)
    logger.info('move forward ')
    time.sleep(3)
    logger.info('stop')
    pi.write(pin_right_forward, 0)
    pi.write(pin_left_forward, 0)
    logger.info('send "go forward" to Discordbot')
    await ctx.send("go forward")

@bot.command()
async def backward(ctx):
    logger.info('moving backword')
    pi.write(pin_right_backward, 1)
    pi.write(pin_left_backward, 1)
    logger.info('move backword')
    time.sleep(3)
    pi.write(pin_right_backward, 0)
    pi.write(pin_left_backward, 0)
    logger.info('stop')
    logger.info('send "go backward" to Discordbot')
    await ctx.send("go backward")
    
    
@bot.command()
async def right(ctx):
    logger.info('moving right')
    pi.write(pin_left_forward, 1)
    time.sleep(0.4)
    logger.info('stop')
    pi.write(pin_left_forward, 0)
    logger.info('send "go left" to Discordbot')
    await ctx.send("go right")
    
    
@bot.command()
async def left(ctx):
    logger.info('moving left')
    pi.write(pin_right_forward, 1)
    time.sleep(0.4)
    logger.info('stop')
    pi.write(pin_right_forward, 0)
    logger.info('send "go left" to Discordbot')
    await ctx.send("go left")



PAGE="""\
<html>
<head>
<title>Esieabot camera</title>
</head>
<body>
<center><h1>Esieabot camera</h1></center>
<center><img src="stream.mjpg" width="900" height="900"></center>
</body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    output = None

    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with StreamingHandler.output.condition:
                        StreamingHandler.output.condition.wait()
                        frame = StreamingHandler.output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    def __init__(self, address, handler, output):
        handler.output = output
        super().__init__(address, handler)

def cameraControler():
    logger.info('starting streaming the camera ....')
    #with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    with picamera.PiCamera(resolution='1080p', framerate=24) as camera:
            output = StreamingOutput()
            camera.start_recording(output, format='mjpeg')
            try:
                address = ('', 8000)
                server = StreamingServer(address, StreamingHandler, output)
                server.serve_forever()
                logger.info('the camera is on streaming ....')
            except(KeyboardInterrupt):
                camera.stop_recording()
                logger.info('stop streaming from the camera, error detected !!!')

# run the camera in a thread so it will be run in parallel as the bot.
camera_worker = threading.Thread(target=cameraControler)
camera_worker.start()

logger.info('activate your DiscordBot')
#launch discordBot
bot.run("MTAzNzQ2MDY5NTk4NzUxOTU0OQ.GRKgFq.FKPuu8CGs9wnTK-SbsRqEfzrYpu66hJi-Zq7s8")

camera_worker.join()

