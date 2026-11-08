"""XTest input and readback for a private Xvfb display, never the user's display.

Only :189 is accepted. The portable Xvfb server uses a private authority file and
has TCP disabled. This adapter lets the same rendered input fixtures run while
the user works in their normal Wayland desktop.
"""
import ctypes as C
import json
import os
from pathlib import Path
import time


class XImage(C.Structure):
    _fields_ = [('width',C.c_int),('height',C.c_int),('xoffset',C.c_int),('format',C.c_int),
                ('data',C.c_void_p),('byte_order',C.c_int),('bitmap_unit',C.c_int),
                ('bitmap_bit_order',C.c_int),('bitmap_pad',C.c_int),('depth',C.c_int),
                ('bytes_per_line',C.c_int),('bits_per_pixel',C.c_int),
                ('red_mask',C.c_ulong),('green_mask',C.c_ulong),('blue_mask',C.c_ulong),
                ('obdata',C.c_void_p)]


class PrivateX11:
    def __init__(self, display=':189', authority='/tmp/dink-qa-tools/xauthority'):
        if display != ':189':
            raise SystemExit('Private QA accepts only :189; it cannot send keys to the normal desktop.')
        os.environ['XAUTHORITY'] = authority
        self.x = C.CDLL('libX11.so.6')
        self.xt = C.CDLL('libXtst.so.6')
        ptr = C.c_void_p; win = C.c_ulong
        self.x.XOpenDisplay.argtypes=[C.c_char_p];self.x.XOpenDisplay.restype=ptr
        self.x.XDefaultRootWindow.argtypes=[ptr];self.x.XDefaultRootWindow.restype=win
        self.x.XQueryTree.argtypes=[ptr,win,C.POINTER(win),C.POINTER(win),C.POINTER(C.POINTER(win)),C.POINTER(C.c_uint)]
        self.x.XFetchName.argtypes=[ptr,win,C.POINTER(ptr)]
        self.x.XInternAtom.argtypes=[ptr,C.c_char_p,C.c_int];self.x.XInternAtom.restype=C.c_ulong
        self.x.XGetWindowProperty.argtypes=[ptr,win,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(ptr)]
        self.x.XFree.argtypes=[ptr]
        self.x.XGetGeometry.argtypes=[ptr,win,C.POINTER(win),C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)]
        self.x.XGetInputFocus.argtypes=[ptr,C.POINTER(win),C.POINTER(C.c_int)]
        self.x.XSetInputFocus.argtypes=[ptr,win,C.c_int,C.c_ulong]
        self.x.XRaiseWindow.argtypes=[ptr,win]
        self.x.XResizeWindow.argtypes=[ptr,win,C.c_uint,C.c_uint]
        self.x.XMoveWindow.argtypes=[ptr,win,C.c_int,C.c_int]
        self.x.XFlush.argtypes=[ptr]
        self.x.XSync.argtypes=[ptr,C.c_int]
        self.x.XStringToKeysym.argtypes=[C.c_char_p];self.x.XStringToKeysym.restype=C.c_ulong
        self.x.XKeysymToKeycode.argtypes=[ptr,C.c_ulong];self.x.XKeysymToKeycode.restype=C.c_uint
        self.x.XkbKeycodeToKeysym.argtypes=[ptr,C.c_uint,C.c_int,C.c_int];self.x.XkbKeycodeToKeysym.restype=C.c_ulong
        self.xt.XTestFakeKeyEvent.argtypes=[ptr,C.c_uint,C.c_int,C.c_ulong]
        self.x.XGetImage.argtypes=[ptr,win,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_ulong,C.c_int]
        self.x.XGetImage.restype=C.POINTER(XImage)
        self.x.XDestroyImage.argtypes=[C.POINTER(XImage)]
        self.d = self.x.XOpenDisplay(display.encode())
        if not self.d:
            raise SystemExit('Cannot open private display :189. Start its Xvfb server and supply its authority file.')
        self.root = self.x.XDefaultRootWindow(self.d)

    def children(self, window):
        root=C.c_ulong();parent=C.c_ulong();children=C.POINTER(C.c_ulong)();count=C.c_uint()
        self.x.XQueryTree(self.d,window,C.byref(root),C.byref(parent),C.byref(children),C.byref(count))
        result=[children[i] for i in range(count.value)]
        if children:self.x.XFree(children)
        return result

    def title(self, window):
        name=C.c_void_p()
        if not self.x.XFetchName(self.d,window,C.byref(name)) or not name.value:return ''
        result=C.string_at(name).decode('utf-8',errors='replace');self.x.XFree(name)
        return result

    def pid(self,window):
        atom=self.x.XInternAtom(self.d,b'_NET_WM_PID',1)
        actual=C.c_ulong();fmt=C.c_int();count=C.c_ulong();remaining=C.c_ulong();data=C.c_void_p()
        self.x.XGetWindowProperty(self.d,window,atom,0,1,0,0,C.byref(actual),C.byref(fmt),C.byref(count),C.byref(remaining),C.byref(data))
        result=C.cast(data,C.POINTER(C.c_ulong))[0] if data.value and count.value else None
        if data.value:self.x.XFree(data)
        return result

    def geometry(self, window):
        root=C.c_ulong();x=C.c_int();y=C.c_int();w=C.c_uint();h=C.c_uint();border=C.c_uint();depth=C.c_uint()
        self.x.XGetGeometry(self.d,window,C.byref(root),C.byref(x),C.byref(y),C.byref(w),C.byref(h),C.byref(border),C.byref(depth))
        return x.value,y.value,w.value,h.value

    def window(self):
        matches=[]
        pending=self.children(self.root)
        while pending:
            w=pending.pop();title=self.title(w)
            if title.startswith('DinkRemaster ('):matches.append((w,title))
            pending.extend(self.children(w))
        if len(matches)!=1:raise SystemExit(f'Expected one Dink window on private :189; found {len(matches)}')
        w,title=matches[0];x,y,width,height=self.geometry(w)
        return {'address':hex(w),'id':w,'class':'UnrealEditor','title':title,'at':[x,y],
                'size':[width,height],'pid':self.pid(w),'backend':'private Xvfb :189 with XTest'}

    def focus(self, window):
        # This changes focus only inside Xvfb, never in the real desktop.
        self.x.XRaiseWindow(self.d,window['id'])
        self.x.XSetInputFocus(self.d,window['id'],2,0);self.x.XSync(self.d,0)
        time.sleep(.1)

    def require_focus(self):
        expected=self.window()['id'];focused=C.c_ulong();revert=C.c_int()
        self.x.XGetInputFocus(self.d,C.byref(focused),C.byref(revert))
        if focused.value!=expected:raise SystemExit('Private Dink window lost focus; input stopped.')

    def key(self,name,pressed):
        symbol=ord(name) if len(name)==1 else self.x.XStringToKeysym(name.encode())
        code=self.x.XKeysymToKeycode(self.d,symbol)
        if not code:raise RuntimeError(f'No private X11 keycode for {name}')
        self.xt.XTestFakeKeyEvent(self.d,code,int(pressed),0);self.x.XFlush(self.d)

    def text(self,text,delay_ms):
        for character in text:
            symbol=ord(character);code=self.x.XKeysymToKeycode(self.d,symbol)
            if not code:raise RuntimeError(f'No private keycode for {character!r}')
            unshifted=self.x.XkbKeycodeToKeysym(self.d,code,0,0)
            shifted=self.x.XkbKeycodeToKeysym(self.d,code,0,1)
            shift=symbol!=unshifted and symbol==shifted
            if shift:self.key('Shift_L',True)
            self.xt.XTestFakeKeyEvent(self.d,code,1,0);self.xt.XTestFakeKeyEvent(self.d,code,0,0)
            if shift:self.key('Shift_L',False)
            self.x.XFlush(self.d);time.sleep(delay_ms/1000)

    def capture(self,path):
        from PIL import Image
        w=self.window();width,height=w['size']
        image=self.x.XGetImage(self.d,w['id'],0,0,width,height,C.c_ulong(-1).value,2)
        if not image:raise RuntimeError('Private framebuffer readback failed')
        info=image.contents
        if info.bits_per_pixel!=32 or info.red_mask!=0xff0000:
            self.x.XDestroyImage(image);raise RuntimeError('Unsupported private framebuffer pixel format')
        pixels=C.string_at(info.data,info.bytes_per_line*height)
        result=Image.frombuffer('RGB',(width,height),pixels,'raw','BGRX',info.bytes_per_line,1)
        Path(path).parent.mkdir(parents=True,exist_ok=True);result.save(path)
        self.x.XDestroyImage(image)

    def command(self,*args):
        if args[0]=='grim':self.capture(args[-1]);return ''
        if args[0]!='wtype':raise RuntimeError(f'Unsupported private-display command {args[0]}; refusing host fallback')
        self.require_focus();delay=0;i=1
        while i<len(args):
            arg=args[i]
            if arg in ['-P','-p','-k','-s','-d']:
                value=args[i+1];i+=2
                if arg=='-s':time.sleep(float(value)/1000)
                elif arg=='-d':delay=float(value)
                elif arg=='-P':self.key(value,True)
                elif arg=='-p':self.key(value,False)
                else:self.key(value,True);self.key(value,False)
            else:self.text(arg,delay);i+=1
        self.x.XSync(self.d,0);return ''

    def dispatch(self,window,operation):
        if 'focus' in operation:self.focus(window)
        elif 'resize' in operation:self.x.XResizeWindow(self.d,window['id'],1280,720)
        elif 'move' in operation:self.x.XMoveWindow(self.d,window['id'],0,0)
        elif 'float' not in operation:raise RuntimeError('Unknown private window operation')
        self.x.XSync(self.d,0)
