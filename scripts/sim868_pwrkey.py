#!/usr/bin/python3
"""Pulse the Waveshare SIM868 PWRKEY input."""
import time

import RPi.GPIO as GPIO


PWRKEY_PIN = 7
PWRKEY_LOW_SECONDS = 4


def main() -> None:
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PWRKEY_PIN, GPIO.OUT)
    try:
        GPIO.output(PWRKEY_PIN, GPIO.LOW)
        time.sleep(PWRKEY_LOW_SECONDS)
        GPIO.output(PWRKEY_PIN, GPIO.HIGH)
    finally:
        GPIO.cleanup(PWRKEY_PIN)


if __name__ == "__main__":
    main()