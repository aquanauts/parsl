#  _*_  coding : utf-8    _*_
#
#  Parsl DAG Application for strategy performance
#  based on app_dag_zhuzhao.py
#   Author: Takuya Kurihana 
#
import os
import time
import argparse
import numpy as np
import psutil
import parsl
from parsl import *
from parsl.config import Config
from parsl.executors import ThreadPoolExecutor
from parsl.executors import HighThroughputExecutor
from parsl.providers import LocalProvider
from parsl.channels  import LocalChannel
from parsl.launchers import SingleNodeLauncher
from parsl.addresses import address_by_hostname
from parsl.channels  import SSHChannel
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher
import logging
from parsl.app.app import python_app

# Argument settings
p = argparse.ArgumentParser()
# Executor option
p.add_argument(
    "--executor",
    help="executor option for configuration setting ",
    type=str,
    default='HighThroughput_Slurm'
)
# Strategy option
p.add_argument(
    "--strategy",
    help="strategy option for configuration setting ",
    type=str,
    default='simple'
)
# outputfile directory
p.add_argument(
    "--ofiledir",
    help="output npy-filename directory ",
    type=str,
    default=os.getcwd()
)
# outputfilename
p.add_argument(
    "--oname",
    help="output npy-filename option ",
    type=str,
    default='default'
)
args = p.parse_args()
print('Argparse:  --executor='+args.executor, flush=True)


# Here we can add htex_strategy for option
# config
if args.executor == 'ThreadPool':
  config = Config(
      executors=[ThreadPoolExecutor(
          #label='threads',
          label='htex_local',
          max_threads=5)
      ],
  )
elif args.executor == 'HighThroughput_Local':
  config = Config(
      executors=[
          HighThroughputExecutor(
            label="htex_local",
            cores_per_worker=1,
            provider=LocalProvider(
              channel=LocalChannel(),
              init_blocks=1,
              max_blocks=1,
              # tasks_perss_node=1,  # For HighThroughputExecutor, this option sho<
              launcher=SingleNodeLauncher(),
            ),
        )
    ],
    #strategy='htex_aggressive',
    #strategy='htex_totaltime',
    #strategy='simple',
    strategy=args.strategy,
  )
elif args.executor == 'HighThroughput_Slurm':
  config = Config(
    executors=[
        HighThroughputExecutor(
            label="midway_htex",
            cores_per_worker=1,
            address=address_by_hostname(),
            provider=SlurmProvider(
                'broadwl',    # machine name on midway
                launcher=SrunLauncher(),
                scheduler_options='#SBATCH --mem-per-cpu=16000 ',
                ###scheduler_options='#SBATCH --exclusive',
                worker_init='module load Anaconda3/5.0.0.1; source activate parsl-dev',
                init_blocks=1,
                max_blocks=1,
                nodes_per_block=1,
                # tasks_per_node=1,  # For HighThroughputExecutor, this option sho<
                parallelism=1.0,
                walltime='12:00:00',
            ),
        )
    ],
    #strategy='htex_aggressive',
    #strategy='htex_totaltime',
    #strategy='simple',
    strategy=args.strategy,
  )

# TODO: 
#try:
#except:
#  raise NameError("Invalid parsed argument")  

# Load config
print(config)
dfk = parsl.load(config)


@App('python', dfk)
def sleeper(dur=5):
    import time
    time.sleep(dur)


@App('python', dfk)
def cpu_stress(dur=30):
    import time
    s = 0
    start = time.time()
    for i in range(10**8):
        s += i
        if time.time() - start >= dur:
            break
    return s

@python_app
def inc(inputs=[], init_time=0):
    import time
    import psutil
    import numpy as np
    start = time.time()
    #sleep_duration = 600.0
    sleep_duration = 10
    _inputs = np.asarray(inputs)
    mems = [] #_inputs[0].tolist()
    cpus = [] #_inputs[1].tolist()
    times =[]
    x = 0
    while True:
        x += 1
        end = time.time()
        #if (end - start) % 10 == 0:
        if (end - start) % 2 == 0:
            mems += [psutil.virtual_memory().percent]
            cpus += [psutil.cpu_percent()]
            times += [time.time() - init_time ]
        if end - start >= sleep_duration:
            break
    mems += [psutil.virtual_memory().percent]
    cpus += [psutil.cpu_percent()]
    times += [time.time() - init_time ]
    return [mems, cpus, times]

@python_app
def add_inc(inputs=[], init_time=0):
    import time
    import psutil
    import numpy as np
    start = time.time()
    #sleep_duration = 300.0
    sleep_duration = np.random.gumbel(20, 0.05)
    res = 0
    _inputs = np.asarray(inputs)
    mems = [] # _inputs[0].tolist()
    cpus = [] # _inputs[1].tolist()
    times = []
    while True:
        res += 1
        end = time.time()
        #if (end - start) % 10 == 0:
        if (end - start) % 2 == 0:
            mems += [psutil.virtual_memory().percent]
            cpus += [psutil.cpu_percent()]
            times += [time.time() - init_time ]
        if end - start >= sleep_duration:
            break
    mems += [psutil.virtual_memory().percent]
    cpus += [psutil.cpu_percent()]
    times += [time.time() - init_time ]
    return  [mems, cpus, times]

if __name__ == "__main__":

    #total = 10 
    total = 40
    #half = int(total / 2)
    #one_third = int(total / 3)
    #two_third = int(total / 3 * 2)
    mems = [psutil.virtual_memory().percent]
    cpus = [psutil.cpu_percent()]
    inputs = [mems, cpus]
    init_time = time.time()   # initial time for runnnig
    futures_0 = inc(inputs, init_time)
    _outputs1 = [ futures_0.result() ]
    futures_1 = [ add_inc(futures_0, init_time = init_time) for i in range(total) ]
    _outputs2 = [ i.result() for i in futures_1 ]
    futures_2 = add_inc(futures_1[0], init_time = init_time)
    _outputs3 = [ futures_2.result() ]
    #_outputs1 = [i.result() for i in futures_1]
    #futures_2 = [add_inc(inputs=futures_1, init_time=init_time)]  
    
    print(futures_2.result())
    print("Done")

    # save output into file
    cdir = args.ofiledir
    try:
      if  cdir is not 'not-specify': 
        print("  ### Outputdir : %s " % cdir , flush=True )
    except:
      cdir = os.getcwd()
    
    for idx ,  iout in enumerate([_outputs1, _outputs2, _outputs3]) :
        _iout = np.asarray(iout)
        _idx = idx + 1
        np.save(cdir+'/'+"outputs_app2-"+str(_idx)+"_slurm-"+args.oname, _iout)