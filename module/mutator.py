import can
import random
import isotp
import uds_isotp
import time

MAX_MUTATION_PER_LOGIC = 5


def bitflip1(data):
    
    flipped_data = data.copy()

    for i in range(len(flipped_data)):
        idx = random.randrange(len(flipped_data))
        flipped_data[idx] ^= 1 - flipped_data[idx]
def bitflip2(data):

def bitflip4(data):

def byteflip8(data):

def byteflip16(data):

def byteflip32(data):

def arithmetic_inc8(data):

def arithmetic_inc16(data):

def arithmetic_inc32(data): 

def arithmetic_dec8(data):

def arithmetic_dec16(data):
    
def arithmetic_dec32(data):
    
def randombytes(data):

def deletebytes(data):

def insertbytes(data):
  

def call_muatate(cnt):

def mutator(data):
    target_logic = random.randint(1, 0b1000000000000000)
    
    cnt=0
    while target_logic>>cnt:
        if target_logic>>cnt &0b1:
            call_muatate(cnt)
        cnt += 1 
    return mutatedata







