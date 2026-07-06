"""
NASA Ingenuity Drone Simulation
Mars Mission: Jezero Crater Scout

Hackathon Project Features:
- Mission-control style interface
- Real-time telemetry dashboard
- Autonomous command queue
- Battery tracking
- Martian wind drift simulation
- Obstacle detection
- Flight logging
- Mission report generation
- Safe image loading with fallback shapes

Run:
    python drone_sim.py

Required:
    pip install pillow
"""

import turtle
import tkinter as tk
from PIL import Image
import os
import random
import time
import datetime
import traceback


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

class Config:
    WIDTH = 1000
    HEIGHT = 700

    BG_COLOR = "#160d0a"
    PANEL_COLOR = "#2b1a16"
    TEXT_GREEN = "#00ff9d"
    WARNING_RED = "#ff4757"
    MARS_ORANGE = "#ff6b35"
    MARS_DUST = "#d2691e"
    WHITE = "#f7e9dc"

    # Put these image files in the same folder as this Python file.
    # The simulation will still run if they are missing.
    DRONE_FILE = "Science_jpegPIA23882.webp"
    LOGO_FILE = "images (3).jpg"

    DRONE_GIF = "drone.gif"
    LOGO_GIF = "logo.gif"

    LOG_FILE = "flight_data.log"
    REPORT_FILE = "mission_report.txt"

    HOME_X = -380
    HOME_Y = -180

    BATTERY_DRAIN_MOVING = 0.035
    BATTERY_DRAIN_HOVER = 0.012

    WIND_EFFECT_MIN = -0.35
    WIND_EFFECT_MAX = 0.35

    OBSTACLE_COLLISION_RADIUS = 42
    MOVE_SPEED = 3


# ------------------------------------------------------------
# LOGGER
# ------------------------------------------------------------

class Logger:
    @staticmethod
    def timestamp():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def write(level, message):
        output = f"[{Logger.timestamp()}] [{level}] {message}"
        print(output)

        try:
            with open(Config.LOG_FILE, "a", encoding="utf-8") as file:
                file.write(output + "\n")
        except Exception:
            pass

    @staticmethod
    def info(message):
        Logger.write("INFO", message)

    @staticmethod
    def warning(message):
        Logger.write("WARNING", message)

    @staticmethod
    def error(message):
        Logger.write("ERROR", message)


# ------------------------------------------------------------
# ASSET MANAGER
# ------------------------------------------------------------

class AssetManager:
    """
    Converts JPG/WEBP/PNG images into GIF files that Turtle can use.
    Turtle cannot use most image formats directly, so we convert them safely.
    """

    @staticmethod
    def resize_image(source, output, size):
        if not os.path.exists(source):
            Logger.warning(f"Missing image file: {source}")
            return False

        try:
            image = Image.open(source)

            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.LANCZOS

            image = image.resize(size, resample_filter)

            # Turtle works best with simple GIF files.
            image = image.convert("P", palette=Image.ADAPTIVE)
            image.save(output, "GIF")

            Logger.info(f"Prepared image asset: {source} -> {output}")
            return True

        except Exception as error:
            Logger.error(f"Could not process image {source}: {error}")
            return False

    @staticmethod
    def prepare_assets():
        assets = {
            "drone": AssetManager.resize_image(
                Config.DRONE_FILE,
                Config.DRONE_GIF,
                (85, 85)
            ),
            "logo": AssetManager.resize_image(
                Config.LOGO_FILE,
                Config.LOGO_GIF,
                (105, 105)
            )
        }

        return assets


# ------------------------------------------------------------
# DRAWING HELPERS
# ------------------------------------------------------------

class Drawer:
    @staticmethod
    def draw_rectangle(x, y, width, height, fill_color, outline_color=None):
        pen = turtle.Turtle()
        pen.hideturtle()
        pen.speed(0)
        pen.penup()
        pen.goto(x, y)
        pen.pendown()

        pen.color(outline_color if outline_color else fill_color)
        pen.fillcolor(fill_color)
        pen.begin_fill()

        for _ in range(2):
            pen.forward(width)
            pen.right(90)
            pen.forward(height)
            pen.right(90)

        pen.end_fill()
        pen.penup()

    @staticmethod
    def write_text(x, y, text, color=Config.WHITE, size=13, align="left", bold=False):
        pen = turtle.Turtle()
        pen.hideturtle()
        pen.penup()
        pen.color(color)
        pen.goto(x, y)

        style = "bold" if bold else "normal"
        pen.write(text, align=align, font=("Courier", size, style))
        return pen


# ------------------------------------------------------------
# OBSTACLE
# ------------------------------------------------------------

class Obstacle(turtle.Turtle):
    def __init__(self, x, y, width=2.5, height=2.5, label="ROCK"):
        super().__init__("square")
        self.penup()
        self.speed(0)
        self.color(Config.WARNING_RED)
        self.shapesize(height, width)
        self.goto(x, y)
        self.label = label


# ------------------------------------------------------------
# DRONE
# ------------------------------------------------------------

class DroneActor(turtle.Turtle):
    def __init__(self, shape_name=None):
        # Use image shape only if it was successfully registered.
        if shape_name:
            super().__init__(shape_name)
        else:
            super().__init__("triangle")
            self.color(Config.MARS_ORANGE)

        self.penup()
        self.speed(0)

        self.home_x = Config.HOME_X
        self.home_y = Config.HOME_Y

        self.target_x = self.home_x
        self.target_y = self.home_y

        self.goto(self.home_x, self.home_y)

        self.battery = 100.0
        self.status = "READY"
        self.phase = "MISSION SETUP"

        self.flight_log_count = 0
        self.distance_traveled = 0.0
        self.samples_collected = 0

        self.command_queue = []
        self.current_command = None

        self.crashed = False
        self.wind = 0.0

    def queue_command(self, command):
        if self.crashed:
            return

        if self.battery <= 0:
            return

        self.command_queue.append(command)
        Logger.info(f"Command queued: {command}")

    def execute_next_command(self):
        if self.current_command is not None:
            return

        if not self.command_queue:
            return

        self.current_command = self.command_queue.pop(0)
        Logger.info(f"Executing command: {self.current_command}")

        if self.current_command == "TAKEOFF":
            self.target_y = 80
            self.status = "TAKING OFF"
            self.phase = "AUTONOMOUS FLIGHT"

        elif self.current_command == "FORWARD":
            self.target_x = min(410, self.target_x + 120)
            self.status = "SCOUTING"

        elif self.current_command == "SCAN":
            self.status = "SCANNING"
            self.samples_collected += 1
            self.flight_log_count += 1
            self.current_command = None

        elif self.current_command == "RETURN":
            self.target_x = self.home_x
            self.status = "RETURNING"

        elif self.current_command == "LAND":
            self.target_y = self.home_y
            self.status = "LANDING"

    def update_physics(self):
        if self.crashed:
            self.status = "CRASHED"
            return

        if self.battery <= 0:
            self.battery = 0
            self.status = "POWER DEPLETED"
            self.phase = "MISSION FAILED"
            return

        self.execute_next_command()

        old_x = self.xcor()
        old_y = self.ycor()

        moved = False

        if abs(self.xcor() - self.target_x) > 2:
            step = Config.MOVE_SPEED if self.xcor() < self.target_x else -Config.MOVE_SPEED
            self.setx(self.xcor() + step)
            moved = True

        if abs(self.ycor() - self.target_y) > 2:
            step = Config.MOVE_SPEED if self.ycor() < self.target_y else -Config.MOVE_SPEED
            self.sety(self.ycor() + step)
            moved = True

        # Martian wind drift only while airborne
        if self.ycor() > self.home_y + 20:
            self.wind = random.uniform(Config.WIND_EFFECT_MIN, Config.WIND_EFFECT_MAX)
            self.setx(self.xcor() + self.wind)
            self.battery -= Config.BATTERY_DRAIN_HOVER
        else:
            self.wind = 0.0

        if moved:
            self.battery -= Config.BATTERY_DRAIN_MOVING
            self.flight_log_count += 1

            dx = self.xcor() - old_x
            dy = self.ycor() - old_y
            self.distance_traveled += (dx ** 2 + dy ** 2) ** 0.5

        # Check if command target is reached
        if abs(self.xcor() - self.target_x) <= 3 and abs(self.ycor() - self.target_y) <= 3:
            if self.current_command is not None:
                Logger.info(f"Completed command: {self.current_command}")

            if self.current_command == "LAND":
                self.status = "MISSION COMPLETE"
                self.phase = "TELEMETRY REVIEW"

            self.current_command = None

        self.battery = max(0, self.battery)

    def crash(self):
        if not self.crashed:
            self.crashed = True
            self.status = "CRASHED"
            self.phase = "MISSION FAILED"
            self.battery = 0
            Logger.error("Collision detected. Drone crashed.")


# ------------------------------------------------------------
# SIMULATION ENGINE
# ------------------------------------------------------------

class SimulationEngine:
    def __init__(self):
        Logger.info("Initializing Mars Mission Simulation...")

        self.screen = turtle.Screen()
        self.screen.setup(Config.WIDTH, Config.HEIGHT)
        self.screen.bgcolor(Config.BG_COLOR)
        self.screen.title("Mars Mission: Ingenuity Drone Simulation")
        self.screen.tracer(0)

        self.assets = AssetManager.prepare_assets()
        self.register_shapes()

        self.running = True

        self.setup_background()
        self.setup_environment()
        self.setup_ui()

    def register_shapes(self):
        """
        This fixes the instant-close bug.
        Turtle image files must be registered before they are used as shapes.
        """

        if self.assets.get("drone") and os.path.exists(Config.DRONE_GIF):
            try:
                self.screen.register_shape(Config.DRONE_GIF)
                Logger.info("Registered drone image shape.")
            except Exception as error:
                Logger.warning(f"Could not register drone shape: {error}")
                self.assets["drone"] = False

        if self.assets.get("logo") and os.path.exists(Config.LOGO_GIF):
            try:
                self.screen.register_shape(Config.LOGO_GIF)
                Logger.info("Registered logo image shape.")
            except Exception as error:
                Logger.warning(f"Could not register logo shape: {error}")
                self.assets["logo"] = False

    def setup_background(self):
        Drawer.draw_rectangle(-500, 350, 1000, 90, Config.PANEL_COLOR, Config.MARS_DUST)

        Drawer.write_text(
            -470,
            300,
            "MARS MISSION: INGENUITY SIM | JEZERO CRATER SCOUT",
            Config.MARS_ORANGE,
            17,
            bold=True
        )

        Drawer.write_text(
            -470,
            270,
            "Autonomous drone exploration with wind drift, obstacles, battery tracking, and telemetry.",
            Config.WHITE,
            10
        )

        ground = turtle.Turtle()
        ground.hideturtle()
        ground.speed(0)
        ground.penup()
        ground.goto(-500, Config.HOME_Y - 35)
        ground.pendown()
        ground.color(Config.MARS_DUST)
        ground.width(4)
        ground.forward(1000)

        for _ in range(55):
            dot = turtle.Turtle()
            dot.hideturtle()
            dot.speed(0)
            dot.penup()
            dot.color("#8b4513")
            dot.goto(random.randint(-470, 470), random.randint(-300, -210))
            dot.dot(random.randint(3, 8))

    def setup_environment(self):
        drone_shape = Config.DRONE_GIF if self.assets.get("drone") else None
        self.drone = DroneActor(drone_shape)

        if self.assets.get("logo"):
            self.logo = turtle.Turtle(Config.LOGO_GIF)
            self.logo.penup()
            self.logo.goto(410, 285)
        else:
            Drawer.write_text(380, 285, "NASA", Config.WHITE, 18, bold=True)

        self.obstacles = [
            Obstacle(-70, -175, 2.5, 3, "ROCK FIELD"),
            Obstacle(140, -150, 3, 2.5, "CRATER EDGE"),
            Obstacle(315, -170, 2, 4, "SURFACE HAZARD")
        ]

        self.telemetry = turtle.Turtle()
        self.telemetry.hideturtle()
        self.telemetry.color(Config.TEXT_GREEN)
        self.telemetry.penup()
        self.telemetry.goto(-470, 210)

        self.project_info = turtle.Turtle()
        self.project_info.hideturtle()
        self.project_info.color(Config.WHITE)
        self.project_info.penup()
        self.project_info.goto(170, 210)

    def setup_ui(self):
        self.root = self.screen.getcanvas().winfo_toplevel()
        self.root.configure(bg=Config.BG_COLOR)

        self.frame = tk.Frame(self.root, bg=Config.BG_COLOR)
        self.frame.pack(side=tk.BOTTOM, pady=12)

        controls = [
            ("TAKEOFF", self.takeoff),
            ("FORWARD", self.move_forward),
            ("SCAN AREA", self.scan_area),
            ("AUTO MISSION", self.auto_mission),
            ("RETURN", self.return_home),
            ("LAND", self.land),
            ("RECHARGE", self.recharge),
            ("REPORT", self.generate_report),
        ]

        for text, command in controls:
            button = tk.Button(
                self.frame,
                text=text,
                command=command,
                bg="#321a12",
                fg="white",
                activebackground=Config.MARS_ORANGE,
                activeforeground="white",
                font=("Arial", 10, "bold"),
                width=12,
                relief=tk.RAISED,
                bd=3
            )
            button.pack(side=tk.LEFT, padx=5)

    # --------------------------------------------------------
    # BUTTON COMMANDS
    # --------------------------------------------------------

    def can_accept_command(self):
        if self.drone.crashed:
            Logger.warning("Cannot accept command. Drone has crashed.")
            return False

        if self.drone.battery <= 0:
            Logger.warning("Cannot accept command. Battery depleted.")
            return False

        return True

    def takeoff(self):
        if self.can_accept_command():
            self.drone.queue_command("TAKEOFF")

    def move_forward(self):
        if self.can_accept_command():
            self.drone.queue_command("FORWARD")

    def scan_area(self):
        if self.can_accept_command():
            self.drone.queue_command("SCAN")

    def return_home(self):
        if self.can_accept_command():
            self.drone.queue_command("RETURN")

    def land(self):
        if self.can_accept_command():
            self.drone.queue_command("LAND")

    def auto_mission(self):
        if self.can_accept_command():
            mission = [
                "TAKEOFF",
                "FORWARD",
                "SCAN",
                "FORWARD",
                "SCAN",
                "FORWARD",
                "SCAN",
                "RETURN",
                "LAND"
            ]

            for command in mission:
                self.drone.queue_command(command)

            Logger.info("Full autonomous mission queued.")

    def recharge(self):
        self.drone.battery = 100.0
        self.drone.status = "READY"
        self.drone.phase = "MISSION SETUP"
        self.drone.crashed = False
        self.drone.command_queue.clear()
        self.drone.current_command = None

        self.drone.target_x = self.drone.home_x
        self.drone.target_y = self.drone.home_y
        self.drone.goto(self.drone.home_x, self.drone.home_y)

        Logger.info("Drone recharged and reset to launch pad.")

    # --------------------------------------------------------
    # TELEMETRY
    # --------------------------------------------------------

    def update_telemetry(self):
        altitude = int(self.drone.ycor() - self.drone.home_y)

        queue_display = ", ".join(self.drone.command_queue[:4])
        if len(self.drone.command_queue) > 4:
            queue_display += "..."

        if queue_display == "":
            queue_display = "EMPTY"

        self.telemetry.clear()
        self.telemetry.write(
            f"--- REAL-TIME TELEMETRY ---\n"
            f"STATUS: {self.drone.status}\n"
            f"PHASE: {self.drone.phase}\n"
            f"BATTERY: {self.drone.battery:.1f}%\n"
            f"ALTITUDE: {altitude} m\n"
            f"X-POSITION: {int(self.drone.xcor())}\n"
            f"WIND DRIFT: {self.drone.wind:.2f}\n"
            f"DISTANCE: {self.drone.distance_traveled:.1f} units\n"
            f"SAMPLES: {self.drone.samples_collected}\n"
            f"LOG EVENTS: {self.drone.flight_log_count}\n"
            f"QUEUE: {queue_display}",
            font=("Courier", 12, "bold")
        )

        self.project_info.clear()
        self.project_info.write(
            f"--- HACKATHON PROJECT INFO ---\n"
            f"PROJECT: Mars Drone Simulation\n"
            f"LOCATION: Jezero Crater, Mars\n"
            f"GOAL: Scout terrain autonomously\n"
            f"CHALLENGE: Thin atmosphere + obstacles\n"
            f"SOLUTION: Command queue + telemetry\n"
            f"TECH: Python, Turtle, Tkinter, Pillow\n\n"
            f"MISSION PHASES:\n"
            f"1. Mission Setup\n"
            f"2. Command Queue\n"
            f"3. Autonomous Flight\n"
            f"4. Telemetry Review",
            font=("Courier", 11, "bold")
        )

    def check_collisions(self):
        if self.drone.crashed:
            return

        for obstacle in self.obstacles:
            if self.drone.distance(obstacle) < Config.OBSTACLE_COLLISION_RADIUS:
                self.drone.crash()

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    def generate_report(self):
        altitude = int(self.drone.ycor() - self.drone.home_y)

        report = f"""
NASA INGENUITY DRONE SIMULATION
MARS MISSION REPORT

Generated:
{Logger.timestamp()}

Mission Location:
Jezero Crater, Mars

Mission Objective:
Simulate an autonomous Mars scouting drone that can take off, follow a command queue,
scan terrain, respond to wind drift, avoid obstacles, and return telemetry data.

Final Drone Status:
Status: {self.drone.status}
Mission Phase: {self.drone.phase}
Battery Remaining: {self.drone.battery:.1f}%
Final Altitude: {altitude} m
Distance Traveled: {self.drone.distance_traveled:.1f} simulation units
Samples Collected: {self.drone.samples_collected}
Flight Log Events: {self.drone.flight_log_count}

Hackathon Features Demonstrated:
- Modular simulation design
- Real-time telemetry dashboard
- Autonomous command queue
- Mars-inspired physics constraints
- Wind drift simulation
- Obstacle detection
- Battery drain model
- Mission report generation
- NASA-inspired interface

Technology Used:
- Python
- Turtle graphics
- Tkinter controls
- Pillow image processing

Conclusion:
This project demonstrates how autonomous systems can support future Mars missions
where direct human control is limited by distance, communication delay, and risk.
"""

        try:
            with open(Config.REPORT_FILE, "w", encoding="utf-8") as file:
                file.write(report)

            Logger.info(f"Mission report generated: {Config.REPORT_FILE}")
            self.show_popup("Mission Report", f"Mission report saved as {Config.REPORT_FILE}")

        except Exception as error:
            Logger.error(f"Could not generate report: {error}")
            self.show_popup("Error", f"Could not generate report:\n{error}")

    def show_popup(self, title, message):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.configure(bg=Config.PANEL_COLOR)
        popup.geometry("440x180")

        label = tk.Label(
            popup,
            text=message,
            bg=Config.PANEL_COLOR,
            fg=Config.WHITE,
            font=("Courier", 11, "bold"),
            wraplength=390
        )
        label.pack(pady=32)

        close_button = tk.Button(
            popup,
            text="CLOSE",
            command=popup.destroy,
            bg=Config.MARS_ORANGE,
            fg="white",
            font=("Arial", 10, "bold")
        )
        close_button.pack()

    # --------------------------------------------------------
    # MAIN GAME LOOP
    # --------------------------------------------------------

    def game_loop(self):
        try:
            if self.running:
                self.drone.update_physics()
                self.check_collisions()
                self.update_telemetry()
                self.screen.update()

                # Runs again after 20 milliseconds.
                self.screen.ontimer(self.game_loop, 20)

        except Exception as error:
            Logger.error(f"Simulation error: {error}")
            Logger.error(traceback.format_exc())
            self.show_popup("Simulation Error", str(error))

    def run(self):
        Logger.info("Simulation started.")
        self.game_loop()
        self.screen.mainloop()


# ------------------------------------------------------------
# PROGRAM START
# ------------------------------------------------------------

if __name__ == "__main__":
    try:
        sim = SimulationEngine()
        sim.run()

    except Exception as error:
        print("\nThe simulation crashed before opening correctly.")
        print("Error:")
        print(error)
        print("\nFull details:")
        traceback.print_exc()

        input("\nPress Enter to close...")
