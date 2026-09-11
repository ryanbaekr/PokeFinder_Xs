# solves camera start up issues
import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
"""GUI Application for blink detection and seed identification"""
try:
    import cv2
    import os.path
    import rngtool
    import serial
    import serial.tools.list_ports
    import signal
    import sys
    import threading
    import time
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk
    from typing import Any
    from egg_generator import generate
except ImportError as import_fail:
    raise \
    Exception("Could not import the required modules, " \
              "make sure you are running with the correct python version, " \
              "and that packages are installed correctly.") \
    from import_fail

version = sys.version_info
if version[0] < 3 or version[1] < 7:
    raise Exception("Incorrect python version, make sure to run with 3.7+")

os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


class PokeFinderGUI(tk.Frame):
    default_config = {
        "tid": 43313,
        "sid": 28651,
        "shiny_charm": False,
        "oval_charm": True,
        "compatibility_str": "The two seem to get along",
        "gender_ratio_str": "Genderless",
        "masuda": True,
        "image": "./images/cave/eye.png",
        "camera": 0,
        "display_percent": 33,
        "view": [910, 620, 50, 50],
        "thresh": 0.9,
    }

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.rng = None
        self.player_eye = None
        self.player_eye_tk = None
        self.monitoring_thread = None
        self.previewing_thread = None
        self.monitor_tk_buffer = None
        self.monitor_tk = None
        self.raw_screenshot = None
        self.previewing = False
        self.monitoring = False
        self.tracking = False
        self.advances = 0
        self.keypress_advance = -1
        self.config_json = self.default_config
        self.pack()
        self.create_widgets()
        signal.signal(signal.SIGINT, self.__signal_handler)

    def update_ports(self, *_) -> None:
        self.com_ports = [port.device for port in serial.tools.list_ports.comports()]

        self.port_combobox["values"] = self.com_ports

    def create_widgets(self) -> None:
        self.master.title("PokeFinder_Xs")

        # col 0
        ttk.Label(self, text="Progress:").grid(column=0, row=0)
        ttk.Label(self, text="Seed 0:").grid(column=0, row=1)
        ttk.Label(self, text="Seed 1:").grid(column=0, row=2)
        ttk.Label(self, text="Advances:").grid(column=0, row=3)
        ttk.Label(self, text="Keypress Advance:").grid(column=0, row=5)
        ttk.Label(self, text="").grid(column=0, row=6)
        ttk.Label(self, text="").grid(column=0, row=7)
        ttk.Label(self, text="").grid(column=0, row=8)
        ttk.Label(self, text="").grid(column=0, row=9)
        ttk.Label(self, text="TID:").grid(column=0, row=10)
        ttk.Label(self, text="SID:").grid(column=0, row=11)
        ttk.Label(self, text="Shiny Charm:").grid(column=0, row=12)
        ttk.Label(self, text="Oval Charm:").grid(column=0, row=13)
        ttk.Label(self, text="Compatibility:").grid(column=0, row=14)
        ttk.Label(self, text="Gender Ratio:").grid(column=0, row=15)
        ttk.Label(self, text="Masuda:").grid(column=0, row=16)

        self.port_combobox = ttk.Combobox(self, state="readonly", values=[])
        self.port_combobox.grid(column=0, row=17, rowspan=2, columnspan=2)
        self.port_combobox.bind("<Button-1>", self.update_ports)
        self.update_ports()

        # col 1
        self.progress = ttk.Label(self, text="0/0")
        self.progress.grid(column=1, row=0)
        self.seed_0 = ttk.Label(self, text="N/A")
        self.seed_0.grid(column=1, row=1)
        self.seed_1 = ttk.Label(self, text="N/A")
        self.seed_1.grid(column=1, row=2)
        self.adv = ttk.Label(self, text=self.advances)
        self.adv.grid(column=1, row=3)
        self.keypress_adv = ttk.Label(self, text=self.keypress_advance)
        self.keypress_adv.grid(column=1, row=5)
        ttk.Label(self, text="").grid(column=1, row=6)
        ttk.Label(self, text="").grid(column=1, row=7)
        ttk.Label(self, text="").grid(column=1, row=8)
        ttk.Label(self, text="").grid(column=1, row=9)
        self.tid = tk.Spinbox(self, from_= 0, to = 99999, width = 10)
        self.tid.grid(column=1, row=10)
        self.sid = tk.Spinbox(self, from_= 0, to = 99999, width = 10)
        self.sid.grid(column=1, row=11)
        self.shiny_charm = tk.Spinbox(self, from_= 0, to = 1, width = 10)
        self.shiny_charm.grid(column=1, row=12)
        self.oval_charm = tk.Spinbox(self, from_= 0, to = 1, width = 10)
        self.oval_charm.grid(column=1, row=13)
        self.compatibility = ttk.Label(self, text=self.config_json["compatibility_str"])
        self.compatibility.grid(column=1, row=14)
        self.gender_ratio = ttk.Label(self, text=self.config_json["gender_ratio_str"])
        self.gender_ratio.grid(column=1, row=15)
        self.masuda = ttk.Label(self, text=self.config_json["masuda"])
        self.masuda.grid(column=1, row=16)

        # col 2
        self.monitor_display_buffer = ttk.Label(self)
        self.monitor_display_buffer.grid(column=2, row=0, rowspan=64, columnspan=2)
        self.monitor_display = ttk.Label(self)
        self.monitor_display.grid(column=2, row=0, rowspan=64, columnspan=2)

        # col 4
        self.eye_display = ttk.Label(self)
        self.eye_display.grid(column=4, row=0, rowspan=10, columnspan=2)
        ttk.Label(self, text="Camera").grid(column=4, row=10)
        ttk.Label(self, text="Percent").grid(column=4, row=11)
        ttk.Label(self, text="X").grid(column=4, row=12)
        ttk.Label(self, text="Y").grid(column=4, row=13)
        ttk.Label(self, text="W").grid(column=4, row=14)
        ttk.Label(self, text="H").grid(column=4, row=15)
        ttk.Label(self, text="Threshold").grid(column=4, row=16)
        self.monitor_blink_button = ttk.Button(self, text="Monitor Blinks", width=16, command=self.monitor_blinks)
        self.monitor_blink_button.grid(column=4, row=17, columnspan=2)
        self.preview_button = ttk.Button(self, text="Preview", width=16, command=self.preview)
        self.preview_button.grid(column=4, row=18, columnspan=2)

        # col 5
        self.camera_index = tk.Spinbox(self, from_= 0, to = 99, width = 5)
        self.camera_index.grid(column=5, row=10)
        self.display_percent = tk.Spinbox(self, from_ = 0, to = 500, width = 5)
        self.display_percent.grid(column=5, row=11)
        self.pos_x = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_x.grid(column=5, row=12)
        self.pos_y = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_y.grid(column=5, row=13)
        self.pos_w = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_w.grid(column=5, row=14)
        self.pos_h = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_h.grid(column=5, row=15)
        self.pos_th = tk.Spinbox(self, from_= 0, to = 1, width = 5, increment=0.1)
        self.pos_th.grid(column=5, row=16)

        self.tid.delete(0, tk.END)
        self.tid.insert(0, self.config_json["tid"])
        self.sid.delete(0, tk.END)
        self.sid.insert(0, self.config_json["sid"])
        self.shiny_charm.delete(0, tk.END)
        self.shiny_charm.insert(0, self.config_json["shiny_charm"])
        self.oval_charm.delete(0, tk.END)
        self.oval_charm.insert(0, self.config_json["oval_charm"])
        self.camera_index.delete(0, tk.END)
        self.camera_index.insert(0, self.config_json["camera"])
        self.display_percent.delete(0, tk.END)
        self.display_percent.insert(0, self.config_json["display_percent"])
        self.pos_x.delete(0, tk.END)
        self.pos_x.insert(0, self.config_json["view"][0])
        self.pos_y.delete(0, tk.END)
        self.pos_y.insert(0, self.config_json["view"][1])
        self.pos_w.delete(0, tk.END)
        self.pos_w.insert(0, self.config_json["view"][2])
        self.pos_h.delete(0, tk.END)
        self.pos_h.insert(0, self.config_json["view"][3])
        self.pos_th.delete(0, tk.END)
        self.pos_th.insert(0, self.config_json["thresh"])

        self.player_eye = cv2.imread(self.config_json["image"], cv2.IMREAD_GRAYSCALE)
        self.player_eye_tk = self.cv_image_to_tk(self.player_eye)
        self.eye_display["image"] = self.player_eye_tk

        self.after_task()

    @staticmethod
    def cv_image_to_tk(image):
        split = cv2.split(image)

        if len(split) == 3:
            blue, green, red = split

            image = cv2.merge((red, green, blue))

        image = Image.fromarray(image)

        return ImageTk.PhotoImage(image=image)

    def monitor_blinks(self) -> None:
        if not self.monitoring:
            self.monitor_blink_button["text"] = "Stop Monitoring"
            self.monitoring = True
            self.monitoring_thread = threading.Thread(target=self.monitoring_work)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
        else:
            self.monitor_blink_button["text"] = "Monitor Blinks"
            self.monitoring = False

    def monitoring_work(self) -> None:
        ser = serial.Serial(self.port_combobox.get(), 115200)

        # get the controller connected
        for _ in range(0, 2):
            # down
            ser.write(bytearray("+IMM 000004 \n", "ascii"))
            time.sleep(0.1)
            # neutral
            ser.write(bytearray("+IMM 000008 \n", "ascii"))
            time.sleep(0.1)

        # down
        ser.write(bytearray("+IMM 000004 \n", "ascii"))

        blinks, intervals, offset_time = rngtool.tracking_blink(
            self.player_eye,
            *self.config_json["view"],
            threshold=self.config_json["thresh"],
            camera=self.config_json["camera"],
            tk_window=self,
        )

        try:
            self.rng = rngtool.recov(blinks, intervals)
        except AssertionError as failed_deduction:
            raise Exception("Failed to deduce seed from monitored blinks.") from failed_deduction

        waituntil = time.perf_counter()
        diff = round(waituntil - offset_time)
        self.rng.get_next_rand_sequence(diff)

        state = self.rng.get_state()

        print(f"{state[0]:08X}{state[1]:08X} {state[2]:08X}{state[3]:08X}")

        shinies = generate(
            tid=self.config_json["tid"],
            sid=self.config_json["sid"],
            shiny_charm=self.config_json["shiny_charm"],
            oval_charm=self.config_json["oval_charm"],
            compatibility_str=self.config_json["compatibility_str"],
            gender_ratio_str=self.config_json["gender_ratio_str"],
            masuda=self.config_json["masuda"],
            seed0=int(f"{state[0]:08X}{state[1]:08X}", 16),
            seed1=int(f"{state[2]:08X}{state[3]:08X}", 16),
            initial_advances=440,
            max_advances=5440,
        )
        if len(shinies) == 0:
            raise Exception("No shinies found")

        print(shinies[0])
        temp = int(shinies[0]["Advances"])

        while temp > 440:
            if (temp % 600) == 0:
                # neutral
                ser.write(bytearray("+IMM 000008 \n", "ascii"))
                time.sleep(0.5)
                # down
                ser.write(bytearray("+IMM 000004 \n", "ascii"))
                time.sleep(0.5)
            else:
                time.sleep(1)
            temp -= 1
            print(temp)

        self.tracking = False

        blinks, intervals, offset_time = rngtool.tracking_blink(
            self.player_eye,
            *self.config_json["view"],
            threshold=self.config_json["thresh"],
            camera=self.config_json["camera"],
            tk_window=self,
        )

        try:
            self.rng = rngtool.recov(blinks, intervals)
        except AssertionError as failed_deduction:
            raise Exception("Failed to deduce seed from monitored blinks.") from failed_deduction

        self.monitor_blink_button["text"] = "Monitor Blinks"
        self.monitoring = False
        self.preview()

        waituntil = time.perf_counter()
        diff = round(waituntil - offset_time)
        self.rng.get_next_rand_sequence(diff)

        state = self.rng.get_state()

        print(f"{state[0]:08X}{state[1]:08X} {state[2]:08X}{state[3]:08X}")
        self.seed_0["text"] = f"{state[0]:08X}{state[1]:08X}"
        self.seed_1["text"] = f"{state[2]:08X}{state[3]:08X}"

        shinies = generate(
            tid=self.config_json["tid"],
            sid=self.config_json["sid"],
            shiny_charm=self.config_json["shiny_charm"],
            oval_charm=self.config_json["oval_charm"],
            compatibility_str=self.config_json["compatibility_str"],
            gender_ratio_str=self.config_json["gender_ratio_str"],
            masuda=self.config_json["masuda"],
            seed0=int(f"{state[0]:08X}{state[1]:08X}", 16),
            seed1=int(f"{state[2]:08X}{state[3]:08X}", 16),
            initial_advances=0,
            max_advances=400,
        )

        print(shinies[0])
        self.keypress_advance = int(shinies[0]["Advances"])

        self.advances = 1
        self.tracking = True

        while self.tracking:
            self.advances += 1

            if self.advances == (self.keypress_advance + 1):
                # down + b
                ser.write(bytearray("+IMM 000204 \n", "ascii"))
                time.sleep(0.1)
                # down
                ser.write(bytearray("+IMM 000004 \n", "ascii"))

                self.tracking = False
                break
            rand = self.rng.get_next_rand_sequence(1)[-1]
            waituntil += 1.018

            print(f"advances:{self.advances}, blinks:{hex(rand&0xF)}")

            next_time = waituntil - time.perf_counter() or 0
            time.sleep(next_time)

    def preview(self) -> None:
        if not self.previewing:
            self.preview_button["text"] = "Stop Preview"
            self.previewing = True
            self.previewing_thread = threading.Thread(target=self.previewing_work)
            self.previewing_thread.daemon = True
            self.previewing_thread.start()
        else:
            self.preview_button["text"] = "Preview"
            self.previewing = False

    # pylint: disable=too-many-locals
    # previewing live updates at any setting change
    # many local variables are required to do this
    def previewing_work(self):
        """Thread work to be done for the preview function"""
        last_frame_tk = None
        last_camera = self.config_json["camera"]

        if sys.platform.startswith('linux'): # all Linux
            backend = cv2.CAP_V4L
        else: # MS Windows/macOS/otherwise
            backend = cv2.CAP_ANY # auto-detect via OpenCV
        video = cv2.VideoCapture(self.config_json["camera"],backend)
        video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
        video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
        video.set(cv2.CAP_PROP_BUFFERSIZE,1)
        print(f"camera {self.config_json['camera']}")

        while self.previewing:
            if self.config_json["camera"] != last_camera:
                video = cv2.VideoCapture(self.config_json["camera"],backend)
                video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
                video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
                video.set(cv2.CAP_PROP_BUFFERSIZE,1)
                print(f"camera {self.config_json['camera']}")
                last_camera = self.config_json["camera"]

            eye = self.player_eye
            eye_width, eye_height = eye.shape[::-1]
            roi_x, roi_y, roi_w, roi_h = self.config_json["view"]
            if roi_w < eye_width or roi_h < eye_height:
                raise Exception("Width and Height of box cannot be smaller than selected eye image")
            _, frame = video.read()
            if frame is not None:
                try:
                    roi = cv2.cvtColor(frame[roi_y:roi_y+roi_h,roi_x:roi_x+roi_w],
                                       cv2.COLOR_RGB2GRAY)
                except cv2.error as empty_frame:
                    raise Exception("Frame captured is empty, " \
                                    "make sure your camera/window is set up properly.") \
                    from empty_frame
                try:
                    res = cv2.matchTemplate(roi,eye,cv2.TM_CCOEFF_NORMED)
                except cv2.error as bad_location:
                    raise Exception("Tried to read from out of the bounds of " \
                                    "the image read from camera/window, " \
                                    "make sure the position of " \
                                    "the monitoring box is not out of bounds.") \
                    from bad_location
                _, match, _, max_loc = cv2.minMaxLoc(res)

                cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), (0,0,255), 2)
                if 0.01<match<self.config_json["thresh"]:
                    cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), 255, 2)
                else:
                    max_loc = (max_loc[0] + roi_x,max_loc[1] + roi_y)
                    bottom_right = (max_loc[0] + eye_width, max_loc[1] + eye_height)
                    cv2.rectangle(frame,max_loc, bottom_right, 255, 2)
                self.raw_screenshot = frame
                if self.config_json["display_percent"] != 100:
                    _, frame_width, frame_height = frame.shape[::-1]
                    frame = cv2.resize(frame,
                                      (round(frame_width*self.config_json["display_percent"]/100),
                                      round(frame_height*self.config_json["display_percent"]/100)))
                frame_tk = self.cv_image_to_tk(frame)
                self.monitor_tk_buffer = last_frame_tk
                self.monitor_display_buffer['image'] = self.monitor_tk_buffer
                self.monitor_tk = frame_tk
                self.monitor_display['image'] = self.monitor_tk
                last_frame_tk = frame_tk
        self.monitor_tk_buffer = None
        self.monitor_tk = None

    def after_task(self) -> None:
        self.adv["text"] = self.advances
        self.keypress_adv["text"] = self.keypress_advance

        self.config_json["tid"] = int(self.tid.get())
        self.config_json["sid"] = int(self.sid.get())
        self.config_json["shiny_charm"] = int(self.shiny_charm.get())
        self.config_json["oval_charm"] = int(self.oval_charm.get())

        self.config_json["camera"] = int(self.camera_index.get())
        self.config_json["display_percent"] = int(self.display_percent.get())
        self.config_json["view"] = [
            int(self.pos_x.get()),
            int(self.pos_y.get()),
            int(self.pos_w.get()),
            int(self.pos_h.get()),
        ]
        self.config_json["thresh"] = float(self.pos_th.get())

        self.after(100, self.after_task)

    @staticmethod
    def __signal_handler(*_: Any) -> None:
        sys.exit(0)


if __name__ == "__main__":
    root: tk.Tk = tk.Tk()
    app: PokeFinderGUI = PokeFinderGUI(master=root)
    app.mainloop()
