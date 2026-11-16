"""Read current DST animation metadata without extracting game textures."""
import argparse
import json
import struct
import zipfile
from pathlib import Path

GAME = Path("E:/steam/steamapps/common/Don't Starve Together")

class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0
    def unpack(self, fmt):
        size = struct.calcsize('<' + fmt)
        result = struct.unpack_from('<' + fmt, self.data, self.pos)
        self.pos += size
        return result
    def string(self):
        n, = self.unpack('I')
        result = self.data[self.pos:self.pos+n].decode('utf-8')
        self.pos += n
        return result
    def strings(self):
        n, = self.unpack('I')
        return {self.unpack('I')[0]: self.string() for _ in range(n)}

def read_build(data):
    r = Reader(data)
    magic, version, nsymbols, nframes = r.unpack('4sIII')
    assert magic == b'BILD' and version == 6
    name = r.string()
    atlas_count, = r.unpack('I')
    atlases = [r.string() for _ in range(atlas_count)]
    symbols = []
    for _ in range(nsymbols):
        h, count = r.unpack('II')
        frames = []
        for _ in range(count):
            f, duration, x, y, w, height, start, vertices = r.unpack('IIffffII')
            frames.append(dict(frame=f, duration=duration, x=x, y=y, w=w, h=height))
        symbols.append(dict(hash=h, frames=frames))
    vertices, = r.unpack('I')
    r.pos += vertices * 24
    names = r.strings()
    for symbol in symbols:
        symbol['name'] = names[symbol.pop('hash')]
    return dict(name=name, frame_count=nframes, symbols=symbols, atlases=atlases)

def read_anim(data):
    r = Reader(data)
    magic, version, ne, nf, nev, na = r.unpack('4sIIIII')
    assert magic == b'ANIM' and version == 4
    anims = []
    for _ in range(na):
        name = r.string()
        facing, root, fps, count = r.unpack('BIfI')
        frames = []
        for _ in range(count):
            box = r.unpack('ffff')
            event_count, = r.unpack('I')
            events = [r.unpack('I')[0] for _ in range(event_count)]
            element_count, = r.unpack('I')
            elements = []
            for _ in range(element_count):
                symbol, frame, layer, a, b, c, d, tx, ty, tz = r.unpack('IIIfffffff')
                elements.append(dict(symbol=symbol, frame=frame, layer=layer,
                    a=a, b=b, c=c, d=d, tx=tx, ty=ty, tz=tz))
            frames.append(dict(box=box, events=events, elements=elements))
        anims.append(dict(name=name, facing=facing, root=root, fps=fps, frames=frames))
    names = r.strings()
    for anim in anims:
        anim['root'] = names[anim['root']]
        for frame in anim['frames']:
            frame['events'] = [names[e] for e in frame['events']]
            for element in frame['elements']:
                element['symbol'] = names[element['symbol']]
                element['layer'] = names[element['layer']]
    return anims

def read_game_zip(name, member):
    path = GAME / 'data' / 'anim' / (name + '.zip')
    with zipfile.ZipFile(path) as z:
        return z.read(member)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('name', nargs='?', default='wilson')
    p.add_argument('--anim', action='store_true')
    p.add_argument('--script')
    p.add_argument('--start',type=int,default=1)
    p.add_argument('--count',type=int,default=80)
    p.add_argument('--find')
    p.add_argument('--search')
    args = p.parse_args()
    if args.search:
        import re
        pattern=re.compile(args.search)
        found=0
        with zipfile.ZipFile(GAME/'data/databundles/scripts.zip') as z:
            for entry in z.namelist():
                if not entry.endswith('.lua'):continue
                for index,line in enumerate(z.read(entry).decode('utf-8-sig',errors='replace').splitlines()):
                    if pattern.search(line):
                        print(f'{entry}:{index+1}:{line[:250]}');found+=1
                        if found>=40:raise SystemExit(0)
        raise SystemExit(0)
    if args.script:
        with zipfile.ZipFile(GAME/'data/databundles/scripts.zip') as z:
            lines=z.read('scripts/'+args.script).decode('utf-8-sig').splitlines()
        if args.find:
            import re
            matches=[i for i,line in enumerate(lines) if re.search(args.find,line)]
            for index in matches[:20]:
                print('\n'.join(str(i+1)+':'+lines[i] for i in range(max(0,index-2),min(len(lines),index+args.count))))
            raise SystemExit(0)
        print('\n'.join(str(i+1)+':'+lines[i] for i in range(args.start-1,min(len(lines),args.start+args.count-1))))
        raise SystemExit(0)
    value = read_anim(read_game_zip(args.name, 'anim.bin')) if args.anim else read_build(read_game_zip(args.name, 'build.bin'))
    if args.anim:
        value = [{k: v for k, v in a.items() if k != 'frames'} | {'frames':len(a['frames'])} for a in value]
    print(json.dumps(value, indent=2))
