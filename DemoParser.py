import argparse
import json

from Demo import Demo

if __name__ == "__main__":
    aparser = argparse.ArgumentParser(description='Demo processing')
    aparser.add_argument('demofile')
    args = aparser.parse_args()
    demo = Demo(args.demofile, full=True)
    print (demo.directory)
    tojson = {
        "time":list(),
        "frame":list(),
        "origin_x":list(),
        "origin_y":list(),
        "origin_z":list(),
        "viewangle_x":list(),
        "viewangle_y":list(),
        "viewangle_z":list(),
    }
    # print( "\n".join(str(x) for x in demo.playback_entry.frameTimes()) )
    for frame in demo.playback_entry.frames[:]:
        if frame.type == 4:
            tojson["time"].append(frame.time[0])
            tojson["frame"].append(frame.frame)
            tojson["origin_x"].append(frame.origin[0][0])
            tojson["origin_y"].append(frame.origin[1][0])
            tojson["origin_z"].append(frame.origin[2][0])
            tojson["viewangle_x"].append(frame.viewangles[0][0])
            tojson["viewangle_y"].append(frame.viewangles[1][0])
            tojson["viewangle_z"].append(frame.viewangles[2][0])

    with open(args.demofile+'.json', 'w') as f:
        json.dump(tojson, f, sort_keys=True)