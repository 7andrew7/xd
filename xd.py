#!/usr/bin/env python3

'''Delta compression based on the xdelta algorithm:

http://citeseerx.ist.psu.edu/viewdoc/download;jsessionid=C6AB7A1B7782EF05DD82C6E52FFAF42C?doi=10.1.1.35.2828&rep=rep1&type=pdf
'''

import random
import zlib

BLOCK_SIZE = 16

def find_match(src, src_dict, target, target_index):
    # TODO: use a rolling hash
    hsh = zlib.adler32(target[target_index: target_index + BLOCK_SIZE])

    length = 0
    src_index = 0
    if hsh in src_dict:
        src_index = src_dict[hsh]
        bound = min(len(target) - target_index, len(src) - src_index)
        while length < bound and target[target_index + length] == src[src_index + length]:
            length += 1

    return src_index, length

def xdelta(src, target):
    
    # Initialize source blocks
    src_dict = dict()
    for start in range(0, len(src), BLOCK_SIZE):
        hsh = zlib.adler32(src[start:start + BLOCK_SIZE])
        src_dict[hsh] = start
    
    # Search for matching target regions
    i = 0
    instructions = []
    insert_buffer = bytes()
    while i < len(target):
        offset, length = find_match(src, src_dict, target, i)
        if length >= BLOCK_SIZE:
            if insert_buffer:
                instructions.append(('INSERT', insert_buffer, len(insert_buffer)))
                insert_buffer = bytes()
            instructions.append(('COPY', offset, length))
            i += length
        else:
            insert_buffer += target[i:i+1 ]
            i += 1

    if insert_buffer:
        instructions.append(('INSERT', insert_buffer, len(insert_buffer)))

    return instructions

def do_slice(src, deltas, offset, size):
    delta = deltas[0]
    position = 0
    ret = bytes()

#    indent = '   ' * (3 - len(deltas))
#    print("%sdo_slice(%d, %d)" % (indent, offset, size))

    # Fast forward to the first chunk with relevant data
    for index, instruction in enumerate(delta):
        chunk_length = instruction[2]
        if position + chunk_length > offset:
            chunk_offset = offset - position
            break
        position += chunk_length

    for op, chunk_arg, chunk_length in delta[index:]:
        chunk_read_size = min(chunk_length - chunk_offset, size - len(ret))

        if chunk_read_size <= 0:
            print(chunk_length, chunk_offset, size, len(ret))
            assert False
            
        if op == 'COPY':
            chunk_start = chunk_arg
            ret += do_slice(src, deltas[1:], chunk_start + chunk_offset, chunk_read_size)
        else:
            ret += chunk_arg[chunk_offset:chunk_offset + chunk_read_size]

        position += chunk_read_size
        if len(ret) == size:
            return ret
        assert len(ret) < size
        chunk_offset = 0
    else:
        print("Exhausted chunks?")
        assert False

def slice(src, _deltas, offset, size):
    # Rearrage deltas from newset to oldest.  Append a dummy entry with a global INSERT as the basis case
    deltas = list(reversed(_deltas))
    deltas.append([('INSERT', src, len(src))])
    return do_slice(src, deltas, offset, size)

if __name__ == '__main__':
    src  = 'It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the season of Darkness, it was the spring of hope, it was the winter of despair, we had everything before us, we had nothing before us, we were all going direct to Heaven, we were all going direct the other way - in short, the period was so far like the present period, that some of its noisiest authorities insisted on its being received, for good or for evil, in the superlative degree of comparison only.'

    deltas = []
    current_src = src

    for i in range(10):
        # Replace a word in the current_src text
        toks = current_src.split()
        index = random.randrange(len(toks))

        old = toks[index]
        toks[index] = random.choice(toks).upper()
        print("%s => %s" % (old, toks[index]))
        
        target = ' '.join(toks)
        print(target)
        
        deltas.append(xdelta(current_src.encode(), target.encode()))
        current_src = target

    length = len(current_src)
    y = slice(src.encode(), deltas, 0, length).decode()

    print("FORWARD: " + current_src)
    print("BACKWARDS: " + y)
    print(current_src == y)
    


