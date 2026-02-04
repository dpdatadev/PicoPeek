# Beep notification when a new device is connected on the network (todo)
# V0 - beep notification whenever we <insert task>

from machine import Pin
from time import sleep

def test_func() -> bool:
    return True

def notify() -> None:
    buzzer = Pin(15, Pin.OUT)
    onboard_led = Pin("LED", Pin.OUT)
    buzzer.value(1)
    onboard_led.toggle()
    sleep(0.75)
    onboard_led.toggle()
    buzzer.value(0)
    

if __name__ == '__main__':
    notify()
