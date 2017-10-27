#!/usr/bin/env python
import time

from ant.core import driver
from ant.core import node

from PowerMeterTx import PowerMeterTx
from FECTrainer import FECTrainer
from SpeedCadenceSensorRx import SpeedCadenceSensorRx
from config import DEBUG, LOG, NETKEY, POWER_CALCULATOR, POWER_SENSOR_ID, SENSOR_TYPE, SPEED_SENSOR_ID, TRAINER_SENSOR_ID

antnode = None
speed_sensor = None
power_meter = None
trainer = None

try:
    print "Using " + POWER_CALCULATOR.__class__.__name__

    stick = driver.USB2Driver(None, log=LOG, debug=DEBUG)
    antnode = node.Node(stick)
    print "Starting ANT node"
    antnode.start()
    key = node.NetworkKey('N:ANT+', NETKEY)
    antnode.setNetworkKey(0, key)

    print "Starting FE-C trainer"
    try:
        # create trainer
        trainer = FECTrainer(antnode, TRAINER_SENSOR_ID)
        trainer.open()
        print "Started FE-C trainer ID " + TRAINER_SENSOR_ID
    except Exception as e:
        print "trainer error: " + e.message
        trainer = None

    # Notify the power meter every time we get a calculated power value
    POWER_CALCULATOR.notify_change(power_meter)

    print "Main wait loop"
    while True:
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            break

except Exception as e:
    print "Exception: "+repr(e)
finally:
    if speed_sensor:
        print "Closing speed sensor"
        speed_sensor.close()
        speed_sensor.unassign()
    if power_meter:
        print "Closing power meter"
        power_meter.close()
        power_meter.unassign()
    if antnode:
        print "Stopping ANT node"
        antnode.stop()
