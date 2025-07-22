import isotp
import can
import time

WAIT_RESPONSE_TIME = 0.5  # seconds
RESET_SLEEP_TIME = 0.05

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

    def error_handler(self, e):
        if isinstance(e, isotp.errors.FlowControlTimeoutError):
            print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Flow Control Error: ", e)
            self.error_detected = True
        else:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Error: ", e)

    def CheckUDSMessage(self):
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.udsid, rxid=Response_ID[self.udsid])
        params = {"tx_padding": 0xFF}
        stack = isotp.CanStack(bus=self.bus, address=addr, params=params, error_handler=self.error_handler)

        print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Sending UDS Message: {self.data}")

        if self.diagnosticmodefail or self.error_detected:
            self.ECUReset(stack)  # ← 반드시 Reset
            return self.failed

        self.FailDetection(stack)

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
            print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 3E 00")
            self.diagnosticmodefail = True
            return

        retry = 0
        while retry < 3:
            stack.send(bytes([0x10, 0x03]))
            if self.wait_response(stack, [0x50, 0x03]):
                break
            retry += 1

        if retry == 3:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 10 03")
            self.diagnosticmodefail = True
            return

    def FailDetection(self, stack):
        send_data = [self.sid] + self.data
        stack.send(bytes(send_data))

        s_time = time.time()
        while time.time() - s_time < WAIT_RESPONSE_TIME:
            stack.process()
            if stack.available():
                _ = stack.recv()
                break
            time.sleep(0.01)

        if self.error_detected:
            return

        # Valid request check
        stack.send(bytes([0x10, 0x01]))
        if not self.wait_response(stack, [0x50, 0x01]):
            self.failed = True

    def wait_response(self, stack, expected_data, timeout=WAIT_RESPONSE_TIME):
        start_time = time.time()
        while time.time() - start_time < timeout:
            stack.process()
            if stack.available():
                response = stack.recv()
                if response[:len(expected_data)] == bytes(expected_data):
                    return True
            time.sleep(0.01)
        return False

    def ECUReset(self, stack):
        retry = 0
        while retry < 3:
            stack.send(bytes([0x11, 0x02]))
            if self.wait_response(stack, [0x51, 0x02]):
                time.sleep(RESET_SLEEP_TIME)
                break
            retry += 1
        if retry == 3:
            print(f"[{hex(self.udsid)}][{hex(self.sid)}]: no response 11 02")
