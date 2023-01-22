import os, sys
import struct
import json
from collections import namedtuple

class Demo():
    def __init__(self, filename):
        self.filename = filename
        try:
            self.file_stats = os.stat(filename)
        except IOError:
            print(f'File "{filename}" not found')
            sys.exit()
        self.filesize = self.file_stats.st_size
        self.f = open(filename, 'rb')
        self.structs = json.loads(open("structs.json").read())
        self.header = self.get_header()
        self.directory = self.get_directory()
           
    def __unpack(self, tuple_name, field_names, format, buffer) -> namedtuple:
        try:
            s = struct.unpack(format, buffer)
        except struct.error as e:
            print("[!] Not valid HLDEMO file, exiting")
            sys.exit()
        else:
            t = namedtuple(tuple_name, field_names)
            t = t._make(s)
            return t

    def __partial_unpack(self, tuple_name, buffer, framestruct) -> namedtuple:
        fields = self.fields
        ret = namedtuple(tuple_name, fields)
        ready = []
        for field in fields:
            t = framestruct[field]['t']
            offset = framestruct[field]['offset']
            size = framestruct[field]['size']
            ready.append(struct.unpack("="+t, buffer[offset:offset+size])[0])
        ret = ret._make(ready)
        return ret

    def parse(self, fields: list) -> int:
        self.frames = self.get_frames(fields)
        return len(self.frames)

    def get_header(self) -> namedtuple:
        HEADER_SIZE = 544
        SIGNATURE_SIZE = 8
        MAPNAME_SIZE = 260
        GAMEDIR_SIZE = 260
        self.f.seek(0)
        header = self.__unpack(
            'header',
            'magic demo_protocol net_protocol mapname gamedir mapcrc dir_offset',
            f'{SIGNATURE_SIZE}sii{MAPNAME_SIZE}s{GAMEDIR_SIZE}sii',
            self.f.read(HEADER_SIZE)) 
        if header.magic != b'HLDEMO\x00\x00':
            print("[!] Not valid HLDEMO file (magic string not found), exiting")
            sys.exit()
        return header

    def get_directory(self) -> list[namedtuple]:
        MIN_DIR_ENTRY_COUNT = 1
        MAX_DIR_ENTRY_COUNT = 1024
        DIR_ENTRY_SIZE = 92
        DIR_ENTRY_DESCRIPTION_SIZE = 64
        self.f.seek(self.header.dir_offset)
        entry_count = struct.unpack('i', self.f.read(4))[0]
        if not (MIN_DIR_ENTRY_COUNT <= entry_count <= MAX_DIR_ENTRY_COUNT):
            print('[!] Not valid HLDEMO file (incorrect dir entry count), exiting')
            sys.exit()
        entries = list()
        for _ in range(entry_count):
            entry = self.__unpack(
                'dir_entry',
                'type description flags track track_time frame_count offset size',
                f'i{DIR_ENTRY_DESCRIPTION_SIZE}siifiii',
                self.f.read(DIR_ENTRY_SIZE))
            entries.append(entry)
        return entries

    def get_frames(self, fields: list) -> list[tuple]:
        # Find the Playback (type=1) dir entry and read the frames. The other entry
        # is called LOADING (type=0), which normally doesn't contain any frames.
        playback_entry = None
        for e in self.directory:
            if e.type == 1:
                playback_entry = e
        if not playback_entry:
            print('[!] No Playback dir entry (not in-eye demo or corrupted), exiting')
            sys.exit()

        self.f.seek(playback_entry.offset)
        self.raw_playback = self.f.read(playback_entry.size)
        self.ptr = 0
        self.fields = fields

        frames = list()
        while True:
            subframe = self.get_frame()
            if subframe:
                if type(subframe).__name__ == "NextSectionFrame":
                    # NextSection frame is the last frame in Playback
                    break
                frames.append(subframe)
        return frames

    def get_frame(self) -> namedtuple:
        BASE_FRAME_LENGTH = 9
        p = self.ptr
        frame_type = struct.unpack("B", self.raw_playback[p:p+1])[0]
        
        match frame_type:
            case 1:          
                NETMSG_FRAME_LENGTH = BASE_FRAME_LENGTH + 468
                MSGLEN_OFFSET = NETMSG_FRAME_LENGTH - 4
                FRAME_NAME = 'NetMsgFrame'

                netmsgframe_struct = self.structs[FRAME_NAME]

                # Need to read msg length before unpacking
                msg_len = struct.unpack("i", self.raw_playback[p + MSGLEN_OFFSET: p + MSGLEN_OFFSET + 4])[0]
                netmsgframe_struct['msg']['t'] = f"{msg_len}s"
                netmsgframe_struct['msg']['size'] = msg_len

                if self.fields:
                    frame = self.__partial_unpack(
                        FRAME_NAME,
                        self.raw_playback[p: p + NETMSG_FRAME_LENGTH + msg_len],
                        netmsgframe_struct)
                else:
                    frame = self.__unpack(
                        FRAME_NAME,
                        " ".join(k for k in netmsgframe_struct),
                        "=" + "".join(v['t'] for v in netmsgframe_struct.values()),
                        self.raw_playback[p: p + NETMSG_FRAME_LENGTH + msg_len])

                self.ptr += NETMSG_FRAME_LENGTH + msg_len
                return frame

            # Rest of the frames are not used but need to be parsed/read
            case 2:
                START_FRAME_LENGTH = BASE_FRAME_LENGTH + 0
                self.ptr += START_FRAME_LENGTH
            case 3:
                CONSOLECOMMAND_FRAME_LENGTH = BASE_FRAME_LENGTH + 64
                self.ptr += CONSOLECOMMAND_FRAME_LENGTH
            case 4:
                CLIENTDATA_FRAME_LENGTH = BASE_FRAME_LENGTH + 32
                self.ptr += CLIENTDATA_FRAME_LENGTH
            case 5:
                NEXTSECTION_FRAME_LENGTH = BASE_FRAME_LENGTH + 0       
                frame = self.__unpack(
                    'NextSectionFrame',
                    "type time frame",
                    "=Bfi",
                    self.raw_playback[p: p + NEXTSECTION_FRAME_LENGTH])
                self.ptr += NEXTSECTION_FRAME_LENGTH
                return frame
            case 6:
                EVENT_FRAME_LENGTH = BASE_FRAME_LENGTH + 72
                self.ptr += EVENT_FRAME_LENGTH
            case 7:
                WEAPONANIM_FRAME_LENGTH = BASE_FRAME_LENGTH + 8
                self.ptr += WEAPONANIM_FRAME_LENGTH
            case 8:
                SOUND_FRAME_LENGTH = BASE_FRAME_LENGTH + 24
                SAMPLE_LEN_OFFSET = BASE_FRAME_LENGTH + 4
                # Need to read sample length before unpacking
                sample_len = struct.unpack("i", self.raw_playback[p + SAMPLE_LEN_OFFSET: p + SAMPLE_LEN_OFFSET + 4])[0]
                self.ptr += SOUND_FRAME_LENGTH + sample_len
            case 9:
                BUFFER_FRAME_LENGTH = BASE_FRAME_LENGTH + 4
                BUFFER_LEN_OFFSET = BASE_FRAME_LENGTH
                # Need to read buffer length before unpacking
                buffer_len = struct.unpack("i", self.raw_playback[p + BUFFER_LEN_OFFSET: p + BUFFER_LEN_OFFSET + 4])[0]
                self.ptr += BUFFER_FRAME_LENGTH + buffer_len
            case _:
                print(f"[!] Found unknown frame, exiting")
                sys.exit()