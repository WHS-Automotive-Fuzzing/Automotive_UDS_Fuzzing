import cmd
import isotp
import can
import time
from module.logger import * 
from module.uds_send import UDSSender

WAIT_RESPONSE_TIME = 0.2  # seconds
RESET_WAIT_RESPONSE_TIME = 2
RESET_SLEEP_TIME_DIFF_ID = 0.01
RESET_SLEEP_TIME_SAME_ID = 0.05
prev_udsid = 0x0000

# CAN IDs and corresponding response IDs
Response_ID = {
    0x73E: 0x7A8,
    0x70E: 0x778,
    0x74C: 0x7B6,
    0x723: 0x78D,
    0x74B: 0x7B5,
    0x74A: 0x7B4,
    0x17FC0084: 0x17FE0084,
}

class UDSMessage:
    def __init__(self, udsid, sid, data: list[int], depth, bus):
        self.udsid = udsid
        self.sid = sid
        self.data = data
        self.depth = depth
        self.bus = bus
        self.response = None

        self.error_detected = False
        self.failed = False
        self.fail_level = 0

    def error_handler(self, e):
        if isinstance(e, isotp.errors.FlowControlTimeoutError):
            self.error_detected = True

    def CheckUDSMessage(self):
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.udsid, rxid=Response_ID[self.udsid])
        params = {"tx_padding": 0xFF}
        stack = isotp.CanStack(bus=self.bus, address=addr, params=params, error_handler=self.error_handler)
        sender = UDSSender(stack)

        print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Sending UDS Message: {self.data}")

        # diagnosticmode_fail = self.StartDiagnosticMode(sender)
        # if diagnosticmode_fail or self.error_detected:
        #     self.ECUReset(sender)  # ← 반드시 Reset
        #     return self.fail_level

        self.FailDetection(sender)

        if self.error_detected:
            print("Error")
            # self.ECUReset(sender)
        elif self.failed:
            print("Fail")
            # self.ECUReset(sender)

        self.ECUReset(sender)
        return self.fail_level
    
    def StartDiagnosticMode(self, sender):
        # Send Tester Present
        Diagnosticmode_fail = False
        success, response = sender.SendTesterPresent(retry_count=3)
        if not success:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 3E 00")

        # Enter Extended Diagnostic Session
        success, response = sender.EnterDiagnosticSession(session_type=0x03, retry_count=3)
        if not success:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 10 03")
            Diagnosticmode_fail = True
        
        return Diagnosticmode_fail

    def Check_ECU_Alive(self, sender):        
        success, _= sender.EnterDiagnosticSession(session_type=0x01, retry_count=5)
        if not success:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}] Fail Detected: no response 10 01")
        
        return success
    
    def Set_Fail_Level(self, Alive):
        if self.failed:
            if not Alive:
                self.fail_level = 3
            else:
                self.fail_level = 2
        else:
            if not Alive:
                self.fail_level = 1
            else:
                self.fail_level = 0
        

    def FailDetection(self, sender):
        # Clear DTC First
        success = sender.SendDTCClear(timeout=WAIT_RESPONSE_TIME)
        if not success:
            print(f"[{self.sid}] DTC Clear Fail.")
            return
        
        # Check DTC before sending message
        success, First_DTC_reponse = sender.SendDTCRequest(timeout=WAIT_RESPONSE_TIME)

        if not success:
            print(f"[{self.sid}] First DTC Request Fail.")
            return
        
        # Send UDS message
        success, _ = sender.SendUDSMessage(self.sid, self.data, timeout=WAIT_RESPONSE_TIME)
        
        # Check DTC after sending message
        success, Second_DTC_reponse = sender.SendDTCRequest(timeout=WAIT_RESPONSE_TIME)

        # if no/negative response or New DTC occur, then regard message as Fail Message
        if not success or (First_DTC_reponse != Second_DTC_reponse):
            print(f"[{self.sid}] Fail Detected: Different DTC Response.")
            self.failed = True
        
        self.Set_Fail_Level(self.Check_ECU_Alive(sender))

        return


    def ECUReset(self, sender):
        global prev_udsid
        print("Reset")

        # Send ECU Reset (Soft Reset - 0x01)
        success, response = sender.SendECUReset(reset_type=0x02, retry_count=3, timeout=RESET_WAIT_RESPONSE_TIME)
        
        if not success:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 11 02")
        else:
            print("Reset Done!")

        prev_udsid = self.udsid
        #print(f"ECU Reset: {time.time()-s_time}")

    def Debug_fail(self):
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.udsid, rxid=Response_ID[self.udsid])
        params = {"tx_padding": 0xFF}
        stack = isotp.CanStack(bus=self.bus, address=addr, params=params, error_handler=self.error_handler)
        sender = UDSSender(stack)

        print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Sending UDS Message: {self.data}")

        self.StartDiagnosticMode(sender)
        if self.diagnosticmodefail or self.error_detected:
            self.ECUReset(sender)  # ← 반드시 Reset
            return self.failed

        # Send UDS message
        success, response = sender.SendUDSMessage(self.sid, self.data, timeout=WAIT_RESPONSE_TIME)
        
        if response:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}] Response: {response.hex()}")

        if self.error_detected:
            return

        # Send multiple Tester Present
        sender.SendTesterPresent(retry_count=3)
        
        # Valid request check
        success, response = sender.EnterDiagnosticSession(session_type=0x01, retry_count=1)
        if not success:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}] no response 10 01")
            self.failed = True

        if self.error_detected:
            self.ECUReset(sender)
            return self.failed


class NegativeResponseCodes(object):
    """
    ISO-14229-1 negative response codes
    """
    POSITIVE_RESPONSE = 0x00
    # 0x01-0x0F ISO SAE Reserved
    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUB_FUNCTION_NOT_SUPPORTED = 0x12
    INCORRECT_MESSAGE_LENGTH_OR_INVALID_FORMAT = 0x13
    RESPONSE_TOO_LONG = 0x14
    # 0x15-0x20 ISO SAE Reserved
    BUSY_REPEAT_REQUEST = 0x21
    CONDITIONS_NOT_CORRECT = 0x22
    # 0x23 ISO SAE Reserved
    REQUEST_SEQUENCE_ERROR = 0x24
    NO_RESPONSE_FROM_SUBNET_COMPONENT = 0x25
    FAILURE_PREVENTS_EXECUTION_OF_REQUESTED_ACTION = 0x26
    # 0x27-0x30 ISO SAE Reserved
    REQUEST_OUT_OF_RANGE = 0x31
    # 0x32 ISO SAE Reserved
    SECURITY_ACCESS_DENIED = 0x33
    # 0x34 ISO SAE Reserved
    INVALID_KEY = 0x35
    EXCEEDED_NUMBER_OF_ATTEMPTS = 0x36
    REQUIRED_TIME_DELAY_NOT_EXPIRED = 0x37
    # 0x38-0x4F Reserved by extended data link security document
    # 0x50-0x6F ISO SAE Reserved
    UPLOAD_DOWNLOAD_NOT_ACCEPTED = 0x70
    TRANSFER_DATA_SUSPENDED = 0x71
    GENERAL_PROGRAMMING_FAILURE = 0x72
    WRONG_BLOCK_SEQUENCE_COUNTER = 0x73
    # 0x74-0x77 ISO SAE Reserved
    REQUEST_CORRECTLY_RECEIVED_RESPONSE_PENDING = 0x78
    # 0x79-0x7D ISO SAE Reserved
    SUB_FUNCTION_NOT_SUPPORTED_IN_ACTIVE_SESSION = 0x7E
    SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION = 0x7F
    # 0x80 ISO SAE Reserved
    RPM_TOO_HIGH = 0x81
    RPM_TOO_LOW = 0x82
    ENGINE_IS_RUNNING = 0x83
    ENGINE_IS_NOT_RUNNING = 0x84
    ENGINE_RUN_TIME_TOO_LOW = 0x85
    TEMPERATURE_TOO_HIGH = 0x86
    TEMPERATURE_TOO_LOW = 0x87
    VEHICLE_SPEED_TOO_HIGH = 0x88
    VEHICLE_SPEED_TOO_LOW = 0x89
    THROTTLE_PEDAL_TOO_HIGH = 0x8A
    THROTTLE_PEDAL_TOO_LOW = 0x8B
    TRANSMISSION_RANGE_NOT_IN_NEUTRAL = 0x8C
    TRANSMISSION_RANGE_NOT_IN_GEAR = 0x8D
    # 0x8E ISO SAE Reserved
    BRAKE_SWITCHES_NOT_CLOSED = 0x8F
    SHIFT_LEVER_NOT_IN_PARK = 0x90
    TORQUE_CONVERTER_CLUTCH_LOCKED = 0x91
    VOLTAGE_TOO_HIGH = 0x92
    VOLTAGE_TOO_LOW = 0x93
    # 0x94-0xEF Reserved for specific conditions not correct
    # 0xF0-0xFE Vehicle manufacturer specific conditions not correct
    # 0xFF ISO SAE Reserved