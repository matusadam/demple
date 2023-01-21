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
        self.header = self.get_header()
        self.directory = self.get_directory()
        self.netmsgframe_struct = json.loads(open("netmsgframe_struct.json").read())
        
    def __unpack(self, tuple_name, field_names, format, buffer) -> namedtuple:
        try:
            s = struct.unpack(format, buffer)
        except struct.error:
            print("[!] Not valid HLDEMO file, exiting")
            sys.exit()
        else:
            t = namedtuple(tuple_name, field_names)
            t = t._make(s)
            return t

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

    def get_frames(self, values: set[str]) -> list[namedtuple]:
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
        frames = list()
        for _ in range(playback_entry.frame_count):
            # Parse frame and get only what is requested by user
            subframe = self.get_frame(values)
            if subframe:
                frames.append(subframe)
        return frames

    def get_frame(self, values: set[str]) -> namedtuple:
        frame_type = struct.unpack("B",self.f.read(1))[0]
        BASE_FRAME_LENGTH = 8

        match frame_type:
            case 1:
                
                NETMSG_FRAME_LENGTH = BASE_FRAME_LENGTH + 468
                MSGLEN_OFFSET = NETMSG_FRAME_LENGTH - 4
                # Need to read msg length before unpacking
                ptr = self.f.tell()
                self.f.seek(ptr + MSGLEN_OFFSET)
                msg_len = struct.unpack("i",self.f.read(4))[0]
                self.f.seek(ptr)

                self.netmsgframe_struct.append(("msg",f"{msg_len}s"))

                frame = self.__unpack(
                    'NetMsgFrame',
                    " ".join(x[0] for x in self.netmsgframe_struct),
                    "".join(x[1] for x in self.netmsgframe_struct),
                    self.f.read(NETMSG_FRAME_LENGTH + msg_len))

                self.netmsgframe_struct.pop()
                # Get subset from given values
                frame = {k: getattr(frame, k) for k in values}  
                return frame

            # Rest of the frames are not used but need to be parsed/read
            case 2:
                START_FRAME_LENGTH = BASE_FRAME_LENGTH + 0
                self.f.read(START_FRAME_LENGTH)
            case 3:
                CONSOLECOMMAND_FRAME_LENGTH = BASE_FRAME_LENGTH + 64
                self.f.read(CONSOLECOMMAND_FRAME_LENGTH)
            case 4:
                CLIENTDATA_FRAME_LENGTH = BASE_FRAME_LENGTH + 32
                self.f.read(CLIENTDATA_FRAME_LENGTH)
            case 5:
                NEXTSECTION_FRAME_LENGTH = BASE_FRAME_LENGTH + 0
                self.f.read(NEXTSECTION_FRAME_LENGTH)
            case 6:
                EVENT_FRAME_LENGTH = BASE_FRAME_LENGTH + 72
                self.f.read(EVENT_FRAME_LENGTH)
            case 7:
                WEAPONANIM_FRAME_LENGTH = BASE_FRAME_LENGTH + 8
                self.f.read(WEAPONANIM_FRAME_LENGTH)
            case 8:
                SOUND_FRAME_LENGTH = BASE_FRAME_LENGTH + 24
                SAMPLE_LEN_OFFSET = 12
                # Need to read sample length before unpacking
                ptr = self.f.tell()
                self.f.seek(ptr + SAMPLE_LEN_OFFSET)
                sample_len = struct.unpack("i",self.f.read(4))[0]
                self.f.seek(ptr)
                self.f.read(SOUND_FRAME_LENGTH + sample_len)
            case 9:
                BUFFER_FRAME_LENGTH = BASE_FRAME_LENGTH + 4
                BUFFER_LEN_OFFSET = 8
                # Need to read buffer length before unpacking
                ptr = self.f.tell()
                self.f.seek(ptr + BUFFER_LEN_OFFSET)
                buffer_len = struct.unpack("i",self.f.read(4))[0]
                self.f.seek(ptr)
                self.f.read(BUFFER_FRAME_LENGTH + buffer_len)
            case _:
                print(f"[!] Found unknown frame, exiting")
                sys.exit()