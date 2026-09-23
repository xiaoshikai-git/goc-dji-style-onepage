#!/usr/bin/env python3
"""Native draw.io primitives and local previews for Feishu wireframe workflows.

Requires Pillow. No network, browser control, credentials, or Feishu mutations.
Import Board from a project-specific build script; run --demo for an example.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise SystemExit("Pillow is required. Use the bundled workspace Python or install Pillow.") from exc


def _default_font(bold=False):
    paths = [
        f"/System/Library/Fonts/Supplemental/Arial{' Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"C:/Windows/Fonts/arial{'bd' if bold else ''}.ttf",
    ]
    for path in paths:
        if Path(path).is_file():
            return path
    raise ValueError("No default font found; pass font_path and font_family to Board.")


@lru_cache(maxsize=128)
def _font(path, size):
    return ImageFont.truetype(str(path), max(1, round(size)))


def _wrap(value, width, font):
    """Word wrap Latin and character wrap CJK/long words without dropping text."""
    if width <= 0:
        raise ValueError("Text width must be positive")
    rows = []
    for paragraph in str(value).split('\n'):
        row = ''
        tokens = re.findall(r'[\u2e80-\u9fff\uac00-\ud7ff]|[^\s\u2e80-\u9fff\uac00-\ud7ff]+|[ \t]+', paragraph)
        for token in tokens:
            if not row and token.isspace():
                continue
            if font.getlength(row + token) <= width:
                row += token
                continue
            if row:
                rows.append(row.rstrip())
                row = ''
            if token.isspace():
                continue
            for char in token:
                if font.getlength(char) > width:
                    raise ValueError(f"Text column is narrower than one character: {char!r}")
                if row and font.getlength(row + char) > width:
                    rows.append(row)
                    row = ''
                row += char
        rows.append(row.rstrip())
    return rows


class Frame:
    def __init__(self, board, name, x, y, width):
        if not all(math.isfinite(v) and v >= 0 for v in (x, y, width)) or width == 0:
            raise ValueError('Frame origin must be nonnegative and width positive')
        self.board, self.name = board, name
        self.x, self.y, self.width = x, y, width
        self.height = None
        self.shapes = []

    def _add(self, kind, x, y, w, h, **attrs):
        if self.height is not None:
            raise ValueError(f'{self.name}: finish() has already been called')
        if not all(math.isfinite(v) and v >= 0 for v in (x, y, w, h)):
            raise ValueError(f'{self.name}: invalid {kind} geometry')
        if x + w > self.width + 0.01:
            raise ValueError(f'{self.name}: {kind} crosses the right frame boundary')
        self.shapes.append(dict(kind=kind, x=x, y=y, w=w, h=h, **attrs))

    def rect(self, x, y, w, h, fill='#FFFFFF', stroke='#BBBBBB'):
        self._add('rect', x, y, w, h, fill=fill, stroke=stroke)

    def line(self, x1, y1, x2, y2, color='#BBBBBB'):
        self._add('line', min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1),
                  x1=x1, y1=y1, x2=x2, y2=y2, stroke=color)

    def text(self, value, x, y, w, size=18, bold=False, color='#222222', align='left', height=None):
        if align not in ('left', 'center', 'right') or size <= 0:
            raise ValueError('Invalid text alignment or size')
        font_path = self.board.bold_font_path if bold else self.board.font_path
        rows = _wrap(value, w - 4, _font(font_path, size))
        needed = math.ceil(len(rows) * size * 1.4 + 4)
        if height is not None and height < needed:
            raise ValueError(f'{self.name}: text needs {needed} height, got {height}: {value!r}')
        h = needed if height is None else height
        self._add('text', x, y, w, h, text='\n'.join(rows), size=size, bold=bold,
                  color=color, align=align, font_path=str(font_path))
        return h

    def button(self, label, x, y, w=200, h=48, primary=True):
        font = _font(self.board.font_path, 17)
        rows = _wrap(label, w-28, font)
        th = math.ceil(len(rows)*17*1.4+4)
        if th > h-8:
            raise ValueError(f'Button label does not fit: {label!r}; increase width/height')
        self.rect(x,y,w,h,'#171717' if primary else '#FFFFFF','#171717')
        self.text(label,x+12,y+(h-th)/2,w-24,17,color='#FFFFFF' if primary else '#222222',align='center')

    def media(self, label, x, y, w, h, video=False):
        rows = _wrap(label, w-44, _font(self.board.font_path,17))
        th = math.ceil(len(rows)*17*1.4+4)
        extra = 72 if video else 0
        if h < th+extra+32:
            raise ValueError('Media label does not fit; enlarge the media frame')
        self.rect(x,y,w,h,'#EEEEEE','#BBBBBB')
        ty=y+(h-th-extra)/2
        if video:
            self._add('ellipse',x+w/2-24,ty,48,48,fill='#FFFFFF',stroke='#777777')
            self._add('triangle',x+w/2-7,ty+13,18,22,fill='#333333',stroke='none')
            ty+=extra
        self.text(label,x+20,ty,w-40,17,color='#666666',align='center')

    def finish(self, height=None):
        if self.height is not None:
            raise ValueError(f'{self.name}: frame already finished')
        minimum=max((s['y']+s['h'] for s in self.shapes),default=0)
        height = math.ceil(minimum) if height is None else height
        if not math.isfinite(height) or height <= 0 or height < minimum:
            raise ValueError(f'{self.name}: frame height {height} does not contain content ({minimum})')
        self.height=height
        return self


class Board:
    def __init__(self, name, font_path=None, bold_font_path=None, font_family='Arial'):
        self.name = name
        self.font_path=str(font_path or _default_font())
        self.bold_font_path=str(bold_font_path or (font_path if font_path else _default_font(True)))
        self.font_family=font_family
        _font(self.font_path,18)
        _font(self.bold_font_path,18)
        self.frames=[]

    def frame(self, name, x=0, y=0, width=1200):
        if any(f.name == name for f in self.frames):
            raise ValueError(f'Duplicate frame name: {name}')
        f=Frame(self,name,x,y,width)
        self.frames.append(f)
        return f

    def write(self, path, preview=True, scale=0.6):
        path=Path(path)
        if path.suffix != '.drawio':
            raise ValueError('Output path must end with .drawio')
        if not self.frames or any(f.height is None for f in self.frames):
            raise ValueError('Create at least one frame and call finish() on every frame')
        if scale <= 0 or not math.isfinite(scale):
            raise ValueError('Preview scale must be finite and positive')
        doc=ET.Element('mxfile',host='app.diagrams.net')
        diagram=ET.SubElement(doc,'diagram',name=self.name,id='wireframes')
        root=ET.SubElement(ET.SubElement(diagram,'mxGraphModel',page='0'),'root')
        ET.SubElement(root,'mxCell',id='0')
        ET.SubElement(root,'mxCell',id='1',parent='0')
        for fi,f in enumerate(self.frames):
            for si,s in enumerate(f.shapes):
                attrs=dict(id=f'f{fi}-s{si}',parent='1',value=s.get('text',''))
                if s['kind']=='line':
                    attrs.update(edge='1',style=f"endArrow=none;startArrow=none;strokeColor={s['stroke']};")
                    cell=ET.SubElement(root,'mxCell',attrs)
                    g=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
                    for n in (1,2):
                        ET.SubElement(g,'mxPoint',x=str(f.x+s[f'x{n}']),y=str(f.y+s[f'y{n}']),attrib={'as':'sourcePoint' if n==1 else 'targetPoint'})
                    continue
                if s['kind']=='text':
                    style=(f"text;html=0;whiteSpace=wrap;fillColor=none;strokeColor=none;align={s['align']};"
                           f"verticalAlign=top;fontFamily={self.font_family};fontSize={s['size']};"
                           f"fontStyle={int(s['bold'])};fontColor={s['color']};spacing=0;")
                else:
                    kind={'rect':'rounded=0','ellipse':'ellipse','triangle':'triangle;direction=east'}[s['kind']]
                    style=f"{kind};fillColor={s['fill']};strokeColor={s['stroke']};strokeWidth=1;"
                attrs.update(vertex='1',style=style)
                cell=ET.SubElement(root,'mxCell',attrs)
                ET.SubElement(cell,'mxGeometry',x=str(f.x+s['x']),y=str(f.y+s['y']),
                              width=str(s['w']),height=str(s['h']),attrib={'as':'geometry'})
        path.parent.mkdir(parents=True,exist_ok=True)
        ET.ElementTree(doc).write(path,encoding='utf-8',xml_declaration=True)
        ET.parse(path)
        geometry=[dict(name=f.name,x=f.x,y=f.y,width=f.width,height=f.height,shapes=f.shapes) for f in self.frames]
        path.with_suffix('.geometry.json').write_text(json.dumps(geometry,ensure_ascii=False,indent=2),encoding='utf-8')
        if preview:
            folder=path.parent/(path.stem+'-previews')
            folder.mkdir(exist_ok=True)
            for i,f in enumerate(self.frames,1):
                safe=re.sub(r'[^\w.-]+','-',f.name).strip('-') or 'frame'
                self._preview(f,folder/f'{i:02d}-{safe}.png',scale)
        return dict(file=str(path.resolve()),frames=len(self.frames),elements=sum(len(f.shapes) for f in self.frames))

    def _preview(self, frame, path, scale):
        im=Image.new('RGB',(math.ceil(frame.width*scale),math.ceil(frame.height*scale)),'#FFFFFF')
        d=ImageDraw.Draw(im)
        for s in frame.shapes:
            x,y,w,h=(s[k]*scale for k in ('x','y','w','h'))
            color=lambda key: None if s.get(key)=='none' else s.get(key)
            if s['kind']=='line':
                d.line([s[k]*scale for k in ('x1','y1','x2','y2')],fill=s['stroke'],width=max(1,round(scale)))
            elif s['kind']=='text':
                font=_font(s['font_path'],s['size']*scale)
                for i,row in enumerate(s['text'].split('\n')):
                    offset=0 if s['align']=='left' else (w-font.getlength(row))/(2 if s['align']=='center' else 1)
                    d.text((x+offset,y+i*s['size']*1.4*scale),row,font=font,fill=s['color'],anchor='lt')
            elif s['kind']=='triangle':
                d.polygon([(x,y),(x+w,y+h/2),(x,y+h)],fill=color('fill'),outline=color('stroke'))
            else:
                fn=d.ellipse if s['kind']=='ellipse' else d.rectangle
                fn((x,y,x+w,y+h),fill=color('fill'),outline=color('stroke'),width=max(1,round(scale)))
        im.save(path)


def demo(output_dir):
    b=Board('Website wireframe / capability example')
    f=b.frame('Home / example')
    f.rect(0,0,1200,76,'#171717','#171717')
    f.text('01 / Home',24,15,1152,32,True,'#FFFFFF')
    f.rect(0,120,1200,104)
    f.text('STUDIO',48,151,190,26,True)
    f.text('Services     Work     About     Contact',560,157,592,18)
    f.rect(0,224,1200,600,'#FAFAFA','#DDDDDD')
    f.text('Spaces made for everyday life.',64,310,480,44,True)
    f.text('Explore a considered approach to planning, materials and the details you use every day.',64,448,470,20)
    f.button('Explore our approach',64,682,228)
    f.media('Interior project / wide view and natural light',630,280,506,472)
    f.rect(0,824,1200,500,'#FFFFFF','#DDDDDD')
    f.text('Find your starting point',64,880,1072,32,True)
    for i,(title,body) in enumerate([
        ('Plan your space','Understand the sequence from first conversation to a clear brief.'),
        ('Explore materials','See how surfaces, light and texture work together.'),
        ('Meet the studio','Learn about the people and process behind the work.')]):
        x=64+i*365
        f.rect(x,960,342,294)
        f.media(title+' / reference image',x+16,976,310,130)
        f.text(title,x+18,1126,306,23,True)
        f.text(body,x+18,1172,306,18)
    f.rect(0,1324,1200,180,'#F4F4F4','#DDDDDD')
    f.text('STUDIO',64,1360,210,25,True)
    f.text('Services       Projects       About       Contact',450,1368,686,18)
    f.text('Privacy     Terms     Region / Language',64,1436,1072,15,color='#666666')
    f.finish(1504)
    m=b.frame('Video / open state',x=1520,width=900)
    m.rect(0,0,900,76,'#171717','#171717')
    m.text('02 / Video - open state',24,15,852,30,True,'#FFFFFF')
    m.rect(0,120,900,660,'#777777','#777777')
    m.rect(40,160,820,580)
    m.text('Inside the studio',72,194,680,28,True)
    m.text('X',794,194,34,25,align='center')
    m.media('Studio walkthrough / video',72,260,756,360,video=True)
    m.text('Play / Pause     -----------------     Volume     Full screen',96,654,708,17)
    m.text('Trigger: Watch video. Close returns to the original page position.\nThis is a drawn state; playback is not implemented.',0,826,900,18,color='#666666')
    m.finish()
    print(json.dumps(b.write(Path(output_dir)/'example.drawio'),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo',action='store_true',help='Create one example page and one state locally')
    parser.add_argument('--output-dir',type=Path,default=Path('output/wireframe-example'))
    args=parser.parse_args()
    if args.demo:
        demo(args.output_dir)
    else:
        parser.print_help()
