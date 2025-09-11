import multiprocessing
import os
import signal


def kill_proc(p: multiprocessing.Process):
    if not p:
        return
    if p.is_alive():
        p.terminate()
        p.join(0.1)
    if p.is_alive():
        try:
            os.kill(p.pid, signal.SIGKILL)
        except Exception:
            pass
        p.join(0.1)
    try:
        p.close()
    except Exception:
        pass
