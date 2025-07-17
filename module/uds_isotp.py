import isotp
import can
import time


WAIT_RESPONSE_TIME = 0.05 # unit: Sec 

# Dict for CAN IDs and their corresponding IDs
Response_ID = {
    0x73E: 0x7A8, # UDS LOCK
    0x70E: 0x778, # UDS WIPER
    0x74C: 0x7B6, # UDS DRIVER SEAT // 응답이 0x7B6인 것 같은데!? 바꿔도 됨??? 바꿨음!! 원래 78D로 되어있었음 ty
    0x723: 0x78D, # UDS TRUNK OPEN
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
        '''variables'''
        # start_time = None # unit: Sec
        #end_time = None
        failed = False
    
    # Function: Cheeck Send&Recv UDS Message
    # sends a UDS Message and checks a response
    def CheckUDSMessage(self): 
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.udsid, rxid=Response_ID[self.udsid])
        stack = isotp.CanStack(bus = self.bus, address = addr)

        while not self.diagnosticmodefail:
            self.StartDiagnosticMode(stack)
        
        
        self.FailDetection(stack) # if failed, it will set self.failed to True
        self.ECUReset(stack) # reset ECU after sending TESTcase
        return self.failed
        
    
    def StartDiagnosticMode(self, stack):
        # 0x3E 0x00
        retry = 0
        while retry < 3:
            stack.send(bytes([0x3E, 0x00]))
            if self.wait_response(stack, [0x7E, 0x00]):
                break
            retry += 1

        if retry==3:
            print("no response 3E 00")
            self.diagnosticmodefail = True

        # 0x10 0x03 
        retry = 0
        while retry < 3:
            stack.send(bytes([0x10, 0x03]))
            if self.wait_response(stack, [0x50, 0x03]):
                break
            retry += 1
        
        if retry == 3:
            print("no response 10 03")
            self.diagnosticmodefail = True


        
    
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
        
        s_time = time.time()
        while time.time() - s_time < WAIT_RESPONSE_TIME:
            stack.process()
            if stack.available():
                response = stack.recv() 

        # send valid request 0x22..
        send_data = [0x22, 0xF1, 0x90] # VIN Request(valid request)
        stack.send(bytes(send_data))
        if not self.wait_response(stack, [0x62, 0xF1, 0x90]): # VIN Response
            self.failed = True
        

        '''
        하나 센드센드
        대기
        응답받기
        if 어쩃든 응답이 옴:
            valid request를 보내
            대기
            if 요상한 응답:
                self.failed = True
            return self.fai함수 종료
        else 시간초과(응답없음):
            valid request를 보내
            대기
            if 요상한 응답:
                self.failed = True
        return self.failed
        '''
        
        
        '''
        if 응답 :
            NRC코드 확인
        else : 
        
        valid req
        
        self.valid = wait response (expected)

        
        '''
        

    def wait_response(self, stack, expected_data, timeout=WAIT_RESPONSE_TIME):
        """
        stack: isotp.CanStack 객체
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
                    return True
            time.sleep(0.01)
        return False

    def ECUReset(self, stack):
        retry = 0
        while retry < 3:
            stack.send(bytes([0x11, 0x02]))
            if self.wait_response(stack, [0x51, 0x02]):
                break
            retry += 1
            if retry == 3:
                print("no response 11 02")
