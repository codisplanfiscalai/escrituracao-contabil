"""Limits applied before loading native decoders; failures must stop the worker."""
import ctypes
import sys

MEMORY_BYTES = 768 * 1024 * 1024
OUTPUT_BYTES = 150 * 1024 * 1024
_JOB = None


def apply_limits(seconds):
    global _JOB
    if sys.platform != 'win32':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (seconds,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_BYTES,) * 2)
        return
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                    ('flags', w.DWORD), ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t),
                    ('processes', w.DWORD), ('affinity', ctypes.c_size_t),
                    ('priority', w.DWORD), ('scheduling', w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
    class Extended(ctypes.Structure):
        _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                    ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    kernel.SetInformationJobObject.restype = w.BOOL
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.AssignProcessToJobObject.restype = w.BOOL
    kernel.GetCurrentProcess.restype = w.HANDLE
    handle = kernel.CreateJobObjectW(None, None)
    if not handle: raise OSError('Job de leitura indisponível')
    limits = Extended()
    # PROCESS_TIME | ACTIVE_PROCESS | PROCESS_MEMORY | KILL_ON_JOB_CLOSE.
    limits.basic.flags = 0x2 | 0x8 | 0x100 | 0x2000
    limits.basic.process_time = seconds * 10_000_000
    limits.basic.processes = 1
    limits.process_memory = MEMORY_BYTES
    if not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise OSError('Não foi possível limitar o processo leitor')
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        raise OSError('Não foi possível isolar o processo leitor')
    _JOB = handle  # Keep open until process exit; never relax limits on failure.
