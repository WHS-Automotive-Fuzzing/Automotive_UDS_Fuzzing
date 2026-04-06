import can
import random
import isotp
from module.uds_isotp import *
import time

MAX_MUTATION_BYTE = 4
MAX_MUTATION_TIME = 2

def bitflip1(data):
    #flip 1 random bit in data
    total_bits = len(data) * 8

    idx = random.randrange(total_bits)
    byte_index = idx // 8
    bit_index = idx % 8
    data[byte_index] ^= (1 << bit_index)

    return data

def bitflip2(data): 

    #flip  2 random consecutive bits in data
    total_bits = len(data) * 8

    idx = random.randrange(total_bits)

    for j in range(2):
        idx = (idx + j) % total_bits
        byte_index = idx // 8
        bit_index = idx % 8
        data[byte_index] ^= (1 << bit_index)
    return data

def bitflip4(data):
    #flip 4 random consecutive bits in data
    total_bits = len(data) * 8

    idx = random.randrange(total_bits)
    for j in range(4):   
        idx = (idx + j) % total_bits
        byte_index = idx // 8
        bit_index = idx % 8
        data[byte_index] ^= (1 << bit_index)
    return data


def byteflip8(data):
    #flip 1 byte in data
    idx = random.randrange(len(data))
    data[idx] ^= 0xFF   
    return data



def byteflip16(data):
    #flip 2 random consecutive bytes in data
    idx = random.randrange(len(data))
    for j in range(2):
        idx = (idx + j) % len(data)
        data[idx] ^= 0xFF

    return data


def byteflip32(data):
    #flip 4 random consecutive bytes in data
    idx = random.randrange(len(data))
    for j in range(4):
        idx = (idx + j) % len(data)
        data[idx] ^= 0xFF
    
    return data


def arithmetic_inc8(data):
    #arithmetic increment 1 random byte in data
    idx = random.randrange(len(data))
    data[idx] = (data[idx] + 1) % 256

    return data

def arithmetic_inc16(data):
    #arithmetic increment 2 random consecutive bytes in data
    idx = random.randrange(len(data))
    for j in range(2):
        idx = (idx + j) % len(data)
        data[idx] = (data[idx] + 1) % 256

    return data
    
def arithmetic_inc32(data): 
    #arithmetic increment 4 random consecutive bytes in data
    idx = random.randrange(len(data))
    for j in range(4):
        idx = (idx + j) % len(data)
        data[idx] = (data[idx] + 1) % 256

    return data

def arithmetic_dec8(data):
    #arithmetic decrement 1 random byte in data
    idx = random.randrange(len(data))
    if data[idx] == 0:
        data[idx] = 255
    else:
        data[idx] = (data[idx] - 1)

    return data
    
def arithmetic_dec16(data):
    #arithmetic decrement 2 random consecutive bytes in data
    idx = random.randrange(len(data))
    for j in range(2):
        idx = (idx + j) % len(data)
        if data[idx] == 0:
            data[idx] = 255
        else:
            data[idx] = (data[idx] - 1)
    return data

        
def arithmetic_dec32(data):
    #arithmetic decrement 4 random consecutive bytes in data
    idx = random.randrange(len(data))
    for j in range(4):
        idx = (idx + j) % len(data)
        if data[idx] == 0:
            data[idx] = 255
        else:
            data[idx] = (data[idx] - 1)
    
    return data
    
def randombytes(data):
    # set random bytes to random value
    how_many_set = random.randint(1, MAX_MUTATION_BYTE)
    for i in range(how_many_set):
        idx = random.randrange(len(data))
        data[idx] = random.randint(0, 255)

    return data


def deletebytes(data):
    # delete random consecutive bytes in data
    n = len(data)
    if n <= 1:
        return data  # 0방지

    random_bytes = random.randint(1, MAX_MUTATION_BYTE)
    how_many_bytes = min(random_bytes, n - 1)

    idx = random.randint(0, n - how_many_bytes)
    del data[idx:idx + how_many_bytes]
    return data
 

        

def insertbytes(data):
    # Ensure the data is not empty
    if len(data) == 0:
        return data  # Return the data unchanged if it's empty
    
    random_bytes = random.randint(1, MAX_MUTATION_BYTE)
    idx = random.randrange(len(data))  # Only execute if data is not empty
    
    for i in range(random_bytes):
        data.insert(idx, random.randint(0, 255))  # Insert random bytes
    
    return data



def replace_zeros1(data):
    if not data:
        return data # Return unchanged if data is empty
    
    idx = random.randrange(len(data))
    data[idx] = 0x00
    
    return data



def replace_zeros2(data):
    if len(data) < 2:
        for i in range(len(data)):
            data[i] = 0x00
        return data  # If data has less than 2 bytes, return zeros of the same length    
        
    idx = random.randrange(len(data)-1)
    data[idx:idx+2] = 0x00, 0x00
    
    return data



def replace_zeros4(data):
    if len(data) < 4:
        for i in range(len(data)):
            data[i] = 0x00
        return data  # If data has less than 4 bytes, return zeros of the same length

    idx = random.randrange(len(data)-3)
    data[idx:idx+4] = 0x00, 0x00, 0x00, 0x00
 
    return data



def replace_ffs1(data):
    if len(data) < 1:
        return data  # Return unchanged if data is empty

    idx = random.randrange(len(data))
    data[idx] = 0xFF
    
    return data



def replace_ffs2(data):
    if len(data) < 2:
        for i in range(len(data)):
            data[i] = 0xFF
        return data  # If data has less than 2 bytes, return 0xFF of the same length
    
    idx = random.randrange(len(data)-1)
    data[idx:idx+2] = 0xFF, 0xFF
    
    return data



def replace_ffs4(data):
    if len(data) < 4:
        for i in range(len(data)):
            data[i] = 0xFF
        return data  # If data has less than 4 bytes, return 0xFF of the same length
    
    idx = random.randrange(len(data)-3)
    data[idx:idx+4] = 0xFF, 0xFF, 0xFF, 0xFF
    
    return data



def call_deterministic_muatate(cnt, data):
    match cnt:
        case 0: return bitflip1(data)
        case 1: return bitflip2(data)
        case 2: return bitflip4(data)
        case 3: return byteflip8(data)
        case 4: return byteflip16(data)
        case 5: return byteflip32(data)
        case 6: return arithmetic_inc8(data)
        case 7: return arithmetic_inc16(data)
        case 8: return arithmetic_inc32(data)
        case 9: return arithmetic_dec8(data)
        case 10: return arithmetic_dec16(data)
        case 11: return arithmetic_dec32(data)
        case 12: return replace_zeros1(data)
        case 13: return replace_ffs1(data)
       
        
        
def call_nondeterministic_mutate(cnt, data):
    match cnt:
        case 0: return bitflip1(data)
        case 1: return bitflip2(data)
        case 2: return bitflip4(data)
        case 3: return byteflip8(data)
        case 4: return byteflip16(data)
        case 5: return byteflip32(data)
        case 6: return arithmetic_inc8(data)
        case 7: return arithmetic_inc16(data)
        case 8: return arithmetic_inc32(data)
        case 9: return arithmetic_dec8(data)
        case 10: return arithmetic_dec16(data)
        case 11: return arithmetic_dec32(data)
        case 12: return replace_zeros1(data)
        case 13: return replace_ffs1(data)
        case 14: return randombytes(data)
        case 15: return insertbytes(data)
        case 16: return deletebytes(data)
            

        
        
def deterministic_mutator(msg):
    new_data_list = []

    for i in range(14):
        new_data=msg.data.copy()
        new_data = call_deterministic_muatate(i, new_data)
        new_data_list.append(new_data)

    return new_data_list



def nondeterministic_mutator(msg):
    new_data_list = []
    if len(msg.data) <=1:
        for i in range(MAX_MUTATION_TIME):
            target_logic = random.randint(1, 0b1<<16)
            new_data=msg.data.copy()
            cnt=0

            while target_logic>>cnt:            
                if (target_logic>>cnt) & 0b1:
                    new_data = call_nondeterministic_mutate(cnt, new_data)
                cnt += 1
            new_data_list.append(new_data)

    else: 
        for i in range(MAX_MUTATION_TIME):
            target_logic = random.randint(1, 0b1<<17)
            new_data=msg.data.copy()
            cnt=0

            while target_logic>>cnt:            
                if (target_logic>>cnt) & 0b1:
                    new_data = call_nondeterministic_mutate(cnt, new_data)
                cnt += 1
            new_data_list.append(new_data)

    return new_data_list
