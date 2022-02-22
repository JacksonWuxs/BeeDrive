import sys
import time


PROCESS_BAR_PATTERN = '\r{}: {} {:4.1f}% | {} | {}'
LOGGING_LEVELS = {"DEBUG": 0, "WARN": 1, "INFO": 2, "ERROR": 3}
LOGGERS = {sys.stdout: 0}


def printf(msg="", end="\n", flush=False, verbals=0):
    for pipe, level in LOGGERS.items():
        if verbals >= level:
            print(msg, end=end, file=pipe, flush=flush)
        

def callback(msg, level="INFO"):
    level = level.upper()
    assert level in LOGGING_LEVELS
    info = '[%s] %s: %s' % (time.asctime(time.localtime()), level, msg)
    printf(info, verbals=LOGGING_LEVELS[level])
    return info


def processbar(percent, task, speed, spent):
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
    printf(bar, end="", flush=True, verbals=2)
    return bar


def flush():
    printf(verbals=max(LOGGING_LEVELS.values()))
