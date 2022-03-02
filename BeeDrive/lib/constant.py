import re


STAGE_INIT = "Init"
STAGE_PRE = "Prepare"
STAGE_RUN = "Run"
STAGE_STOP = "Stop"
STAGE_DONE = "Finished"
STAGE_FAIL = "Fail"
STAGE_RETRY = "Retry"

END_PATTERN = b'___@@@___'
END_PATTERN_COMPILE = re.compile(END_PATTERN)

TCP_BUFF_SIZE = 65535    # 64 KB
DISK_BUFF_SIZE = 262140  # 256 KB
RETRY_WAIT = 10          # 1 min

VERSION = "0.3.5.1"
DATE = 20220228

DEATH = 0
ALIVE = 1
PAUSE = 2    

IsFull = 0     # Whether reach the limitation of the manager
NewTask = 1    # Launch a new task and the manager will create a new worker
KillTask = 2   # Totally stop a working task
Update = 3     # Update latest status of each workers
Stop = 4       # Stop all workers and kill the manager
Done = 5       # A specific task is done

IV = b'0123456789123456'
BLOCK_SIZE = 256
MAX_CLIENT_SIZE = 16
