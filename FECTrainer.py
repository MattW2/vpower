import sys
from ant.core import message
from ant.core import event
from ant.core.constants import *
from ant.core.exceptions import ChannelError

from constants import *
from config import VPOWER_DEBUG

CHANNEL_PERIOD = 8192


# Transmitter for Bicycle Power ANT+ sensor
class FECTrainer(event.EventCallback):
    # current state of our virtual FE-C trainer
    # this should mirror the state the of the computrainer
    class TrainerData:
        def __init__(self):
            self.eventCount = 0
            self.eventTime = 0
            self.cadence = 0
            self.speed = 0
            self.speed_is_virtual = False
            self.accumulated_power = 0
            self.instantaneous_power = 0
            self.targetPower = 0
            self.resistance = 0
            self.power_cal_needed = False
            self.resistance_cal_needed = True
            self.target_power_limits = 0
            self.state = 0   # see sec 6.5.2.7, table 6-10
            self.lap = 0     # flips btw. 0 and 1 to indicate a lap event


    def __init__(self, antnode, sensor_id):
        self.antnode = antnode

        # Get the channel
        self.channel = antnode.getFreeChannel()
        try:
            self.channel.name = 'C:REALTIME'
            self.channel.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_TRANSMIT)
            self.channel.setID(TRAINER_DEVICE_TYPE, sensor_id, 0)
            self.channel.setPeriod(CHANNEL_PERIOD)
            self.channel.setFrequency(57)
        except ChannelError as e:
            print "Channel config error: " + e.message

        self.observer = None
        self.trainerData = FECTrainer.TrainerData()
        self.slot = -1
        self.msgs = self.msgGenerator()
        self.msgs.send(None)

    def notify_change(self, observer):
        self.obesrver = observer

    def open(self):
        self.channel.open()
        self.channel.registerCallback(self)  # -> will callback process(msg) method below

    def close(self):
        self.channel.close()

    def unassign(self):
        self.channel.unassign()

    def process(self, msg):
        if VPOWER_DEBUG: print "process called with msg " + dir(msg)
        
        if isinstance(msg, message.ChannelRequestMessage):
            which = msg.getMessageID()
            payload = self.makeCommonPage(which)

        elif isinstance(msg, message.ChannelStatusMessage):
            if msg.getStatus() == EVENT_CHANNEL_CLOSED:
                open()

        elif isinstance(msg, message.ChannelBroadcastDataMessage):
            if VPOWER_DEBUG: print "Rx: ", ':'.join(x.encode('hex') for x in msg.getPayload())
            pass

        elif isinstance(msg, message.ChannelAcknowledgeDataMessage):
            if VPOWER_DEBUG: print "Rx: ", ':'.join(x.encode('hex') for x in msg.getPayload())
            return

        ant_msg = message.ChannelBroadcastDataMessage(self.channel.number, data=payload)
        sys.stdout.write('+')
        sys.stdout.flush()
        if VPOWER_DEBUG: print 'Write message to ANT stick on channel ' + repr(self.channel.number)
        self.antnode.driver.write(ant_msg.encode())
            

    def update(self, power):
        if VPOWER_DEBUG: print 'PowerMeterTx: update called with power ', power
        self.powerData.eventCount = (self.powerData.eventCount + 1) & 0xff
        if VPOWER_DEBUG: print 'eventCount ', self.powerData.eventCount
        self.powerData.cumulativePower = (self.powerData.cumulativePower + int(power)) & 0xffff
        if VPOWER_DEBUG: print 'cumulativePower ', self.powerData.cumulativePower
        self.powerData.instantaneousPower = int(power)
        if VPOWER_DEBUG: print 'instantaneousPower ', self.powerData.instantaneousPower

        payload = chr(0x10)  # standard power-only message
        payload += chr(self.powerData.eventCount)
        payload += chr(0xFF)  # Pedal power not used
        payload += chr(0xFF)  # Cadence not used
        payload += chr(self.powerData.cumulativePower & 0xff)
        payload += chr(self.powerData.cumulativePower >> 8)
        payload += chr(self.powerData.instantaneousPower & 0xff)
        payload += chr(self.powerData.instantaneousPower >> 8)

        ant_msg = message.ChannelBroadcastDataMessage(self.channel.number, data=payload)
        sys.stdout.write('+')
        sys.stdout.flush()
        if VPOWER_DEBUG: print 'Write message to ANT stick on channel ' + repr(self.channel.number)
        self.antnode.driver.write(ant_msg.encode())

    def msgGenerator(self):
        slot = yield
        while True:
            slot = (yield CommonPage(0x50).fullpage())
            slot = (yield CommonPage(0x50).fullpage())
            for x in range(10):
                slot = (yield GeneralFEData(slot).fullpage())
                slot = (yield SpecificTrainerData(slot).fullpage())
                slot = (yield SpecificTrainerData(slot).fullpage())

            slot = (yield self.makeCommonPage(0x51))
            slot = (yield self.makeCommonPage(0x51))
            slot = (yield SpecificTrainerData(slot).fullpage())
            for x in range(10):
                slot = (yield GeneralFEData(slot).fullpage())
                slot = (yield SpecificTrainerData(slot).fullpage())
                slot = (yield SpecificTrainerData(slot).fullpage())
            slot = (yield GeneralFEData(slot).fullpage())

    def nextMessage(self, slot):
        try:
            return self.msgs.send(slot)
        except StopIteration as e:
            traceback.print_exc()

    def sendNextMessage(self,slot):
        payload = self.nextMessage(slot)
        if VPOWER_DEBUG: print 'Sending slot %d msg %x' % (slot, ord(payload[0]))
        ant_msg = message.ChannelBroadcastDataMessage(self.channel.number, data=payload)
        self.antnode.driver.write(ant_msg.encode())
        return

        if VPOWER_DEBUG: print 'sending message in slot %d' % (self.slot)

        if self.slot == -1:
            payload = chr(0) * 8
            self.slot += 1

        if self.slot in [0,1]:
            payload = self.makeCommonPage(self.nextMessageID)
            self.nextMessageID = [ self.nextMessageID, [ 0x51, 0x50 ][self.nextMessageID - 0x50] ][self.slot]
            
        elif self.slot:
            payload = GeneralFEData().fullpage()

        ant_msg = message.ChannelBroadcastDataMessage(self.channel.number, data=payload.decode("ascii"))
        self.antnode.driver.write(ant_msg.encode())
            
        self.slot += 1
        if self.slot > 65:
            self.slot = 0

class DataPage(object):
    def __init__(self, pagenumber):
        self.page = chr(pagenumber) + chr(0x00) * 7

    @property
    def pageNumber(self):
        return ord(self.page[0])

    @pageNumber.setter
    def pageNumber(self, num):
        self.page = chr(num & 0xff) + self.page[1:7]
        
    @property
    def data(self):
        return self.page[1:]

    @data.setter
    def data(self, pagebytes):
        if isinstance(pagebytes, list):
            pb = ''.join(map(chr,pagebytes))
        else:
            pb = pagebytes
            
        self.page = self.page[0] + pb

    def fullpage(self):
        return self.page

class CommonPage(DataPage):
    def __init__(self, which):
        super(CommonPage,self).__init__(which)
        if which == 0x50:
            msg = [ 0xff, 0xff, # model #
                    0x01,       # hardware version
                    0xff, 0x00, # mfg id
                    0x00, 0x01 ]
        elif which == 0x51:
            msg = [ 0xff,
                    0xff,
                    0x01,
                    0xce, 0xfa, 0xed, 0xfe ]
        self.data = msg
        return
        self.data = ''.join(map(chr, msg))
        
class SpecificTrainerData(DataPage):
    def __init__(self, slot):
        super(SpecificTrainerData,self).__init__(25)
        msg = [slot & 0xff, 0xff, 0x00, 0x00, 0x00, 0x02 | 0x20, 0x00]
        self.data = ''.join(map(chr, msg))

class GeneralFEData(DataPage):
    def __init__(self, slot):
        super(GeneralFEData,self).__init__(16)
        data = chr(25) # trainer
        data += chr(slot & 0xff)  # accum time
        data += chr(0)  # accum distance
        data += chr(0xff) + chr(0xff) # speed == invalid
        data += chr(0xff) # hr == invalid
        data += chr(0x0 | 0x20) # no hr, no distance, speed is real | device is READY
        self.data = data
    
    
