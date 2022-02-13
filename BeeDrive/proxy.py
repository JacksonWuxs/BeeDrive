from .core.Proxy import HostProxy


def proxy_forever(port, max_workers):
    task = HostProxy(int(port), int(max_workers)) 
    task.start()
    task.join()
