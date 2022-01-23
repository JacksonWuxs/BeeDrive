from .core.Proxy import HostProxy


def proxy_forever(port):
    task = HostProxy(int(port)) 
    task.start()
    task.join()
