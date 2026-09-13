import cv2
import sys
import time
from typing import Any
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

import calc
from egg_generator import Xorshift

IDLE: Literal[0xFF] = 0xFF
SINGLE: Literal[0xF0] = 0xF0
DOUBLE: Literal[0xF1] = 0xF1


def tracking_blink(
    img: Any,
    roi_x: int,
    roi_y: int,
    roi_w: int,
    roi_h: int,
    threshold: float = 0.9,
    size: int = 41,
    camera: int = 0,
    tk_window: Optional[Any] = None,
) -> Tuple[List[int], List[int], float]:
    eye = img
    last_frame_tk = None

    if sys.platform.startswith('linux'): # all Linux
        backend = cv2.CAP_V4L
    else: # MS Windows/macOS/otherwise
        backend = cv2.CAP_ANY # auto-detect via OpenCV
    video = cv2.VideoCapture(camera,backend)
    video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
    video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
    video.set(cv2.CAP_PROP_BUFFERSIZE,1)

    state = IDLE
    blinks = []
    intervals = []
    prev_time = time.perf_counter()
    eye_width, eye_height = eye.shape[::-1]

    prev_roi = None
    offset_time = 0

    # observe blinks
    while len(blinks)<size or state!=IDLE:
        if tk_window is not None:
            if not tk_window.monitoring and not tk_window.reidentifying:
                tk_window.progress['text'] = "0/0"
                tk_window.monitor_tk_buffer = None
                tk_window.monitor_tk = None
                sys.exit()
        _, frame = video.read()
        time_counter = time.perf_counter()
        roi = cv2.cvtColor(frame[roi_y:roi_y+roi_h,roi_x:roi_x+roi_w],cv2.COLOR_RGB2GRAY)
        if (roi==prev_roi).all():
            continue

        prev_roi = roi
        res = cv2.matchTemplate(roi,eye,cv2.TM_CCOEFF_NORMED)
        _, match, _, max_loc = cv2.minMaxLoc(res)

        cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), (0,0,255), 2)
        if 0.01<match<threshold:
            cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), 255, 2)
            if state==IDLE:
                blinks.append(0)
                interval = (time_counter - prev_time)/1.017
                interval_round = round(interval)
                intervals.append(interval_round)
                print(f"Adv Since Last: {round((time_counter - prev_time)/1.018)} " \
                      f"{(time_counter - prev_time)/1.018}")
                print("blink logged")
                print(f"Intervals {len(intervals)}/{size}")
                if tk_window is not None:
                    tk_window.progress['text'] = f"{len(intervals)}/{size}"

                if len(intervals)==size:
                    offset_time = time_counter

                state = SINGLE
                prev_time = time_counter
            elif state==SINGLE:
                #doubleの判定
                if time_counter - prev_time>0.3:
                    blinks[-1] = 1
                    state = DOUBLE
                    print("double blink logged")
            elif state==DOUBLE:
                pass
        else:
            max_loc = (max_loc[0] + roi_x,max_loc[1] + roi_y)
            bottom_right = (max_loc[0] + eye_width, max_loc[1] + eye_height)
            cv2.rectangle(frame,max_loc, bottom_right, 255, 2)
        if tk_window is None:
            cv2.imshow("view", frame)
            keypress = cv2.waitKey(1)
            if keypress == ord('q'):
                cv2.destroyAllWindows()
                sys.exit()
        else:
            if tk_window.config_json["display_percent"] != 100:
                _, frame_width, frame_height = frame.shape[::-1]
                frame = cv2.resize(
                    frame,
                    (round(frame_width*tk_window.config_json["display_percent"]/100),
                    round(frame_height*tk_window.config_json["display_percent"]/100)
                    ))
            frame_tk = tk_window.cv_image_to_tk(frame)
            tk_window.monitor_tk_buffer = last_frame_tk
            tk_window.monitor_display_buffer['image'] = tk_window.monitor_tk_buffer
            tk_window.monitor_tk = frame_tk
            tk_window.monitor_display['image'] = tk_window.monitor_tk
            last_frame_tk = frame_tk
        if state!=IDLE and time_counter - prev_time>0.7:
            state = IDLE
    if tk_window is None:
        cv2.destroyAllWindows()
    else:
        tk_window.progress['text'] = "0/0"
        frame_tk = None
        last_frame_tk = None
    video.release()
    return (blinks[1:], intervals[1:], offset_time)


def recov(blinks: List[int], rawintervals: List[int]) -> Xorshift:
    intervals: List[int] = rawintervals[1:]
    advanced_frame: int = sum(intervals)
    states: List[int] = calc.reverse_states(blinks, intervals)
    prng: Xorshift = Xorshift(*states)
    states: List[int] = prng.get_state()

    # validation check
    expected_blinks: List[int] = [r & 0xF for r in prng.get_next_rand_sequence(advanced_frame) if (r & 0b1110) == 0]
    paired: List[Tuple[int, int]] = list(zip(blinks, expected_blinks))
    assert all(o == e for o, e in paired)

    result: Xorshift = Xorshift(*states)
    result.get_next_rand_sequence(advanced_frame)
    return result
