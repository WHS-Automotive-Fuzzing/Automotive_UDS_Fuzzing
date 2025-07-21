import isotp
import can
import time


WAIT_RESPONSE_TIME = 0.5 # unit: Sec 
RESET_SLEEP_TIME = 0.01
# Dict for CAN IDs and their corresponding IDs
Response_ID = {
    0x73E: 0x7A8, # UDS LOCK
    0x70E: 0x778, # UDS WIPER
    0x74C: 0x7B6, # UDS DRIVER SEAT 
    0x723: 0x78D, # UDS TRUNK OPEN,
    0x74B: 0x7B5,
    0x74A: 0x7B4,
    0x17FC0084: 0x17FE0084, #UDS SUNROOF
}

class UDSMessage:
    

    #init function to initialize the UDSMessage object
    def __init__(self, udsid, sid, data : list[int], depth, bus):
        self.udsid = udsid
        self.sid = sid
        self.data = data
        self.depth = depth
        self.bus = bus
        self.diagnosticmodefail = False
        
        self.error_detected = False
        self.failed = False
    
    def error_handler(e):
        if isinstance(e, isotp.errors.FlowControlTimeoutError):
            print(f"[{self.udsid}][{self.sid}] [Depth: {self.depth}] Flow Control Error: ", e)
            self.error_detected = True
        

    # Function: Cheeck Send&Recv UDS Message
    # sends a UDS Message and checks a response
    def CheckUDSMessage(self):
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.udsid, rxid=Response_ID[self.udsid])
        params = {
            "tx_padding": 0xFF
        }
        stack = isotp.CanStack(bus = self.bus, address = addr, params = params, error_handler=error_handler)
        
        print(f"[{hex(self.udsid)}][{hex(self.sid)}] [Depth: {self.depth}] Sending UDS Message: [{self.data}]")

        self.StartDiagnosticMode(stack)
        
        if self.diagnosticmodefail:
            print(f"diagnostic fail: [{hex(self.udsid)}][{hex(self.sid)}] [{self.data}] [Depth: {self.depth}]")
            self.ECUReset(stack)
            return False
        
        
        self.FailDetection(stack) # if failed, it will set self.failed to True
        self.ECUReset(stack) # reset ECU after sending TESTcase
        return self.failed
        
        
        
    # Function: initial UDS message to start diagnostic mode
    def StartDiagnosticMode(self, stack):
        # 0x3E 0x00
        retry = 0
        while retry < 3:
            stack.send(bytes([0x3E, 0x00]))
            stack.send(bytes([0x3E, 0x00]))
            if self.wait_response(stack, [0x7E, 0x00]):
                break
            retry += 1

        if retry==3:
            print(f"["+hex(self.udsid)+f"]["+hex(self.sid)+f"]: no response 3E 00")
            self.diagnosticmodefail = True
            return 

        # 0x10 0x03 
        retry = 0
        while retry < 3:
            stack.send(bytes([0x10, 0x03]))
            if self.wait_response(stack, [0x50, 0x03]):
                break
            retry += 1
        
        if retry == 3:
            print(f"["+hex(self.udsid)+f"]["+hex(self.sid)+f"]: no response 10 03")
            self.diagnosticmodefail = True
            return
 

        
    
    def FailDetection(self, stack):
        '''
        FailDetection based on time
        1. Send UDS Message 
        2. wait for response 
        3. if no response within XXms, then send Valid Request
        4. if no response or invalid response, then Check it as failed
        '''

        # send Testcase
        send_data = [self.sid] + self.data
        
        stack.send(bytes(send_data))

        # wait for response
        s_time = time.time()
        while time.time() - s_time < WAIT_RESPONSE_TIME:
            stack.process()
            if stack.available():
                response = stack.recv()  

        # send valid request 0x10..
        send_data = [0x10, 0x01] # valid request
        stack.send(bytes(send_data))
        if not self.wait_response(stack, [0x50, 0x01]): # Vaild Response 
            self.failed = True
        
        
    # Function: Wait for response for WAIT_RESPONSE_TIME seconds
    def wait_response(self, stack, expected_data, timeout=WAIT_RESPONSE_TIME):
        """
        stack: isotp.CanStack
        expected_data: list of expected data bytes
        timeout: unit :Sec (default = 2)
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            stack.process()
            if stack.available():
                response = stack.recv()
                # check response data
                if response[:len(expected_data)] == bytes(expected_data):
                    #print(list(response))
                    return True
            time.sleep(0.01)
        return False

    # Function: Reset the target ECU
    def ECUReset(self, stack):
        retry = 0
        while retry < 3:
            stack.send(bytes([0x11, 0x02]))
            if self.wait_response(stack, [0x51, 0x02]):
                time.sleep(RESET_SLEEP_TIME)
                break
            retry += 1
            if retry == 3:
                print(f"["+hex(self.udsid)+f"]["+hex(self.sid)+f"]: no response 11 02")