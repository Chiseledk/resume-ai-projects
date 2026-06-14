# -*- coding: UTF-8 -*-
# MindPlus
# Python
import sys
import time

sys.path.append("/root/mindplus/.lib/thirdExtension/liliang-gravityvoicerecognition-thirdex")

from pinpong.board import Board, Pin
from pinpong.extension.unihiker import *
from pinpong.libs.dfrobot_dht20 import DHT20
from pinpong.libs.dfrobot_huskylens import Huskylens
from unihiker import GUI
from DFRobot_DF2301Q import *


# Config
LIGHT_THRESHOLD = 100
TEMP_THRESHOLD = 28.0
VOICE_VOLUME = 5
WAKE_TIME = 20
LOOP_INTERVAL = 0.1
UI_REFRESH_INTERVAL = 0.6
PROMPT_COOLDOWN = 10
ACTION_DISPLAY_SECONDS = 1.8
LIGHT_DISPLAY_STEP = 5
TEMP_DISPLAY_STEP = 0.5
HUMIDITY_DISPLAY_STEP = 1
FACE_CHECK_INTERVAL = 0.3
AUTHORIZED_FACE_ID = 1
LED_PIN = 21

# Voice command IDs. Update these if your voice module command table changes.
CMD_WAKE = 1
CMD_HELLO = 5
CMD_LIGHT_ON = 6
CMD_LIGHT_OFF = 7
CMD_CONFIRM = 8
CMD_AIR_ON = 138
CMD_AIR_OFF = 139

QUESTION_LIGHT = "light"
QUESTION_AIR = "air"

FACE_AUTHORIZED = "authorized"
FACE_UNAUTHORIZED = "unauthorized"
FACE_MISSING = "missing"
FACE_ERROR = "error"

TITLE = "\u884c\u8f66\u52a9\u624b"
WAITING = "\u7b49\u5f85\u8bed\u97f3\u6307\u4ee4..."
LIGHT_LABEL = "\u4eae\u5ea6"
TEMP_LABEL = "\u6e29\u5ea6"
HUMIDITY_LABEL = "\u6e7f\u5ea6"
FACE_LABEL = "\u4eba\u50cf"


def round_to_step(value, step):
    if value is None:
        return None
    return round(value / step) * step


def format_sensor_value(value):
    if value is None:
        return "--"
    if int(value) == value:
        return str(int(value))
    return str(value)


def face_status_text(face_status):
    if face_status == FACE_AUTHORIZED:
        return "\u9a7e\u9a76\u5458\u5df2\u6388\u6743"
    if face_status == FACE_UNAUTHORIZED:
        return "\u975e\u6388\u6743\u4eba\u5458"
    if face_status == FACE_MISSING:
        return "\u672a\u68c0\u6d4b\u5230\u9a7e\u9a76\u5458"
    if face_status == FACE_ERROR:
        return "\u4eba\u50cf\u6a21\u5757\u5f02\u5e38"
    return "\u672a\u542f\u7528"


def is_driver_authorized(face_status):
    return face_status == FACE_AUTHORIZED


def show_auth_required(gui):
    draw_message(gui, "\u8bf7\u5148\u8bc6\u522b\u9a7e\u9a76\u5458", color="red", font_size=22)


def setup_led():
    try:
        led = Pin(LED_PIN, Pin.OUT)
        led.write_digital(0)
        return led
    except Exception as err:
        print("\u521d\u59cb\u5316LED\u706f\u5931\u8d25:", err)
        return None


def set_light_output(led, light_on):
    if led is None:
        return
    try:
        led.write_digital(1 if light_on else 0)
    except Exception as err:
        print("\u63a7\u5236LED\u706f\u5931\u8d25:", err)


def make_home_snapshot(light_value, temp, humidity, light_on, air_on, face_status):
    display_light = round_to_step(light_value, LIGHT_DISPLAY_STEP)
    display_temp = round_to_step(temp, TEMP_DISPLAY_STEP)
    display_humidity = round_to_step(humidity, HUMIDITY_DISPLAY_STEP)
    return (
        display_light,
        display_temp,
        display_humidity,
        light_on,
        air_on,
        face_status,
    )


def draw_home(gui, light_value, temp, humidity, light_on, air_on, face_status):
    gui.clear()
    light_value = format_sensor_value(light_value)
    temp = format_sensor_value(temp)
    humidity = format_sensor_value(humidity)

    gui.draw_text(text=TITLE, x=56, y=46, color="blue", font_size=24)
    gui.draw_text(text=WAITING, x=42, y=88, color="black", font_size=18)
    gui.draw_text(text="%s: %s" % (LIGHT_LABEL, light_value), x=16, y=16, color="green", font_size=15)
    gui.draw_text(text="%s: %s\u2103" % (TEMP_LABEL, temp), x=118, y=16, color="red", font_size=15)

    if humidity != "--":
        gui.draw_text(text="%s: %s%%" % (HUMIDITY_LABEL, humidity), x=16, y=122, color="purple", font_size=15)

    light_text = "\u706f: \u5f00" if light_on else "\u706f: \u5173"
    air_text = "\u7a7a\u8c03: \u5f00" if air_on else "\u7a7a\u8c03: \u5173"
    gui.draw_text(text=light_text, x=16, y=150, color="orange", font_size=15)
    gui.draw_text(text=air_text, x=118, y=150, color="blue", font_size=15)
    gui.draw_text(text="%s: %s" % (FACE_LABEL, face_status_text(face_status)), x=16, y=178, color="black", font_size=15)


def draw_question(gui, question_type, light_value, temp):
    gui.clear()
    if question_type == QUESTION_LIGHT:
        gui.draw_text(text="\u5149\u7ebf\u8f83\u6697", x=54, y=64, color="blue", font_size=24)
        gui.draw_text(text="\u662f\u5426\u9700\u8981\u5f00\u706f\uff1f", x=32, y=106, color="black", font_size=21)
        gui.draw_text(text="\u5f53\u524d\u4eae\u5ea6: %s" % light_value, x=42, y=144, color="green", font_size=16)
    elif question_type == QUESTION_AIR:
        gui.draw_text(text="\u6e29\u5ea6\u8f83\u9ad8", x=54, y=64, color="red", font_size=24)
        gui.draw_text(text="\u662f\u5426\u9700\u8981\u5f00\u7a7a\u8c03\uff1f", x=22, y=106, color="black", font_size=21)
        gui.draw_text(text="\u5f53\u524d\u6e29\u5ea6: %s\u2103" % temp, x=40, y=144, color="red", font_size=16)


def draw_message(gui, message, color="blue", font_size=24):
    gui.clear()
    gui.draw_text(text=message, x=36, y=100, color=color, font_size=font_size)


def read_humidity(dht20):
    for method_name in ("humidity", "humi", "hum"):
        method = getattr(dht20, method_name, None)
        if method is None:
            continue
        try:
            return round(method(), 1)
        except Exception:
            return None
    return None


def read_sensors(dht20):
    try:
        light_value = light.read()
    except Exception as err:
        print("\u8bfb\u53d6\u5149\u7ebf\u4f20\u611f\u5668\u5931\u8d25:", err)
        light_value = None

    try:
        temp = round(dht20.temp_c(), 1)
    except Exception as err:
        print("\u8bfb\u53d6\u6e29\u5ea6\u4f20\u611f\u5668\u5931\u8d25:", err)
        temp = None

    humidity = read_humidity(dht20)
    return light_value, temp, humidity


def result_has_id(result, target_id):
    if result is None:
        return False
    if isinstance(result, (list, tuple)):
        for item in result:
            if result_has_id(item, target_id):
                return True
        return False
    if isinstance(result, dict):
        return result.get("ID") == target_id or result.get("id") == target_id
    return getattr(result, "ID", None) == target_id or getattr(result, "id", None) == target_id


def request_authorized_face(huskylens):
    for method_name in ("is_appear", "isAppear"):
        method = getattr(huskylens, method_name, None)
        if method is None:
            continue
        try:
            if method(AUTHORIZED_FACE_ID, "blocks"):
                return True
        except Exception:
            pass

    for method_name in ("command_request_blocks_by_id", "command_request_by_id"):
        method = getattr(huskylens, method_name, None)
        if method is None:
            continue
        try:
            if result_has_id(method(AUTHORIZED_FACE_ID), AUTHORIZED_FACE_ID):
                return True
        except Exception:
            pass

    for method_name in ("command_request_blocks_learned", "command_request_learned"):
        method = getattr(huskylens, method_name, None)
        if method is None:
            continue
        try:
            if result_has_id(method(), AUTHORIZED_FACE_ID):
                return True
        except Exception:
            pass

    return False


def read_face_status(huskylens):
    try:
        huskylens.command_request()
        if request_authorized_face(huskylens):
            return FACE_AUTHORIZED
        if huskylens.is_appear_direct("blocks"):
            return FACE_UNAUTHORIZED
        return FACE_MISSING
    except Exception as err:
        print("\u8bfb\u53d6\u4eba\u50cf\u8bc6\u522b\u6a21\u5757\u5931\u8d25:", err)
        return FACE_ERROR


def setup():
    Board().begin()
    gui = GUI()
    led = setup_led()
    voice = DFRobot_DF2301Q_I2C()
    dht20 = DHT20()
    huskylens = Huskylens()

    voice.set_volume(VOICE_VOLUME)
    voice.set_mute_mode(0)
    voice.set_wake_time(WAKE_TIME)

    huskylens.command_request_algorthim("ALGORITHM_FACE_RECOGNITION")
    huskylens.command_request_customnames(1, "Driver")
    return gui, voice, dht20, huskylens, led


def wait_for_driver_auth(gui, huskylens):
    draw_message(gui, "\u8bf7\u8bc6\u522b\u9a7e\u9a76\u5458", color="red", font_size=24)
    last_status = None

    while True:
        face_status = read_face_status(huskylens)
        if face_status == FACE_AUTHORIZED:
            draw_message(gui, "\u9a7e\u9a76\u5458\u5df2\u6388\u6743", color="green", font_size=24)
            time.sleep(0.8)
            return FACE_AUTHORIZED

        if face_status != last_status:
            last_status = face_status
            if face_status == FACE_UNAUTHORIZED:
                draw_message(gui, "\u975e\u6388\u6743\u4eba\u5458", color="red", font_size=24)
            elif face_status == FACE_ERROR:
                draw_message(gui, "\u4eba\u50cf\u6a21\u5757\u5f02\u5e38", color="red", font_size=22)
            else:
                draw_message(gui, "\u8bf7\u8bc6\u522b\u9a7e\u9a76\u5458", color="red", font_size=24)

        time.sleep(FACE_CHECK_INTERVAL)


def main():
    gui, voice, dht20, huskylens, led = setup()

    pending_question = None
    last_prompt_at = {
        QUESTION_LIGHT: 0,
        QUESTION_AIR: 0,
    }
    last_ui_refresh = 0
    message_until = 0
    light_on = False
    air_on = False
    last_home_snapshot = None

    print("===== \u884c\u8f66\u667a\u80fd\u8f85\u52a9\u7cfb\u7edf\u7b49\u5f85\u9a7e\u9a76\u5458\u6388\u6743 =====")
    draw_message(gui, TITLE, color="blue", font_size=26)
    time.sleep(0.8)
    face_status = wait_for_driver_auth(gui, huskylens)
    print("===== \u9a7e\u9a76\u5458\u5df2\u6388\u6743\uff0c\u884c\u8f66\u667a\u80fd\u8f85\u52a9\u7cfb\u7edf\u5df2\u542f\u52a8 =====")

    while True:
        now = time.time()
        light_value, temp, humidity = read_sensors(dht20)

        if pending_question is None and now >= message_until:
            home_snapshot = make_home_snapshot(light_value, temp, humidity, light_on, air_on, face_status)
            if home_snapshot != last_home_snapshot and (now - last_ui_refresh) >= UI_REFRESH_INTERVAL:
                draw_home(gui, home_snapshot[0], home_snapshot[1], home_snapshot[2], light_on, air_on, face_status)
                last_home_snapshot = home_snapshot
                last_ui_refresh = now

        if (
            light_value is not None
            and light_value < LIGHT_THRESHOLD
            and not light_on
            and is_driver_authorized(face_status)
            and pending_question is None
            and now - last_prompt_at[QUESTION_LIGHT] >= PROMPT_COOLDOWN
        ):
            pending_question = QUESTION_LIGHT
            last_home_snapshot = None
            last_prompt_at[QUESTION_LIGHT] = now
            draw_question(gui, QUESTION_LIGHT, light_value, temp)
            voice.play_by_CMDID(2)

        if (
            temp is not None
            and temp > TEMP_THRESHOLD
            and not air_on
            and is_driver_authorized(face_status)
            and pending_question is None
            and now - last_prompt_at[QUESTION_AIR] >= PROMPT_COOLDOWN
        ):
            pending_question = QUESTION_AIR
            last_home_snapshot = None
            last_prompt_at[QUESTION_AIR] = now
            draw_question(gui, QUESTION_AIR, light_value, temp)
            voice.play_by_CMDID(3)

        cmd_id = voice.get_CMDID()
        if cmd_id != 0:
            print("\u547d\u4ee4ID:", cmd_id)

            if cmd_id == CMD_HELLO:
                pending_question = None
                last_home_snapshot = None
                draw_message(gui, "\u4f60\u597d\u5440\uff01", color="green", font_size=28)
                message_until = now + ACTION_DISPLAY_SECONDS

            elif cmd_id == CMD_WAKE:
                pending_question = None
                last_home_snapshot = None
                draw_message(gui, "\u5df2\u5524\u9192", color="blue", font_size=26)
                message_until = now + ACTION_DISPLAY_SECONDS

            elif cmd_id == CMD_LIGHT_ON:
                pending_question = None
                last_home_snapshot = None
                if is_driver_authorized(face_status):
                    light_on = True
                    set_light_output(led, light_on)
                    draw_message(gui, "\u706f\u5df2\u6253\u5f00", color="orange", font_size=26)
                else:
                    show_auth_required(gui)
                message_until = now + ACTION_DISPLAY_SECONDS

            elif cmd_id == CMD_LIGHT_OFF:
                pending_question = None
                last_home_snapshot = None
                if is_driver_authorized(face_status):
                    light_on = False
                    set_light_output(led, light_on)
                    draw_message(gui, "\u706f\u5df2\u5173\u95ed", color="red", font_size=26)
                else:
                    show_auth_required(gui)
                message_until = now + ACTION_DISPLAY_SECONDS

            elif cmd_id == CMD_AIR_ON:
                pending_question = None
                last_home_snapshot = None
                if is_driver_authorized(face_status):
                    air_on = True
                    draw_message(gui, "\u7a7a\u8c03\u5df2\u6253\u5f00", color="red", font_size=26)
                else:
                    show_auth_required(gui)
                message_until = now + ACTION_DISPLAY_SECONDS

            elif cmd_id == CMD_AIR_OFF:
                pending_question = None
                last_home_snapshot = None
                if is_driver_authorized(face_status):
                    air_on = False
                    draw_message(gui, "\u7a7a\u8c03\u5df2\u5173\u95ed", color="blue", font_size=26)
                else:
                    show_auth_required(gui)
                message_until = now + ACTION_DISPLAY_SECONDS

            elif cmd_id == CMD_CONFIRM:
                if not is_driver_authorized(face_status):
                    show_auth_required(gui)
                    pending_question = None
                elif pending_question == QUESTION_LIGHT:
                    light_on = True
                    set_light_output(led, light_on)
                    draw_message(gui, "\u706f\u5df2\u6253\u5f00", color="orange", font_size=26)
                elif pending_question == QUESTION_AIR:
                    air_on = True
                    draw_message(gui, "\u7a7a\u8c03\u5df2\u6253\u5f00", color="red", font_size=26)
                else:
                    draw_message(gui, "\u597d\u7684\uff0c\u5df2\u6267\u884c", color="blue", font_size=24)
                pending_question = None
                last_home_snapshot = None
                message_until = now + ACTION_DISPLAY_SECONDS

            last_ui_refresh = 0

        time.sleep(LOOP_INTERVAL)


if __name__ == "__main__":
    main()
