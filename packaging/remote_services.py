"""Cliente administrativo HTTPS; credencial persistida com DPAPI no Windows."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import uuid
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError
import ssl

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Redirecionamento do agente recusado.')


def validate_url(url):
    parsed=urlsplit(url.rstrip('/'))
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Informe uma URL HTTPS sem credenciais, parâmetros ou fragmento.')
    return url.rstrip('/')

class RemoteServices:
    def __init__(self,url,token,ca_file=None):
        self.url=validate_url(url);self.token=token
        self.opener=build_opener(NoRedirect(),HTTPSHandler(context=ssl.create_default_context(cafile=ca_file or None)))
    def request(self,path,action=False):
        headers={'Authorization':'Bearer '+self.token,'Accept':'application/json'}
        if action:headers.update({'Content-Type':'application/json','Idempotency-Key':str(uuid.uuid4())})
        request=Request(self.url+path,headers=headers,data=b'{}' if action else None)
        try:
            with self.opener.open(request,timeout=20) as response:
                return json.loads(response.read(2*1024*1024))['data']
        except HTTPError as error:
            raise ValueError(f'Agente respondeu HTTP {error.code}. Confira a credencial e a instalação.') from None
    def services(self):return self.request('/v1/services')
    def command(self,ident,action):
        import re
        if not re.fullmatch(r'[a-f0-9]{64}',ident) or action not in ('start','stop','restart'):raise ValueError('Operação inválida.')
        return self.request(f'/v1/services/{ident}/{action}',True)
    def logs(self,ident):
        import re
        if not re.fullmatch(r'[a-f0-9]{64}',ident):raise ValueError('Serviço inválido.')
        return self.request(f'/v1/services/{ident}/logs')['text']


def protect(value,decrypt=False):
    if os.name!='nt':raise OSError('O cofre DPAPI exige Windows.')
    class Blob(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    raw=value if isinstance(value,bytes) else value.encode()
    buffer=(ctypes.c_ubyte*len(raw)).from_buffer_copy(raw);source=Blob(len(raw),buffer);target=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    call=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    call.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    call.restype=wintypes.BOOL
    if not call(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):raise ctypes.WinError(ctypes.get_last_error())
    try:return ctypes.string_at(target.data,target.size)
    finally:
        kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree(target.data)

def save_token(path,token):
    path=Path(path);temp=path.with_suffix('.tmp');temp.write_bytes(protect(token));temp.replace(path)
def load_token(path):
    path=Path(path)
    return protect(path.read_bytes(),True).decode() if path.exists() else ''
