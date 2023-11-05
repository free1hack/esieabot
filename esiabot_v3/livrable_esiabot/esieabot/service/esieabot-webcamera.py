#!/usr/bin/python3
# esieabot-webcamera
# Based on an example from the picamera lib documentation
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming
# BSD licence and copyright below

import io
# TODO: migrate to picamera2 API
import picamera
import logging
import socketserver
from threading import Condition, Thread, activeCount
from http import server
import logging
import atexit
from time import sleep

log = logging.getLogger('werkzeug')
log.disabled = True

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
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/stream.mjpg')
            self.end_headers()
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                print("Removed streaming client " + str(self.client_address) + ": " + str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def exit(camera):
    if camera.recording:
        print("Recording stopped on exit")
        camera.stop_recording()
    print("Bye")

print("Starting esieabot webcamera streaming server")
with picamera.PiCamera(resolution='848x480', framerate=20) as camera:
    output = StreamingOutput()
    camera.rotation = 180
    atexit.register(exit, camera)
    address = ('127.0.0.1', 8000)
    server = StreamingServer(address, StreamingHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    while True:
        # If there are no clients (Thread #0 is the main thread and Thread #1 is the webserver)
        if activeCount() <= 2:
            if camera.recording:
                print("There is no client and the camera is recording, stopping it...")
                camera.stop_recording()
                print("Recording stopped")
        # If there are some clients
        else:
            if not camera.recording:
                print("There are some clients but the camera is not recording, starting it...")
                camera.start_recording(output, format='mjpeg', bitrate=3000000, quality=40)
                print("Recording started")
        sleep(0.5)


"""
picamera library and examples:

Copyright 2013-2017 Dave Jones <dave@waveform.org.uk>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the copyright holder nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""