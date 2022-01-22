from time import localtime, asctime
from sys import stdout


PROCESS_BAR_PATTERN = '\r{}: {} {:4.1f}% | {} | {}'
OUTPUTS = [stdout]


def printf(msg="", end="\n", flush=False):
    for output in OUTPUTS:
        print(msg, end=end, file=output, flush=flush)
        

def callback_info(msg):
    if "\n" in msg:
        msg = "\n" + msg
    info = '[%s] INFO: %s' % (asctime(localtime()), msg)
    printf(info)
    return info


def callback_processbar(percent, task, speed, spent):
    if speed < 1048576:
        speed_flag = '%.2fKB/s' % (speed / 1024)
    elif speed < 1073741824:
        speed_flag = '%.2fMB/s' % (speed / 1048576)
    else:
        speed_flag = '%.2fGB/s' % (speed / 1073741824)

    spent_flag = ''
    spent = max(spent / (percent + 0.000001) - spent, 0.000001)
    if spent >= 3600:
        spent_flag += "%2.0f" % (spent // 3600) + ':'
        spent = spent % 3600
    if spent >= 60:
        spent_flag += "%2.0f" % (spent // 60) + ':'
        spent = spent % 60
    spent_flag += '%2.0f' % spent
    
    bar = PROCESS_BAR_PATTERN.format(task, '=' * int(percent * 50) + " " * int((1.0 - percent) * 50),
                                     percent*100, speed_flag, spent_flag)
    printf(bar, end="", flush=True)
    return bar


def callback_flush():
    printf()


def callback_error(msg, code, name=""):
    info = '[%s] ERROR-%d: %s  -> %s\r' % (asctime(localtime()), code, msg, name)
    printf(info)
    return info

