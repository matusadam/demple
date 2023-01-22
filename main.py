import argparse
from time import perf_counter
from Demo import Demo
import os, psutil

# Example driver code

# Usage: py main.py <.dem file>

if __name__ == "__main__":
    aparser = argparse.ArgumentParser(description='Demo processing')
    aparser.add_argument('demofile')
    args = aparser.parse_args()

    process = psutil.Process(os.getpid())
    
    t1 = perf_counter()
    demo = Demo(args.demofile)
    t2 = perf_counter()
    print(f"Demo init in {t2-t1} seconds")

    t1 = perf_counter()
    framecount = demo.parse()
    t2 = perf_counter()
    print(f"Demo.parse fetched {framecount} frames in {t2-t1} seconds")

    mem = process.memory_info().rss
    print(f"Using {mem} bytes ({(mem / 2**20):.2f} MB) of memory")
