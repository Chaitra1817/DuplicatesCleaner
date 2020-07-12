#!/usr/bin/env python
import os
import sys
import hashlib
from collections import defaultdict
import time


def chunk_reader(fobj, chunk_size=1024):
    """ Generator that reads a file in chunks of bytes """
    while True:
        chunk = fobj.read(chunk_size)
        if not chunk:
            return
        yield chunk


def get_hash(filename, first_chunk_only=False, hash_algo=hashlib.sha1):
    hashobj = hash_algo()
    with open(filename, "rb") as f:
        if first_chunk_only:
            hashobj.update(f.read(1024))
        else:
            for chunk in chunk_reader(f):
                hashobj.update(chunk)
    return hashobj.digest()


def check_for_duplicates(paths, statement):

    z=0
    start_time = time.time()
    removed = 0
    skipped = 0

    files_by_size = defaultdict(list)
    files_by_small_hash = defaultdict(list)
    files_by_full_hash = dict()

    for path in paths:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    # if the target is a symlink (soft one), this will
                    # dereference it - change the value to the actual target file
                    full_path = os.path.realpath(full_path)
                    file_size = os.path.getsize(full_path)
                except OSError:
                    # not accessible (permissions, etc) - pass on
                    continue
                files_by_size[file_size].append(full_path)
                print("Check " + str(z))
                z+=1

    # For all files with the same file size, get their hash on the first 1024 bytes
    for files in files_by_size.values():
        if len(files) < 2:
            continue  # this file size is unique, no need to spend cpu cycles on it

        for filename in files:
            try:
                small_hash = get_hash(filename, first_chunk_only=True)
            except OSError:
                # the file access might've changed till the exec point got here
                continue
            files_by_small_hash[small_hash].append(filename)
            print("Check " + str(z))
            z+=1

    
    # For all files with the hash on the first 1024 bytes, get their hash on the full
    # file - collisions will be duplicates
    for files in files_by_small_hash.values():
        if len(files) < 2:
            # the hash of the first 1k bytes is unique -> skip this file
            continue

        for filename in files:
            try:
                full_hash = get_hash(filename, first_chunk_only=False)
            except OSError:
                # the file access might've changed till the exec point got here
                continue

            if full_hash in files_by_full_hash:
                duplicate = files_by_full_hash[full_hash]
                print("Duplicate found:\n - %s\n - %s\n" % (filename, duplicate))
                filename = filename.replace('\\\\','\\')
                try:
                    os.remove(filename)
                except PermissionError:
                    skipped+=1
                    print("Check "+ str(z) +"skipped")
                removed +=1
            else:
                files_by_full_hash[full_hash] = filename
            print("Check " + str(z))
            z+=1

    statement.set("✅ Finished cleaning - "+ str(removed-skipped) + " files removed in "+ str(round(time.time() - start_time, 4)) + " seconds & "+str(skipped)+" files with permission error")