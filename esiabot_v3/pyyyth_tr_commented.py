import asyncio
import logging
import libcamera
import picamera2
import streaming


class Camera:

    #class constructor. self : the class insance that instansiate the class objects.
    # "->None" is The main reason is to allow static type checking. By default, "mypy" will ignore unannotated functions and methods. See: https://peps.python.org/pep-0484/#the-meaning-of-annotations
    # the usage of dict ???? camera_settings is an attribute (variable) that is a dictionary type.
    # In python to declare a variable: varriable_name: type_variable = value
    def __init__(self, camera_settings: dict) -> None: 
        self.logger: logging.Logger = logging.getLogger("Esieabot.Camera")
        self.logger.propagate = True

        self.logger.info("Starting the initialization of the camera...")

        self.settings = camera_settings

        self.camera: picamera2.Picamera2 = picamera2.Picamera2()
        self.camera.configure(
            self.camera.create_video_configuration(
                main = {
                    "size": (
                        self.settings["video_width"],
                        self.settings["video_height"]
                    )
                },
                transform = libcamera.Transform(
                    hflip = self.settings["video_hflip"],
                    vflip = self.settings["video_vflip"]
                )
            )
        )

        picamera2.Picamera2.set_logging(picamera2.Picamera2.WARNING)

        self.streaming_output = streaming.StreamingOutput()
        server_address = ("", self.settings["streaming_server_port"])
        self.streaming_server = streaming.StreamingServer(server_address, streaming.StreamingHandler)
        self.streaming_server.streaming_output = self.streaming_output

        self.logger.info("Done with the camera initialization.")
        
    
    def start(self) -> None:

        self.logger.info("Starting the camera....")
        self.camera.start_recording(
            picamera2.encoders.JpegEncoder(),
            picamera2.outputs.FileOutput(self.streaming_output),
            picamera2.encoders.Quality.VERY_LOW
        )

        self.logger.info("Starting the streaming server...")
        self.streaming_server.serve_forever()


    async def handle_stop(self) -> None:

        self.logger.info("Sending termination signal to the streaming server...")
        self.streaming_server.shutdown()

        self.logger.info("Sending termination signal to the camera thread...")
        self.camera.stop_recording()

        self.logger.info("Waiting 2.5 seconds for subprocesses to finish...")
        await asyncio.sleep(2.5)


if __name__ == "__main__":
    exit()




from enumerations import Directions, Gpios
from logger import LoggerBuilder
from motor import Motor
import asyncio
import atexit
import logging
import pigpio


class Controller:

    def __init__(self) -> None:

        self.logger: logging.Logger = logging.getLogger("Esieabot.Controller")
        self.logger.propagate = True

        self.logger.info("Starting initialization...")

        self.logger.info("Connecting to pigpio daemon...")
        self.gpio_daemon = pigpio.pi()
        if not self.gpio_daemon.connected:
            self.logger.critical("Unable to connect to the pigpio daemon...")
            exit()
        atexit.register(self.gpio_daemon.stop)

        self.motor_right = Motor(
            self.gpio_daemon,
            Gpios.MOTOR_RIGHT_FORWARD.value,
            Gpios.MOTOR_RIGHT_BACKWARD.value,
            Gpios.MOTOR_RIGHT_ENABLE.value
        )

        self.motor_left = Motor(
            self.gpio_daemon,
            Gpios.MOTOR_LEFT_FORWARD.value,
            Gpios.MOTOR_LEFT_BACKWARD.value,
            Gpios.MOTOR_LEFT_ENABLE.value
        )

        self.logger.info("Done with initialization.")
        

    async def move_forward(self, duration: float) -> None:

        await self.move(Directions.FORWARD, duration)


    async def move_backward(self, duration: float) -> None:

        await self.move(Directions.BACKWARD, duration)


    async def move(self, direction, duration: float) -> None:

        if direction is Directions.FORWARD:
            self.motor_right.rotate_clockwise()
            self.motor_left.rotate_clockwise()
        elif direction is Directions.BACKWARD:
            self.motor_right.rotate_anticlockwise()
            self.motor_left.rotate_anticlockwise()
        else:
            return

        await asyncio.sleep(duration)
        
        self.motor_right.stop()
        self.motor_left.stop()

    async def turn_right(self, duration: float) -> None:

        self.turn(Directions.RIGHT, duration)


    async def turn_left(self, duration: float) -> None:

        await self.turn(Directions.LEFT, duration)


    async def turn(self, direction, duration: float) -> None:

        if direction is Directions.RIGHT:
            self.motor_right.rotate_clockwise()
            self.motor_left.rotate_anticlockwise()
        elif direction is Directions.LEFT:
            self.motor_right.rotate_anticlockwise()
            self.motor_left.rotate_clockwise()
        else:
            return
        
        await asyncio.sleep(duration)

        self.motor_right.stop()
        self.motor_left.stop()


if __name__ == "__main__":
    exit()



from discord.ext.commands import command
import discord
import esieabot
from typing import Literal
import logging


class DiscordBot(discord.ext.commands.Bot):
    
    def __init__(self, esieabot: esieabot.Esieabot, discord_settings: dict):

        self.logger: logging.Logger = logging.getLogger("Esieabot.DiscordBot")
        self.logger.propagate = True

        self.logger.info("Starting initialization of the discordbot...")

        self.esieabot = esieabot

        self.command_prefix = discord_settings["command_prefix"]
        self.owner_id = discord_settings["owner_id"]
        self.token = discord_settings["token"]

        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        
        discord.ext.commands.Bot.__init__(
            self,
            command_prefix = self.command_prefix,
            intents = intents
        )

        self.add_commands()

        self.logger.info("Done with initialization of the discordbot.")


    async def on_ready(self):

        self.logger.info(f"Logged to discord as {self.user}")


    async def handle_on_command_error(self, ctx: discord.ext.commands.Context, error: discord.DiscordException):

        if isinstance(error, discord.HTTPException):
            self.logger.error(f"Error: HTTPException [status: {error.status}] [code: {error.code}].")
            return
        elif isinstance(error, discord.ext.commands.MissingRequiredArgument):
            await ctx.send(f"Error: MissingRequiredArgument [{error.param}].")
            self.logger.debug("Error: MissingRequiredArgument.")
        elif isinstance(error, discord.ext.commands.ArgumentParsingError):
            await ctx.send(f"Error: ArgumentParsingError.")
            self.logger.debug("Error: ArgumentParsingError.")
        elif isinstance(error, discord.ext.commands.BadLiteralArgument):
            await ctx.send(f"Error: BadLiteralArgument [{error.param}].")
            self.logger.debug("Error: BadLiteralArgument.")
        elif isinstance(error, discord.ext.commands.TooManyArguments):
            await ctx.send(f"Error: TooManyArguments.")
            self.logger.debug("Error: TooManyArguments.")
        elif isinstance(error, discord.ext.commands.BadArgument):
            await ctx.send("Error: BadArgument.")
            self.logger.debug("Error: BadArgument.")
        else:
            await ctx.send("UnexpectedError. Seems like something went wrong...")
            self.logger.debug("Error: UnexpectedError.")


    def add_commands(self):

        @command("move", ignore_extra = False)
        async def move(ctx: discord.ext.commands.Context, direction: Literal["forward", "backward"], duration: float):
            if direction == "forward":
                await ctx.send("Moving forward...")
                await self.esieabot.controller.move_forward(duration)
            elif direction == "backward":
                await ctx.send("Moving backward...")
                await self.esieabot.controller.move_backward(duration)
            await ctx.send("Done with move. Ready for commands !")

        @move.error
        async def on_move_error(ctx: discord.ext.commands.Context, error: discord.DiscordException):
            await self.handle_on_command_error(ctx, error)

        self.add_command(move)

        @command("turn", ignore_extra = False)
        async def turn(ctx: discord.ext.commands.Context, direction: Literal["right", "left"], duration: float):
            if direction == "right":
                await ctx.send("Turning right...")
                await self.esieabot.controller.turn_right(duration)
            elif direction == "left":
                await ctx.send("Turning left...")
                await self.esieabot.controller.turn_left(duration)
            await ctx.send("Done with turn. Ready for commands !")

        @turn.error
        async def on_turn_error(ctx: discord.ext.commands.Context, error: discord.DiscordException):
            await self.handle_on_command_error(ctx, error)

        self.add_command(turn)

        @command("shutdown", ignore_extra = False)
        async def shutdown(ctx: discord.ext.commands.Context):
            await ctx.send("Shutting down... Hope to see you soon ;) !")
            self.esieabot.shutdown()

        @shutdown.error
        async def on_shutdown_error(ctx: discord.ext.commands.Context, error: discord.DiscordException):
            await self.handle_on_command_error(ctx, error)

        self.add_command(shutdown)


if __name__ == "__main__":
    exit()



import asyncio
import logging
import signal
import camera
import controller
import discordbot
import discord
import logger
import json

class Esieabot:

    def __init__(self) -> None:

        with open("./settings.json") as fd:
            settings = json.load(fd)
            self.camera_settings = settings["camera_settings"]
            self.discord_settings = settings["discord_settings"]
            self.logging_settings = settings["logging_settings"]
            
        self.logger: logging.Logger = logger.LoggerBuilder(
            "Esieabot"
        ).add_level(
            self.logging_settings["level"]
        ).add_format(
            self.logging_settings["message_format"],
            self.logging_settings["date_format"]
        ).build()

        self.logger.info("Starting initialization...")

        self.controller = controller.Controller()
        self.discordbot = discordbot.DiscordBot(self, self.discord_settings)
        self.camera = camera.Camera(self.camera_settings)

        self.logger.info("Done with initialization.")

        try:
            asyncio.run(self.start())
        except RuntimeError:
            pass
        finally:
            exit()


    async def start(self) -> None:

        self.logger.info("Starting esieabot...")

        running_loop = asyncio.get_running_loop()
        for signal_enum in [signal.SIGINT, signal.SIGTERM]:
            running_loop.add_signal_handler(signal_enum, running_loop.stop)
        
        try:
            self.running_tasks = asyncio.gather(
                self.discordbot.start(self.discordbot.token),
                asyncio.to_thread(self.camera.start),
            )
            await self.running_tasks
        except discord.LoginFailure:
            self.logger.critical("Unable to log into Discord. Please check your credentials and Internet connection.")
        except asyncio.CancelledError:
            pass
        finally:
            await self.camera.handle_stop()
            if not self.discordbot.is_closed():
                self.logger.info("Closing the connection to Discord...")
                await self.discordbot.close()
            self.logger.info("Done with shutdown. This process will now exit.")


    def shutdown(self) -> None:
        self.logger.info("Received shutdown signal...")
        self.running_tasks.cancel()
        

if __name__ == "__main__":
    Esieabot()
import logging


class LoggerBuilder:

    def __init__(self, logger_name: str):

        self.logger = logging.getLogger(logger_name)
        self.handler = logging.StreamHandler()
        self.logger.addHandler(self.handler)


    def add_level(self, level: str):

        if level == "DEBUG":
            self.logger.setLevel(logging.DEBUG)
        elif level == "INFO":
            self.logger.setLevel(logging.INFO)
        elif level == "WARNING":
            self.logger.setLevel(logging.WARNING)
        elif level == "ERROR":
            self.logger.setLevel(logging.ERROR)
        elif level == "CRITICAL":
            self.logger.setLevel(logging.CRITICAL)
        else:
            self.logger.setLevel(logging.INFO)

        return self


    def add_format(self, message_format: str, date_format: str):

        self.formatter = logging.Formatter(message_format, date_format)
        self.handler.setFormatter(self.formatter)

        return self


    def build(self):

        return self.logger


if __name__ == "__main__":
    exit()



from enumerations import Rotations
import pigpio


class Motor:

    def __init__(self, pigpio_daemon, gpio_forward, gpio_backward, gpio_enable):
        
        self.pigpio_daemon = pigpio_daemon
        
        self.gpio_forward = gpio_forward
        self.gpio_backward = gpio_backward
        self.gpio_enable = gpio_enable
        
        self.pigpio_daemon.set_mode(self.gpio_forward, pigpio.OUTPUT)
        self.pigpio_daemon.set_mode(self.gpio_backward, pigpio.OUTPUT)
        self.pigpio_daemon.set_mode(self.gpio_enable, pigpio.OUTPUT)


    def rotate_clockwise(self):

        self.rotate(Rotations.CLOCKWISE)


    def rotate_anticlockwise(self):

        self.rotate(Rotations.ANTICLOCKWISE)


    def rotate(self, rotation):

        if rotation is Rotations.CLOCKWISE:
            self.pigpio_daemon.write(self.gpio_forward, pigpio.HIGH)
        elif rotation is Rotations.ANTICLOCKWISE:
            self.pigpio_daemon.write(self.gpio_backward, pigpio.HIGH)
        else:
            return   
        self.pigpio_daemon.write(self.gpio_enable, pigpio.HIGH)


    def stop(self):

        self.pigpio_daemon.write(self.gpio_enable, pigpio.LOW)
        self.pigpio_daemon.write(self.gpio_forward, pigpio.LOW)
        self.pigpio_daemon.write(self.gpio_backward, pigpio.LOW)


if __name__ == "__main__":
    exit()



from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BufferedIOBase
from socketserver import ThreadingMixIn
from threading import Condition


PAGE = """\
<html>
<head>
<title>picamera2 MJPEG streaming ESIEABOT</title>
</head>
<body>
<h1>Picamera2 MJPEG Streaming ESIEABOT</h1>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""


class StreamingHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass
    
    
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
                    with self.server.streaming_output.condition:
                        self.server.streaming_output.condition.wait()
                        frame = self.server.streaming_output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                pass
        else:
            self.send_error(404)
            self.end_headers()


class StreamingOutput(BufferedIOBase):

    def __init__(self):

        self.frame = None
        self.condition = Condition()

    def write(self, frame):

        with self.condition:
            self.frame = frame
            self.condition.notify_all()


class StreamingServer(ThreadingMixIn, HTTPServer):
    
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    exit()





json 

{
	"camera_settings": {
		"streaming_server_port": 7080,
		"video_width": 640,
		"video_height": 480,
		"video_hflip": true,
		"video_vflip": true
	},
	"discord_settings": {
		"command_prefix": "$",
		"owner_id": "",
		"token": ""
	},
	"logging_settings": {
		"date_format": "%H:%M:%S",
		"message_format": "%(levelname)s[%(name)s@%(asctime)s] %(message)s",
		"level": "INFO"
	}
}



$ sudo apt update
$ sudo apt upgrade
$ sudo apt install -y python3-picamera2 --no-install-recommends


