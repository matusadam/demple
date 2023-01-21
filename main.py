import argparse

from Demo import Demo

# Example driver code

# Usage: py main.py <.dem file>

if __name__ == "__main__":
    aparser = argparse.ArgumentParser(description='Demo processing')
    aparser.add_argument('demofile')
    args = aparser.parse_args()
    demo = Demo(args.demofile)
    frames = demo.get_frames(
        {"time","vieworg_x","vieworg_y","vieworg_z"})
    
    for f in frames:
        print(f"Time: {f['time']}, player origin: {f['vieworg_x']} {f['vieworg_y']} {f['vieworg_z']}")
    