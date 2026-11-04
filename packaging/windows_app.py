"""Administração gráfica Windows; o motor contábil permanece independente."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes as w
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from src import local_app


class BackendController:
    """Controla apenas a instância local pertencente a este aplicativo."""
    def __init__(self):
        self.server = None
        self.thread = None

    def start(self, database, port, corporate=False):
        if self.server is not None: return
        path = Path(database).expanduser().resolve()
        if not 1024 <= int(port) <= 65535: raise ValueError('Informe uma porta entre 1024 e 65535.')
        if local_app.PROJECT_ROOT == path or local_app.PROJECT_ROOT in path.parents:
            raise ValueError('Escolha a pasta de dados fora da instalação.')
        path.parent.mkdir(parents=True, exist_ok=True)
        with local_app.open_store(path): pass
        if corporate:
            from src.server.runtime import PortalServer
            server = PortalServer(path, int(port))
        else:
            server = local_app.LocalServer(path, int(port))
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, name='EscrituraLocal', daemon=True)
        self.thread.start()
        if corporate:
            deadline=time.monotonic()+10
            while not server.server.started:
                if not self.thread.is_alive() or time.monotonic()>deadline:
                    self.stop()
                    raise RuntimeError('Servidor corporativo não iniciou.')
                time.sleep(0.05)

    def stop(self):
        server, thread = self.server, self.thread
        if server is None: return
        server.shutdown()
        server.server_close()
        if thread: thread.join(timeout=5)
        self.server = self.thread = None

    @property
    def running(self):
        return bool(self.server and self.thread and self.thread.is_alive())


class Tray:
    """Ícone e menu nativos da área de notificação, sem processo de console."""
    def __init__(self, root, icon, callbacks, identity):
        self.root, self.callbacks = root, callbacks
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.shell = ctypes.WinDLL('shell32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.GetModuleHandleW.restype = w.HMODULE
        self.user.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        self.user.DefWindowProcW.restype = ctypes.c_ssize_t
        self.user.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, ctypes.c_void_p]
        self.user.CreateWindowExW.restype = w.HWND
        self.user.LoadImageW.argtypes = [w.HINSTANCE, w.LPCWSTR, w.UINT, ctypes.c_int, ctypes.c_int, w.UINT]
        self.user.LoadImageW.restype = w.HANDLE
        self.user.CreatePopupMenu.restype = w.HMENU
        self.user.AppendMenuW.argtypes = [w.HMENU, w.UINT, ctypes.c_size_t, w.LPCWSTR]
        self.user.TrackPopupMenu.argtypes = [w.HMENU, w.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.HWND, ctypes.c_void_p]
        self.user.SetForegroundWindow.argtypes = [w.HWND]
        self.user.DestroyMenu.argtypes = [w.HMENU]
        self.user.DestroyWindow.argtypes = [w.HWND]
        self.user.DestroyIcon.argtypes = [w.HICON]
        self.user.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        self.user.PeekMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT]
        self.user.DispatchMessageW.argtypes = [ctypes.POINTER(w.MSG)]
        self.user.DispatchMessageW.restype = ctypes.c_ssize_t
        self.user.RegisterWindowMessageW.argtypes = [w.LPCWSTR]
        self.taskbar_created = self.user.RegisterWindowMessageW('TaskbarCreated')
        self.proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        class WindowClass(ctypes.Structure):
            _fields_ = [('style', w.UINT), ('proc', self.proc_type), ('extra_class', ctypes.c_int), ('extra_window', ctypes.c_int), ('instance', w.HINSTANCE), ('icon', w.HICON), ('cursor', w.HANDLE), ('background', w.HBRUSH), ('menu', w.LPCWSTR), ('name', w.LPCWSTR)]
        class Notify(ctypes.Structure):
            _fields_ = [('size', w.DWORD), ('window', w.HWND), ('id', w.UINT), ('flags', w.UINT), ('message', w.UINT), ('icon', w.HICON), ('tip', w.WCHAR * 128), ('state', w.DWORD), ('mask', w.DWORD), ('info', w.WCHAR * 256), ('timeout', w.UINT), ('title', w.WCHAR * 64), ('infoflags', w.DWORD), ('guid', ctypes.c_byte * 16), ('balloon', w.HICON)]
        self.shell.Shell_NotifyIconW.argtypes = [w.DWORD, ctypes.POINTER(Notify)]
        self.proc = self.proc_type(self.handle)
        self.instance = self.kernel.GetModuleHandleW(None)
        self.class_name = 'EscrituraTray_' + identity
        wc = WindowClass(0, self.proc, 0, 0, self.instance, None, None, None, None, self.class_name)
        self.user.RegisterClassW.argtypes = [ctypes.POINTER(WindowClass)]
        if not self.user.RegisterClassW(ctypes.byref(wc)): raise ctypes.WinError(ctypes.get_last_error())
        self.window = self.user.CreateWindowExW(0, self.class_name, 'Escritura', 0, 0, 0, 0, 0, None, None, self.instance, None)
        if not self.window: raise ctypes.WinError(ctypes.get_last_error())
        self.icon = self.user.LoadImageW(None, str(icon), 1, 0, 0, 0x10 | 0x40)
        if not self.icon: raise ctypes.WinError(ctypes.get_last_error())
        self.data = Notify()
        self.data.size, self.data.window, self.data.id = ctypes.sizeof(Notify), self.window, 1
        self.data.flags, self.data.message, self.data.icon = 1 | 2 | 4, 0x8001, self.icon
        self.data.tip = 'Escritura - Administração'
        self.available = bool(self.shell.Shell_NotifyIconW(0, ctypes.byref(self.data)))
        self.closed = False
        self.root.after(100, self.pump)

    def handle(self, window, message, wp, lp):
        if message == self.taskbar_created and hasattr(self, 'data'):
            self.available = bool(self.shell.Shell_NotifyIconW(0, ctypes.byref(self.data)))
            return 0
        if message == 0x8002:
            self.root.after(0, self.callbacks[1][1]); return 0
        if message == 0x8001:
            if lp == 0x0203:
                self.root.after(0, self.callbacks[1][1])
            elif lp in (0x0205, 0x007B):
                menu = self.user.CreatePopupMenu()
                for key, (label, callback) in self.callbacks.items(): self.user.AppendMenuW(menu, 0, key, label)
                point = w.POINT(); self.user.GetCursorPos(ctypes.byref(point))
                self.user.SetForegroundWindow(window)
                selected = self.user.TrackPopupMenu(menu, 0x100 | 2, point.x, point.y, 0, window, None)
                self.user.DestroyMenu(menu)
                if selected in self.callbacks: self.root.after(0, self.callbacks[selected][1])
                self.user.PostMessageW(window, 0, 0, 0)
            return 0
        return self.user.DefWindowProcW(window, message, wp, lp)

    def notify(self, text):
        self.data.flags = 1 | 2 | 4 | 16
        self.data.title, self.data.info, self.data.infoflags = 'Escritura', text[:255], 1
        self.shell.Shell_NotifyIconW(1, ctypes.byref(self.data))
        self.data.flags = 1 | 2 | 4

    def pump(self):
        if self.closed: return
        message = w.MSG()
        while self.user.PeekMessageW(ctypes.byref(message), self.window, 0, 0, 1):
            self.user.TranslateMessage(ctypes.byref(message)); self.user.DispatchMessageW(ctypes.byref(message))
        self.root.after(100, self.pump)

    def close(self):
        self.closed = True
        self.shell.Shell_NotifyIconW(2, ctypes.byref(self.data))
        self.user.DestroyWindow(self.window)
        self.user.DestroyIcon(self.icon)


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--database')
    parser.add_argument('--port', type=int)
    parser.add_argument('--background', action='store_true')
    args = parser.parse_args(argv)
    home = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'EscrituracaoContabil'
    home.mkdir(parents=True, exist_ok=True)
    settings_file = home / 'desktop.json'
    config = {}
    if settings_file.exists():
        try: config = json.loads(settings_file.read_text(encoding='utf-8'))
        except (ValueError, OSError): pass
    database = args.database or config.get('database') or str(home / 'accounting.sqlite3')
    port = args.port or config.get('port', 8765)
    identity = hashlib.sha256(str(home.resolve()).encode()).hexdigest()[:24]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, w.BOOL, w.LPCWSTR]
    kernel.CreateMutexW.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    mutex = kernel.CreateMutexW(None, False, 'Local\\EscrituraDesktop_' + identity)
    if not mutex: raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.FindWindowW.argtypes = [w.LPCWSTR, w.LPCWSTR]; user.FindWindowW.restype = w.HWND
        user.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        window = user.FindWindowW('EscrituraTray_' + identity, None)
        if window: user.PostMessageW(window, 0x8002, 0, 0)
        kernel.CloseHandle(mutex)
        return
    root = tk.Tk(); root.title('Escritura | Administração'); root.geometry('1080x720'); root.minsize(920, 620)
    root.configure(bg='#f3f5f7')
    style = ttk.Style(root); style.theme_use('clam')
    style.configure('TFrame', background='#f3f5f7'); style.configure('TLabel', background='#f3f5f7')
    style.configure('TButton',font=('Segoe UI',10),padding=(12,9))
    style.configure('TNotebook.Tab',padding=(18,10),font=('Segoe UI',10))
    style.configure('TNotebook', background='#eeeeee')
    style.configure('Title.TLabel', foreground='#064D5D', font=('Segoe UI', 18, 'bold'))
    icon = local_app.WEB_ROOT / 'assets/icon.ico'
    root.iconbitmap(str(icon))
    backend = BackendController()
    sidebar=tk.Frame(root,bg='#064d5d',width=210);sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
    tk.Label(sidebar,text='Escritura',font=('Segoe UI',25,'bold'),fg='white',bg='#064d5d').pack(anchor='w',padx=22,pady=(32,4))
    tk.Label(sidebar,text='ORGANIZAÇÃO CONTÁBIL',font=('Segoe UI',8),fg='#adcbd0',bg='#064d5d').pack(anchor='w',padx=24)
    tk.Label(sidebar,text='ADMINISTRAÇÃO\nDA ESTAÇÃO',font=('Segoe UI',9,'bold'),fg='#adcbd0',bg='#064d5d',justify='left').pack(anchor='w',padx=24,pady=(50,12))
    tk.Label(sidebar,text='Serviços e conexões\nConfiguração local\nHistórico operacional',font=('Segoe UI',11),fg='#edf5f6',bg='#064d5d',justify='left',pady=15).pack(anchor='w',padx=24)
    tk.Label(sidebar,text='Disponível na bandeja\nmesmo com a janela fechada.',font=('Segoe UI',9),fg='#adcbd0',bg='#064d5d',justify='left').pack(side='bottom',padx=20,pady=30)
    outer = ttk.Frame(root, padding=26); outer.pack(fill='both', expand=True)
    ttk.Label(outer, text='Administração do ambiente', style='Title.TLabel').pack(anchor='w')
    state = tk.StringVar(value='Serviço parado')
    ttk.Label(outer, textvariable=state, padding=(0, 8)).pack(anchor='w')
    tabs = ttk.Notebook(outer); tabs.pack(fill='both', expand=True)
    operations = ttk.Frame(tabs, padding=16); settings = ttk.Frame(tabs, padding=16); logs = ttk.Frame(tabs, padding=8); remote_tab=ttk.Frame(tabs,padding=16)
    tabs.add(operations, text='Serviços'); tabs.add(settings, text='Configurações'); tabs.add(remote_tab,text='Servidor Docker'); tabs.add(logs, text='Histórico')
    ttk.Label(operations, text='Portal corporativo local\nLogin, usuários, perfis, empresas e escrituração nesta estação.', justify='left').pack(anchor='w', pady=(0, 16))
    ttk.Label(operations, text='O portal de trabalho abre no navegador.\nA administração permanece disponível na área de notificação.', justify='left').pack(anchor='w', pady=8)
    database_var, port_var = tk.StringVar(value=database), tk.StringVar(value=str(port))
    ttk.Label(settings, text='Arquivo de dados privado').grid(row=0, column=0, sticky='w')
    ttk.Entry(settings, textvariable=database_var, width=64).grid(row=1, column=0, sticky='ew', pady=6)
    def choose():
        chosen = filedialog.asksaveasfilename(parent=root, title='Selecionar arquivo de dados', initialfile='accounting.sqlite3', defaultextension='.sqlite3', filetypes=[('Banco SQLite', '*.sqlite3')])
        if chosen: database_var.set(chosen)
    ttk.Button(settings, text='Selecionar...', command=choose).grid(row=1, column=1, padx=8)
    ttk.Label(settings, text='Porta local (127.0.0.1)').grid(row=2, column=0, sticky='w')
    ttk.Entry(settings, textvariable=port_var, width=10).grid(row=3, column=0, sticky='w', pady=6)
    automatic = tk.BooleanVar(value=config.get('auto_start', True))
    ttk.Checkbutton(settings, text='Iniciar o serviço ao abrir o aplicativo', variable=automatic).grid(row=4, column=0, sticky='w', pady=6)
    text = tk.Text(logs, state='disabled', wrap='word', bg='white', relief='flat', font=('Consolas', 10)); text.pack(fill='both', expand=True)
    tray = None
    def log(value):
        text.configure(state='normal'); text.insert('end', datetime.now().strftime('%H:%M:%S') + '  ' + value + '\n'); text.see('end'); text.configure(state='disabled')
        if int(text.index('end-1c').split('.')[0]) > 500:
            text.configure(state='normal'); text.delete('1.0', '100.0'); text.configure(state='disabled')
    def show(): root.deiconify(); root.lift(); root.focus_force()
    def start():
        try:
            backend.start(database_var.get(), int(port_var.get()),corporate=True)
            state.set(f'Serviço ativo - http://127.0.0.1:{backend.server.server_port}')
            log('Serviço iniciado.')
            if tray: tray.notify('Serviço local iniciado.')
        except Exception:
            state.set('Serviço indisponível'); log('Falha ao iniciar. Confira porta, caminho e permissões.')
            if not os.environ.get('ESCRITURA_SMOKE_STOP_EVENT'): messagebox.showerror('Escritura', 'Não foi possível iniciar. Confira a porta, o caminho e as permissões do arquivo de dados.', parent=root)
    def stop():
        backend.stop(); state.set('Serviço parado'); log('Serviço interrompido.')
    def restart(): stop(); start()
    def portal():
        if backend.running: webbrowser.open(f'http://127.0.0.1:{backend.server.server_port}')
        else: messagebox.showinfo('Escritura', 'Inicie o serviço para abrir o portal.', parent=root)
    def save():
        if backend.running:
            messagebox.showinfo('Escritura', 'Interrompa o serviço antes de alterar a configuração.', parent=root); return
        try:
            selected_port = int(port_var.get())
            if not 1024 <= selected_port <= 65535: raise ValueError()
            path = Path(database_var.get()).expanduser().resolve()
            if local_app.PROJECT_ROOT in path.parents or path == local_app.PROJECT_ROOT: raise ValueError()
            tmp = settings_file.with_suffix('.tmp')
            tmp.write_text(json.dumps({'database': str(path), 'port': selected_port, 'auto_start': automatic.get()}, indent=2), encoding='utf-8')
            tmp.replace(settings_file); log('Configuração salva. O arquivo anterior não foi movido ou excluído.')
        except (ValueError, OSError): messagebox.showerror('Escritura', 'Configuração inválida ou sem permissão de gravação.', parent=root)
    ttk.Button(settings, text='Salvar configuração', command=save).grid(row=5, column=0, sticky='w', pady=12)
    buttons = ttk.Frame(operations); buttons.pack(anchor='w', pady=12)
    for label, action in [('Iniciar', start), ('Interromper', stop), ('Reiniciar', restart), ('Abrir portal', portal)]: ttk.Button(buttons, text=label, command=action).pack(side='left', padx=(0, 6))
    def setup_key():
        path=Path(database_var.get()).expanduser().resolve().parent/'identity'/'setup.token'
        if not path.exists():
            messagebox.showinfo('Escritura','Inicie o portal local para preparar a instalação.',parent=root);return
        key=path.read_text(encoding='utf-8').strip()
        root.clipboard_clear();root.clipboard_append(key)
        messagebox.showinfo('Escritura','Chave de instalação copiada. Cole-a na tela de primeiro acesso do portal. Após configurar, esta chave não cria outro administrador.',parent=root)
    ttk.Button(operations,text='Copiar chave do primeiro acesso',command=setup_key).pack(anchor='w',pady=15)
    from remote_services import RemoteServices,save_token,load_token,validate_url
    remote_config_file=home/'remote.json';remote_config={}
    if remote_config_file.exists():
        try:remote_config=json.loads(remote_config_file.read_text(encoding='utf-8'))
        except (ValueError,OSError):pass
    agent_url=tk.StringVar(value=remote_config.get('agent_url',''))
    portal_url=tk.StringVar(value=remote_config.get('portal_url',''))
    ca_file=tk.StringVar(value=remote_config.get('ca_file',''))
    credential=tk.StringVar(value='')
    ttk.Label(remote_tab,text='Conexão com a instalação Docker',font=('Segoe UI',13,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,10))
    for row,label,variable in [(1,'URL HTTPS do portal',portal_url),(3,'URL HTTPS do agente',agent_url),(5,'Certificado da CA (opcional)',ca_file),(7,'Credencial do agente (em branco mantém o cofre)',credential)]:
        ttk.Label(remote_tab,text=label).grid(row=row,column=0,columnspan=3,sticky='w')
        ttk.Entry(remote_tab,textvariable=variable,width=67,show='•' if row==7 else '').grid(row=row+1,column=0,columnspan=3,sticky='ew',pady=(3,9))
    remote_tab.columnconfigure(0,weight=1)
    service_tree=ttk.Treeview(remote_tab,columns=('service','state','image'),show='headings',height=5)
    for column,title,width in [('service','Serviço',150),('state','Estado',90),('image','Imagem',330)]:service_tree.heading(column,text=title);service_tree.column(column,width=width)
    service_tree.grid(row=10,column=0,columnspan=3,sticky='nsew',pady=10)
    remote_tab.rowconfigure(10,weight=1)
    task_queue=queue.Queue();remote_busy=False
    def remote_client():
        token=credential.get() or load_token(home/'agent.dpapi')
        if not token:raise ValueError('Informe a credencial do agente.')
        return RemoteServices(agent_url.get(),token,ca_file.get())
    def complete_tasks():
        try:
            while True:task_queue.get_nowait()()
        except queue.Empty:pass
        root.after(100,complete_tasks)
    root.after(100,complete_tasks)
    def remote_task(action):
        nonlocal remote_busy
        if remote_busy:return
        try:client=remote_client()
        except Exception as error:messagebox.showerror('Escritura',str(error),parent=root);return
        selected=service_tree.selection()
        if action!='status' and not selected:messagebox.showinfo('Escritura','Selecione um serviço desta instalação.',parent=root);return
        ident=selected[0] if selected else None
        if action in ('stop','restart') and not messagebox.askyesno('Escritura','Esta operação afeta os usuários conectados. Executar no serviço selecionado?',parent=root):return
        remote_busy=True
        state.set('Consultando instalação remota…')
        def work():
            try:
                if action=='logs':
                    detail=client.logs(ident)
                    result=client.services()
                else:
                    if action!='status':client.command(ident,action)
                    result=client.services();detail=''
                def done():
                    nonlocal remote_busy
                    service_tree.delete(*service_tree.get_children())
                    for item in result['services']:service_tree.insert('', 'end',iid=item['id'],values=(item['name'],item['state'],item['image']))
                    if ident and service_tree.exists(ident):service_tree.selection_set(ident)
                    state.set('Instalação remota conectada: '+result['installation'])
                    log('Agente: '+action+' concluído.')
                    if detail:log(detail);tabs.select(logs)
                    if tray and action in ('start','stop','restart'):tray.notify('Comando remoto concluído: '+action)
                    remote_busy=False
                task_queue.put(done)
            except Exception as error:
                message=str(error)
                def failed():
                    nonlocal remote_busy
                    remote_busy=False;state.set('Instalação remota indisponível');log(message)
                    messagebox.showerror('Escritura',message,parent=root)
                task_queue.put(failed)
        threading.Thread(target=work,daemon=True,name='EscrituraAgent').start()
    def save_remote():
        try:
            values={'agent_url':validate_url(agent_url.get()),'portal_url':validate_url(portal_url.get()),'ca_file':ca_file.get()}
            if ca_file.get() and not Path(ca_file.get()).is_file():raise ValueError('Arquivo da CA não encontrado.')
            if credential.get():save_token(home/'agent.dpapi',credential.get());credential.set('')
            temporary=remote_config_file.with_suffix('.tmp');temporary.write_text(json.dumps(values,indent=2),encoding='utf-8');temporary.replace(remote_config_file)
            log('Conexão salva. Credencial protegida pelo Windows para este usuário.')
        except Exception as error:messagebox.showerror('Escritura',str(error),parent=root)
    def open_remote():
        try:webbrowser.open(validate_url(portal_url.get()))
        except ValueError as error:messagebox.showerror('Escritura',str(error),parent=root)
    remote_actions=ttk.Frame(remote_tab);remote_actions.grid(row=9,column=0,columnspan=3,sticky='w')
    ttk.Button(remote_actions,text='Salvar conexão',command=save_remote).pack(side='left',padx=(0,6))
    ttk.Button(remote_actions,text='Abrir portal remoto',command=open_remote).pack(side='left')
    commands=ttk.Frame(remote_tab);commands.grid(row=11,column=0,columnspan=3,sticky='w')
    for title,action in [('Consultar','status'),('Iniciar','start'),('Parar','stop'),('Reiniciar','restart'),('Logs','logs')]:ttk.Button(commands,text=title,command=lambda a=action:remote_task(a)).pack(side='left',padx=(0,5))
    def hide(event=None):
        if tray and tray.available: root.withdraw()
        else: root.iconify()
    def quit_app():
        backend.stop()
        if tray: tray.close()
        root.destroy()
    callbacks = {1: ('Abrir administração', show), 2: ('Abrir portal', portal), 3: ('Iniciar serviço', start), 4: ('Interromper serviço', stop), 5: ('Reiniciar serviço', restart), 6: ('Sair do Escritura', quit_app), 7: ('Consultar Docker remoto', lambda: remote_task('status')), 8: ('Abrir portal remoto', open_remote)}
    try: tray = Tray(root, icon, callbacks, identity)
    except Exception: log('Área de notificação indisponível; use a janela de administração.')
    ttk.Button(outer, text='Sair do Escritura', command=quit_app).pack(anchor='e', pady=(12, 0))
    root.protocol('WM_DELETE_WINDOW', hide); root.bind('<Escape>', hide)
    if automatic.get() or args.database: root.after(100, start)
    if args.background: root.after(500, hide)
    stop_event = None
    if event_name := os.environ.get('ESCRITURA_SMOKE_STOP_EVENT'):
        kernel.OpenEventW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]; kernel.OpenEventW.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        stop_event = kernel.OpenEventW(0x100000, False, event_name)
        def check_stop():
            if stop_event and kernel.WaitForSingleObject(stop_event, 0) == 0: quit_app()
            else: root.after(100, check_stop)
        root.after(100, check_stop)
    if status_file := os.environ.get('ESCRITURA_SMOKE_STATUS_FILE'):
        kernel.GetConsoleWindow.restype = w.HWND
        def smoke_status():
            Path(status_file).write_text(json.dumps({'tk_window': bool(root.winfo_exists()), 'tray_window': bool(tray and tray.window), 'tray_available': bool(tray and tray.available), 'console_window': bool(kernel.GetConsoleWindow()), 'frozen': bool(getattr(sys, 'frozen', False)), 'backend_running': backend.running}), encoding='utf-8')
        root.after(1800, smoke_status)
    try: root.mainloop()
    finally:
        backend.stop()
        if stop_event: kernel.CloseHandle(stop_event)
        kernel.CloseHandle(mutex)
