STAGE_INIT = "Init"
STAGE_PRE = "Prepare"
STAGE_RUN = "Run"
STAGE_STOP = "Stop"
STAGE_DONE = "Finished"
STAGE_FAIL = "Fail"
STAGE_RETRY = "Retry"

END_PATTERN = b'___@@@___'

TCP_BUFF_SIZE = 65535    # 64 KB
DISK_BUFF_SIZE = 65535   # 64 KB

__version__ = "0.1.0"
__date__ = "2022.01.22"

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
