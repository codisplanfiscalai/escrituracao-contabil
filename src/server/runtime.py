"""Inicialização do servidor corporativo e integração com o desktop."""
import argparse
import os
from pathlib import Path
import socket
import threading
import time
import uvicorn
from .app import create_app

class PortalServer:
    def __init__(self,database,port):
        self.database=str(database)
        self.server_port=int(port)
        self.app=create_app(Path(database).parent/'identity',f'http://127.0.0.1:{port}',database=database)
        config=uvicorn.Config(self.app,host='127.0.0.1',port=port,loop='asyncio',http='h11',ws='none',log_config=None,access_log=False,log_level='error')
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.bind(('127.0.0.1',int(port)))
        self.socket.listen(128)
        self.server=uvicorn.Server(config)
        self.thread=None
    def serve_forever(self):self.server.run(sockets=[self.socket])
    def shutdown(self):self.server.should_exit=True
    def server_close(self):self.socket.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',default=os.getenv('ESCRITURA_HOST','0.0.0.0'))
    parser.add_argument('--port',type=int,default=int(os.getenv('ESCRITURA_PORT','8765')))
    parser.add_argument('--data',default=os.getenv('ESCRITURA_DATA','/data'))
    parser.add_argument('--public-url',default=os.getenv('ESCRITURA_PUBLIC_URL'))
    parser.add_argument('--database')
    args=parser.parse_args()
    directory=Path(args.database).resolve().parent/'identity' if args.database else Path(args.data)
    public_url=args.public_url or f'http://127.0.0.1:{args.port}'
    app=create_app(directory,public_url,database=args.database,setup_file=os.getenv('ESCRITURA_SETUP_TOKEN_FILE'),key_file=os.getenv('ESCRITURA_KEY_FILE'))
    uvicorn.run(app,host=args.host,port=args.port,loop='asyncio',http='h11',ws='none',proxy_headers=False,access_log=False,
                ssl_certfile=os.getenv('ESCRITURA_TLS_CERT'),ssl_keyfile=os.getenv('ESCRITURA_TLS_KEY'))

if __name__=='__main__':main()
