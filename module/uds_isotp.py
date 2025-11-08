import cmd
import isotp
import can
import time

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

        self.diagnosticmodefail = False
        self.error_detected = False
        self.failed = False
        self.NRC = None

    def error_handler(self, e):
        if isinstance(e, isotp.errors.FlowControlTimeoutError):
            #print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Flow Control Error: ", e)
            self.error_detected = True
        #else:
            #print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Error: ", e)

    def CheckUDSMessage(self):
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.udsid, rxid=Response_ID[self.udsid])
        params = {"tx_padding": 0xFF}
        stack = isotp.CanStack(bus=self.bus, address=addr, params=params, error_handler=self.error_handler)

        #print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Sending UDS Message: {self.data}")

        s_time = time.time()
        self.StartDiagnosticMode(stack)
        #print(f"Diagnostic Mode: {time.time()-s_time}")
        if self.diagnosticmodefail or self.error_detected:
            self.ECUReset(stack)  # ← 반드시 Reset
            return self.failed

        s_time = time.time()
        self.FailDetection(stack)
        #print(f"Fail detection: {time.time()-s_time}")

        if self.error_detected:
            self.ECUReset(stack)
            return self.failed

        self.ECUReset(stack)
        return self.failed

    def StartDiagnosticMode(self, stack):
        retry = 0
        while retry < 3:
            stack.send(bytes([0x3E, 0x00]))
            stack.send(bytes([0x3E, 0x00]))
            if self.wait_response(stack, [0x7E, 0x00]):
                break
            retry += 1

        if retry == 3:
            #print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 3E 00")
            self.diagnosticmodefail = True
            return

        retry = 0
        while retry < 3:
            stack.send(bytes([0x10, 0x03]))
            if self.wait_response(stack, [0x50, 0x03]):
                break
            retry += 1

        if retry == 3:
            #print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 10 03")
            self.diagnosticmodefail = True
            return

    def FailDetection(self, stack):
        send_data = [self.sid] + self.data
        stack.send(bytes(send_data))

        s_time = time.time()
        while time.time() - s_time < WAIT_RESPONSE_TIME:
            stack.process()
            if stack.available():
                response = stack.recv(timeout=5)
                if response:
                    self.failed = True
                    return
                
                if response[0] == 0x7F and response[2] == 0x78:
                    return
                #print(f"[{hex(self.udsid)}][{hex(self.sid)}] Response: {response.hex()}")  # Debugging output
                break
            #time.sleep(0.01)

        if self.error_detected:
            return

        # Valid request check
        stack.send(bytes([0x10, 0x01]))
        if not self.wait_response(stack, [0x50, 0x01]):
            self.failed = True
            self.NRC = response[2]
            print(f"Fail Detected! \n[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] [{self.data}] NRC: {response[2]}")

    def wait_response(self, stack, expected_data, timeout=WAIT_RESPONSE_TIME):
        start_time = time.time()
        while time.time() - start_time < timeout:

            stack.process()
            if stack.available():
                response = stack.recv(timeout=5)
                if response[:len(expected_data)] == bytes(expected_data):
                    return True
            #time.sleep(0.01)
        return False

    def reset_wait_response(self, stack, expected_data, timeout=RESET_WAIT_RESPONSE_TIME):
        start_time = time.time()
        while time.time() - start_time < timeout:
            stack.process()
            if stack.available():
                response = stack.recv(timeout=5)
                if len(response)>3 and response[2] == 0x78:
                    response = stack.recv(timeout=5)
                if response[:len(expected_data)] == bytes(expected_data):
                    return True
            #time.sleep(0.01)
        return False

    def ECUReset(self, stack):
        global prev_udsid

        s_time = time.time()

        # 단 한 번만 0x11 0x02 (ECU Reset - Hard Reset) 메시지 전송
        stack.send(bytes([0x11, 0x02]))


        #if not self.reset_wait_response(stack, [0x51, 0x02]):
            #print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 11 02")

        prev_udsid = self.udsid
        #print(f"ECU Reset: {time.time()-s_time}")

    '''def ECUReset(self, stack):
        global prev_udsid
        retry = 0
        s_time = time.time()
        while retry < 3:
            stack.send(bytes([0x11, 0x02]))
            if self.wait_response(stack, [0x51, 0x02]):
                # if self.udsid == prev_udsid:
                #     # time.sleep(RESET_SLEEP_TIME_DIFF_ID)
                #     time.sleep(RESET_SLEEP_TIME_SAME_ID)
                break
            retry += 1
        prev_udsid = self.udsid
        if retry == 3:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 11 02")
        print(f"ECU Reset: {time.time()-s_time}")'''

    def Debug_fail(self):
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.udsid, rxid=Response_ID[self.udsid])
        params = {"tx_padding": 0xFF}
        stack = isotp.CanStack(bus=self.bus, address=addr, params=params, error_handler=self.error_handler)

        print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Sending UDS Message: {self.data}")

        self.StartDiagnosticMode(stack)
        if self.diagnosticmodefail or self.error_detected:
            self.ECUReset(stack)  # ← 반드시 Reset
            return self.failed

        send_data = [self.sid] + self.data
        stack.send(bytes(send_data))

        s_time = time.time()
        while time.time() - s_time < WAIT_RESPONSE_TIME:
            stack.process()
            if stack.available():
                response = stack.recv(timeout=5)

                print(f"[{hex(self.udsid)}][{hex(self.sid)}] Response: {response.hex()}")  # Debugging output
                break
            #time.sleep(0.01)

        if self.error_detected:
            return

        # Valid request check
        stack.send(bytes([0x10, 0x03]))
        if not self.wait_response(stack, [0x50, 0x03]):
            #print(f"[{hex(self.udsid)}][{hex(self.sid)}] no response 10 03")
            self.failed = True

        if self.error_detected:
            self.ECUReset(stack)
            return self.failed

        self.ECUReset(stack)


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
