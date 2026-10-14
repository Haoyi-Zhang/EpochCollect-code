"""Explicit host controls; portable runs never claim Linux memory enforcement."""
import os
import platform
import sys


def configure(portable=False):
    resource = None
    if sys.platform == 'linux':
        import resource
        cap = 3 * 1024**3
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
        allowed = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(allowed)})
        affinity = sorted(os.sched_getaffinity(0))
        if len(affinity) != 1:
            raise RuntimeError('one-lane affinity verification failed')
    elif portable and sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        word = ctypes.c_size_t
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(word), ctypes.POINTER(word)]
        kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, word]
        handle = kernel.GetCurrentProcess()
        process, system = word(), word()
        if not kernel.GetProcessAffinityMask(handle, ctypes.byref(process), ctypes.byref(system)):
            raise ctypes.WinError(ctypes.get_last_error())
        lane = process.value & -process.value
        if not lane or not kernel.SetProcessAffinityMask(handle, lane):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.GetProcessAffinityMask(handle, ctypes.byref(process), ctypes.byref(system)) or process.value != lane:
            raise RuntimeError('one-lane affinity verification failed')
        affinity = [lane.bit_length() - 1]
    else:
        raise ValueError('Linux controls required; --portable explicitly permits verified Windows affinity without an address-space cap')
    return ({'platform': platform.platform(), 'python': sys.version,
             'executable': sys.executable, 'optimization': sys.flags.optimize,
             'cpu_affinity': affinity, 'address_space_cap_bytes': 3 * 1024**3 if resource else None,
             'rss_measurement': 'Linux ru_maxrss KiB' if resource else 'not measured',
             'scope': 'owned offline Python scheduling, not network or GPU execution'}, resource)


def peak_rss(resource):
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None
