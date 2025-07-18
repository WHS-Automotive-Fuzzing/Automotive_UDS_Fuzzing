import can
import random
import isotp
import uds_isotp
import time

MAX_MUTATION_PER_LOGIC = 5


def bitflip1(data):
    #flip 1 random bit in data

    total_bits = len(data) * 8

    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)
    for i in range(how_many_flips):

        idx = random.randrange(total_bits)
        byte_index = idx // 8
        bit_index = idx % 8
        data[byte_index] ^= (1 << bit_index)

    return data

def bitflip2(data): 

    #flip  2 random consecutive bits in data
    total_bits = len(data) * 8

    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)
    for i in range(how_many_flips):
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

    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)
    for i in range(how_many_flips):
        idx = random.randrange(total_bits)

        for j in range(2):
        
            idx = (idx + j) % total_bits
            byte_index = idx // 8
            bit_index = idx % 8
            data[byte_index] ^= (1 << bit_index)

    return data


def byteflip8(data):
    #flip 1 byte in data
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
        idx = random.randrange(len(data))
        data[idx] ^= 0xFF
    
    return data



def byteflip16(data):
    #flip 2 random consecutive bytes in data
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
        idx = random.randrange(len(data))

        for j in range(2):
            idx = (idx + j) % len(data)
            data[idx] ^= 0xFF
        
    
    return data


def byteflip32(data):
    #flip 4 random consecutive bytes in data
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
        idx = random.randrange(len(data))

        for j in range(4):
            idx = (idx + j) % len(data)
            data[idx] ^= 0xFF
        
    
    return data


def arithmetic_inc8(data):
    #arithmetic increment 1 random byte in data
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
        idx = random.randrange(len(data))
        data[idx] = (data[idx] + 1) % 256

    return data

def arithmetic_inc16(data):
    #arithmetic increment 2 random consecutive bytes in data
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
        idx = random.randrange(len(data))

        for j in range(2):
            idx = (idx + j) % len(data)
            data[idx] = (data[idx] + 1) % 256

    return data
    
def arithmetic_inc32(data): 
    #arithmetic increment 4 random consecutive bytes in data
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
        idx = random.randrange(len(data))

        for j in range(4):
            idx = (idx + j) % len(data)
            data[idx] = (data[idx] + 1) % 256

    return data

def arithmetic_dec8(data):
    #arithmetic decrement 1 random byte in data
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
        idx = random.randrange(len(data))
        if data[idx] == 0:
            data[idx] = 255
        else:
            data[idx] = (data[idx] - 1)

    return data
    
def arithmetic_dec16(data):
    #arithmetic decrement 2 random consecutive bytes in data
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
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
    how_many_flips = random.randint(1, MAX_MUTATION_PER_LOGIC)

    for i in range(how_many_flips):
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
    how_many_set = random.randint(1, MAX_MUTATION_PER_LOGIC)
    for i in range(how_many_set):
        idx = random.randrange(len(data))
        data[idx] = random.randint(0, 255)

    return data


def deletebytes(data):
    # delete random consecutive bytes in data
    random_bytes = random.randint(1, MAX_MUTATION_PER_LOGIC)
    how_many_bytes = min(random_bytes, len(data))

    idx = random.randint(0, len(data) - how_many_bytes)  # 범위 보장

    del data[idx:idx + how_many_bytes] 
    return data 

        

def insertbytes(data):

    random_bytes = random.randint(1, MAX_MUTATION_PER_LOGIC)
    idx = random.randrange(len(data))
    for i in range(random_bytes):
        data.insert(idx , random.randint(0, 255))

    return data

def call_muatate(cnt, data):
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
        case 12: return randombytes(data)
        case 13: return deletebytes(data)
        case 14: return insertbytes(data)

        
        
def mutator(data):
    target_logic = random.randint(1, 0b1000000000000000)
    new_data=data.copy()
    cnt=0

    while target_logic>>cnt:
        if (target_logic>>cnt) & 0b1:
            new_data = call_muatate(cnt, new_data)
        cnt += 1
    
    return new_data
