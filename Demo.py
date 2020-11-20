import os, sys
import struct

class Demo():
    def __init__(self, filename, full=True):
        self._filename = filename
        self._full = full
        try:
            self._file_stats = os.stat(filename)
            self._demosize = self._file_stats.st_size
        except IOError:
            print('File "{}" not found'.format(filename))
            sys.exit()

        with open(filename, 'rb') as demo:
            self._header = DemoHeader(demo)
            self._directory = DemoDirectory(demo, self._header)
            if full:
                self.__read_all(demo)

    def __read_all(self, demo):

        if self._header.demoProtocol != 5:
            print('Only demo protocol 5 is supported. No frames were loaded.')
            return

        for entry in self._directory.directoryEntries:
            self.__read_entry(demo, entry)
            
    def __read_entry(self, demo, entry):
        MIN_FRAME_SIZE = 12
        DemoFrameType = {
            2 : DemoStartFrame,
            3 : ConsoleCommandFrame,
            4 : ClientDataFrame,
            5 : NextSectionFrame,
            6 : EventFrame,
            7 : WeaponAnimFrame,
            8 : SoundFrame,
            9 : DemoBufferFrame
        }
        demo.seek(entry.offset)
        run = True
        frame_counter = 0
        while run:
            frame_counter += 1
            if (self._demosize - demo.tell()) < MIN_FRAME_SIZE:
                print('min frame size triggered', frame_counter)
                break
            frame_type = int.from_bytes(demo.read(1), byteorder='little')
            frame_class = DemoFrameType.get(frame_type, NetMsgFrame)
            frame = frame_class(demo, frame_type)
            entry.frames.append( frame )
            if frame_class == NextSectionFrame:
                run = False

    @property
    def stats(self):
        s = "Name: {}\nSize: {} bytes\n"
        return s.format(
            self._filename, 
            self._demosize, 
            )

    @property
    def header(self):
        s = "Signature: {}\nDemo protocol: {}\nNetwork protocol: {}\nMap name: {}\nGame Dir: {}\nMap CRC: {}\nDirectory Offset: {}\n"
        return s.format(
            self._header.signature, 
            self._header.demoProtocol, 
            self._header.netProtocol,
            self._header.mapName,
            self._header.gameDir,
            self._header.mapCRC,
            self._header.directoryOffset
        )

    @property
    def directory(self):
        s = "Directory entry count: {}\n{}"
        s_entries = "Entries:\n"
        for entry in self._directory.directoryEntries:
            s_entry = '  Type: {}\n  Description: {}\n  Frame count: {}\n  Offset: {}\n  File length: {}\n{}\n'.format(
                entry.type,
                entry.description,
                entry.frameCount,
                entry.offset,
                entry.fileLength,
                80*'-'
            )
            s_entries += s_entry
        return s.format(
            self._directory.dirEntryCount,
            s_entries
        )

    @property
    def playback_entry(self):
        # search directory for playback entry
        for entry in self._directory.directoryEntries:
            if entry.type == 1:
                return entry




class DemoHeader():
    def __init__(self, demo):

        HEADER_SIZE = 544
        HEADER_SIGNATURE_CHECK_SIZE = 6
        HEADER_SIGNATURE_SIZE = 8
        HEADER_MAPNAME_SIZE = 260
        HEADER_GAMEDIR_SIZE = 260
        demo.seek(0) # start of demo
        self.signature = demo.read(6).decode('UTF-8').rstrip('\0')
        if self.signature != 'HLDEMO':
            print('Yo thats not HLDEMO')
            sys.exit()
        demo.seek(HEADER_SIGNATURE_SIZE) # start of demo + signature offset
        self.demoProtocol = int.from_bytes(demo.read(4), byteorder='little')
        self.netProtocol = int.from_bytes(demo.read(4), byteorder='little')
        self.mapName = demo.read(HEADER_MAPNAME_SIZE).decode('UTF-8').rstrip('\0')
        self.gameDir = demo.read(HEADER_GAMEDIR_SIZE).decode('UTF-8').rstrip('\0')
        self.mapCRC = int.from_bytes(demo.read(4), byteorder='little')
        self.directoryOffset = int.from_bytes(demo.read(4), byteorder='little')


class DemoDirectory():
    def __init__(self, demo, header):

        MIN_DIR_ENTRY_COUNT = 1
        MAX_DIR_ENTRY_COUNT = 1024
        demo.seek(header.directoryOffset)
        self.dirEntryCount = int.from_bytes(demo.read(4), byteorder='little')
        if (self.dirEntryCount < MIN_DIR_ENTRY_COUNT) or (self.dirEntryCount > MAX_DIR_ENTRY_COUNT):
            print('Incorrent directory entry count')
            return
        self.directoryEntries = list()
        for i in range(self.dirEntryCount):
            self.directoryEntries.append( DirectoryEntry(demo) )


class DirectoryEntry():
    def __init__(self, demo):

        DIR_ENTRY_SIZE = 92
        DIR_ENTRY_DESCRIPTION_SIZE = 64
        self.type = int.from_bytes(demo.read(4), byteorder='little')
        self.description = demo.read(DIR_ENTRY_DESCRIPTION_SIZE).decode('UTF-8').rstrip('\0')
        self.flags = int.from_bytes(demo.read(4), byteorder='little')
        self.CDTrack = int.from_bytes(demo.read(4), byteorder='little')
        self.trackTime = struct.unpack('f', demo.read(4))
        self.frameCount = int.from_bytes(demo.read(4), byteorder='little')
        self.offset = int.from_bytes(demo.read(4), byteorder='little')
        self.fileLength = int.from_bytes(demo.read(4), byteorder='little')
        self.frames = list()

    def frameTimes(self):
        return [frame.time for frame in self.frames]

    def frameTypes(self):
        return [frame.type for frame in self.frames]

    def frameTypesAndTimes(self):
        return [(frame.type, frame.time) for frame in self.frames]

    def frameVerbose(self):
        return [frame.getInfo() for frame in self.frames]

    def consoleCommands(self):
        return [frame for frame in self.frames if frame.type == 3]



class Frame():
    def __init__(self, demo, type):
        self.type = type
        self.time = struct.unpack('f', demo.read(4))
        self.frame = int.from_bytes(demo.read(4), byteorder='little')

    def getBaseInfo(self):
        return (self.type, self.time, self.frame)


class DemoStartFrame(Frame):
    def __init__(self, demo, type):
        super().__init__(demo, type)

    def getInfo(self):
        return ( self.getBaseInfo() )


class ConsoleCommandFrame(Frame):
    def __init__(self, demo, type):
        FRAME_CONSOLE_COMMAND_SIZE = 64
        super().__init__(demo, type)
        self.command = demo.read(FRAME_CONSOLE_COMMAND_SIZE).decode("utf-8") 

    def getInfo(self):
        return ( self.getBaseInfo(), self.command )


class ClientDataFrame(Frame):
    def __init__(self, demo, type):       
        super().__init__(demo, type)
        self.origin = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.viewangles = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.weaponBits = int.from_bytes(demo.read(4), byteorder='little')
        self.fov = struct.unpack('f', demo.read(4))

    def getInfo(self):
        return ( self.getBaseInfo() )


class NextSectionFrame(Frame):
    def __init__(self, demo, type):
        super().__init__(demo, type)

    def getInfo(self):
        return ( self.getBaseInfo() )


class EventFrame(Frame):
    def __init__(self, demo, type):
        super().__init__(demo, type)
        self.flags = int.from_bytes(demo.read(4), byteorder='little')
        self.entity_index = int.from_bytes(demo.read(4), byteorder='little')
        self.origin = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.angles = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.velocity = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.ducking = int.from_bytes(demo.read(4), byteorder='little')
        self.fparam1 = struct.unpack('f', demo.read(4))
        self.fparam2 = struct.unpack('f', demo.read(4))
        self.iparam1 = int.from_bytes(demo.read(4), byteorder='little')
        self.iparam2 = int.from_bytes(demo.read(4), byteorder='little')
        self.bparam1 = int.from_bytes(demo.read(4), byteorder='little')
        self.bparam2 = int.from_bytes(demo.read(4), byteorder='little')

    def getInfo(self):
        return ( self.getBaseInfo() )

class WeaponAnimFrame(Frame):
    def __init__(self, demo, type):
        super().__init__(demo, type)
        self.anim = int.from_bytes(demo.read(4), byteorder='little')
        self.body = int.from_bytes(demo.read(4), byteorder='little')

    def getInfo(self):
        return ( self.getBaseInfo() )


class SoundFrame(Frame):
    def __init__(self, demo, type):
        super().__init__(demo, type)
        self.channel = int.from_bytes(demo.read(4), byteorder='little')
        self.length = int.from_bytes(demo.read(4), byteorder='little')
        self.sample = demo.read(self.length)
        self.attenuation = struct.unpack('f', demo.read(4))
        self.volume = struct.unpack('f', demo.read(4))
        self.flags = int.from_bytes(demo.read(4), byteorder='little')
        self.pitch = int.from_bytes(demo.read(4), byteorder='little')

    def getInfo(self):
        return ( self.getBaseInfo() )

class DemoBufferFrame(Frame):
    def __init__(self, demo, type):
        super().__init__(demo, type)
        self.length = int.from_bytes(demo.read(4), byteorder='little')
        self.buffer = demo.read(self.length)

    def getInfo(self):
        return ( self.getBaseInfo() )

class DemoBufferFrame(Frame):
    def __init__(self, demo, type):
        super().__init__(demo, type)
        self.length = int.from_bytes(demo.read(4), byteorder='little')
        self.buffer = demo.read(self.length)

    def getInfo(self):
        return ( self.getBaseInfo() )

class NetMsgFrame(Frame):
    def __init__(self, demo, type):
        MIN_MESSAGE_LENGTH = 0
        MAX_MESSAGE_LENGTH = 65536
        super().__init__(demo, type)
        self.info = NetMsgInfo(demo)
        self.incoming_sequence = int.from_bytes(demo.read(4), byteorder='little')
        self.incoming_acknowledged = int.from_bytes(demo.read(4), byteorder='little')
        self.incoming_reliable_acknowledged = int.from_bytes(demo.read(4), byteorder='little')
        self.incoming_reliable_sequence = int.from_bytes(demo.read(4), byteorder='little')
        self.outgoing_sequence = int.from_bytes(demo.read(4), byteorder='little')
        self.reliable_sequence = int.from_bytes(demo.read(4), byteorder='little')
        self.last_reliable_sequence = int.from_bytes(demo.read(4), byteorder='little')
        self.msg_length = int.from_bytes(demo.read(4), byteorder='little')
        self.msg = demo.read(self.msg_length)

    def getInfo(self):
        return ( self.getBaseInfo() )


class NetMsgInfo():
    def __init__(self, demo):
        self.timestamp = struct.unpack('f', demo.read(4))
        self.ref_params = RefParams(demo)
        self.user_cmd = UserCmd(demo)
        self.move_vars = MoveVars(demo)
        self.view = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.viewmodel = int.from_bytes(demo.read(4), byteorder='little')
       
        
class RefParams():
    def __init__(self, demo):
        self.vieworg = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.viewangles = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.forward = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.right = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.up = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.frametime = struct.unpack('f', demo.read(4))
        self.time = struct.unpack('f', demo.read(4))
        self.intermission = int.from_bytes(demo.read(4), byteorder='little')
        self.paused = int.from_bytes(demo.read(4), byteorder='little')
        self.spectator = int.from_bytes(demo.read(4), byteorder='little')
        self.onground = int.from_bytes(demo.read(4), byteorder='little')
        self.waterlevel = int.from_bytes(demo.read(4), byteorder='little')
        self.simvel = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.simorg = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.viewheight = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.idealpitch = struct.unpack('f', demo.read(4))
        self.cl_viewangles = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.health = int.from_bytes(demo.read(4), byteorder='little')
        self.crosshairangle = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.viewsize = struct.unpack('f', demo.read(4))
        self.punchangle = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.maxclients = int.from_bytes(demo.read(4), byteorder='little')
        self.viewentity = int.from_bytes(demo.read(4), byteorder='little')
        self.playernum = int.from_bytes(demo.read(4), byteorder='little')
        self.max_entities = int.from_bytes(demo.read(4), byteorder='little')
        self.demoplayback = int.from_bytes(demo.read(4), byteorder='little')
        self.hardware = int.from_bytes(demo.read(4), byteorder='little')
        self.smoothing = int.from_bytes(demo.read(4), byteorder='little')
        self.ptr_cmd = int.from_bytes(demo.read(4), byteorder='little')
        self.ptr_movevars = int.from_bytes(demo.read(4), byteorder='little')
        self.viewport = [struct.unpack('f', demo.read(4)) for i in range(4)]
        self.next_view = int.from_bytes(demo.read(4), byteorder='little')
        self.only_client_draw = int.from_bytes(demo.read(4), byteorder='little')

class UserCmd():
    def __init__(self, demo):
        self.lerp_msec = int.from_bytes(demo.read(2), byteorder='little')
        self.msec = int.from_bytes(demo.read(1), byteorder='little')
        align_1 = int.from_bytes(demo.read(1), byteorder='little')
        self.viewangles = [struct.unpack('f', demo.read(4)) for i in range(3)]
        self.forwardmove = struct.unpack('f', demo.read(4))
        self.sidemove = struct.unpack('f', demo.read(4))
        self.upmove = struct.unpack('f', demo.read(4))
        self.lightlevel = int.from_bytes(demo.read(1), byteorder='little')
        align_2 = int.from_bytes(demo.read(1), byteorder='little')
        self.buttons = int.from_bytes(demo.read(2), byteorder='little')
        self.impulse = int.from_bytes(demo.read(1), byteorder='little')
        self.weaponselect = int.from_bytes(demo.read(1), byteorder='little')
        align_3 = int.from_bytes(demo.read(1), byteorder='little')
        align_4 = int.from_bytes(demo.read(1), byteorder='little')
        self.impact_index = int.from_bytes(demo.read(4), byteorder='little')
        self.impact_position = [struct.unpack('f', demo.read(4)) for i in range(3)]

class MoveVars():
    def __init__(self, demo):
        self.gravity = struct.unpack('f', demo.read(4))
        self.stopspeed = struct.unpack('f', demo.read(4))
        self.maxspeed = struct.unpack('f', demo.read(4))
        self.spectatormaxspeed = struct.unpack('f', demo.read(4))
        self.accelerate = struct.unpack('f', demo.read(4))
        self.airaccelerate = struct.unpack('f', demo.read(4))
        self.wateraccelerate = struct.unpack('f', demo.read(4)) 
        self.friction = struct.unpack('f', demo.read(4))
        self.edgefriction = struct.unpack('f', demo.read(4))
        self.waterfriction = struct.unpack('f', demo.read(4))
        self.entgravity = struct.unpack('f', demo.read(4))
        self.bounce = struct.unpack('f', demo.read(4))
        self.stepsize = struct.unpack('f', demo.read(4))
        self.maxvelocity = struct.unpack('f', demo.read(4))
        self.zmax = struct.unpack('f', demo.read(4))
        self.wave_height = struct.unpack('f', demo.read(4))
        self.footsteps = int.from_bytes(demo.read(4), byteorder='little')
        self.sky_name = demo.read(32)
        self.rollangle = struct.unpack('f', demo.read(4))
        self.rollspeed = struct.unpack('f', demo.read(4))
        self.skycolor_r = struct.unpack('f', demo.read(4))
        self.skycolor_g = struct.unpack('f', demo.read(4))
        self.skycolor_b = struct.unpack('f', demo.read(4))
        self.skyvec_x = struct.unpack('f', demo.read(4))
        self.skyvec_y = struct.unpack('f', demo.read(4))
        self.skyvec_z = struct.unpack('f', demo.read(4))


