try:
    import sys
    from itertools import chain
    from datetime import datetime
    from datetime import timedelta
    import json
    from airflow import DAG
    from airflow.operators.python_operator import PythonOperator
    from airflow.operators.bash_operator import BashOperator
    from airflow.operators.docker_operator import DockerOperator
    from airflow.utils.task_group import TaskGroup
    from docker.types import Mount 
    print("All Dag modules are ok ......")
except Exception as e:
    print("Error  {} ".format(e))

default_args = {
    "owner": "admin",
    'depends_on_past': False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2021, 9, 13),
}

recids = [24119, 24120, 19980, 19983, 19985, 19949, 19999, 19397, 19407, 19419, 19412, 20548]

dir_path = '/home/abd/airflow/CMS-Analysis'
vol_path = dir_path + '/vol'
shell_scripts_path = dir_path+'/shell-scripts/Bash'


############### BASH OPERATORS ###############

def pull_images_op():
    return BashOperator(
        task_id = "pull_images",
        bash_command=
        """
        docker pull ubuntu:latest
        docker pull cernopendata/cernopendata-client:0.3.0
        docker pull cmsopendata/cmssw_7_6_7-slc6_amd64_gcc493
        docker pull gitlab-registry.cern.ch/cms-cloud/python-vnc:latest
        """
    )

def prepare_op():
    return BashOperator(
        task_id = "prepare",
        bash_command=
        """
        docker run \
        --name ubuntu \
        --mount type=bind,source={dir_path},target={dir_path} \
        ubuntu:latest \
        bash {shell_scripts_path}/prepare-bash.sh {vol_path} && \
        docker stop ubuntu && \
        docker rm ubuntu
        """,
        env = {'dir_path':dir_path, 'shell_scripts_path':shell_scripts_path, 'vol_path':vol_path}
    )

def filelist_op(recid):
    filelist_operator = BashOperator(
        task_id = "filelist_{}".format(recid),
        bash_command =
        """
        docker run \
        --rm \
        --name cernopendata-client-{recid} \
        --mount type=bind,source={dir_path},target={dir_path} \
        cernopendata/cernopendata-client:0.3.0 \
        get-file-locations --recid {recid} --protocol xrootd > {vol_path}/files_{recid}.txt;
        """,
        env = {'dir_path':dir_path,'recid':str(recid), 'vol_path':vol_path}
    )

def runpoet_op(nFiles, recid, nJobs):
    runpoet_operator = BashOperator(
        task_id = "runpoet_{}".format(recid),
        bash_command=
        """
        if ! docker stop cmssw-{recid} && ! docker rm cmssw-{recid}; then
            echo "some_command returned an error"
        else
            docker stop cmssw-{recid} && docker rm cmssw-{recid}
        fi && \
        docker run \
        --name cmssw-{recid} \
        --mount type=bind,source={dir_path},target={dir_path} \
        cmsopendata/cmssw_7_6_7-slc6_amd64_gcc493 \
        bash {shell_scripts_path}/runpoet-bash.sh {vol_path} {nFiles} {recid} {nJobs} && \
        docker stop cmssw-{recid} && \
        docker rm cmssw-{recid}
        """,
        env = {'dir_path':dir_path, 'shell_scripts_path':shell_scripts_path, 'vol_path':vol_path, 'recid':str(recid), 'nFiles':str(nFiles), 'nJobs':str(nJobs)}
    )

def flattentrees_op(recid):
    flattentrees_operator = BashOperator(
        task_id = "flattentrees_{}".format(recid),
        bash_command=
        """
        docker run \
        -i \
        -d \
        --name python-{recid} \
        --mount type=bind,source={dir_path},target={dir_path} \
        gitlab-registry.cern.ch/cms-cloud/python-vnc && \
        docker start python-{recid} && \
        docker exec python-{recid} bash {shell_scripts_path}/flattentrees-bash.sh {vol_path} {recid} && \
        docker stop python-{recid} && \
        docker rm python-{recid}
        """
        ,
        env = {"dir_path":dir_path, "shell_scripts_path":shell_scripts_path, "vol_path":vol_path, "recid":str(recid)}
    )

def prepare_coffea_op():
    prepare_coffea_operator = BashOperator(
        task_id = "prepare_coffea",
        bash_command=
        """
        docker run \
        -i \
        -d \
        --name prepare-coffea \
        --mount type=bind,source={dir_path},target={dir_path} \
        gitlab-registry.cern.ch/cms-cloud/python-vnc && \
        docker start prepare-coffea && \
        docker exec prepare-coffea bash {shell_scripts_path}/preparecoffea-bash.sh {vol_path} && \
        docker stop prepare-coffea && \
        docker rm prepare-coffea
        """
        ,
        env = {"dir_path":dir_path, "shell_scripts_path":shell_scripts_path, "vol_path":vol_path}
    )

def run_coffea_op():
    run_coffea_operator = BashOperator(
        task_id = "run_coffea",
        bash_command=
        """
        docker run \
        -i \
        -d \
        --name run-coffea \
        --mount type=bind,source={dir_path},target={dir_path} \
        gitlab-registry.cern.ch/cms-cloud/python-vnc && \
        docker start run-coffea && \
        docker exec run-coffea bash {vol_path}/code/commands.sh && \
        docker stop run-coffea && \
        docker rm run-coffea
        """
        ,
        env = {"dir_path":dir_path, "vol_path":vol_path}
    )


with DAG(dag_id="Docker-CMS-Open-Data-Analysis", schedule_interval="@daily", default_args=default_args, catchup=False) as dag:
    
    pull_operator = pull_images_op()
    prepare_operator = prepare_op()

    with TaskGroup(group_id='filelist_group') as filelist_group:
        for recid in recids:
            filelist_op(recid)
    
    with TaskGroup(group_id='runpoet_group') as runpoet_group:
        for recid in recids:
            runpoet_op(2, recid, 1)
    
    with TaskGroup(group_id='flattentrees_group') as flattentrees_group:
        for recid in recids:
            flattentrees_op(recid)
    
    with TaskGroup(group_id='prepare_coffea_group') as prepare_coffea_group:
        prepare_coffea_op()
    
    with TaskGroup(group_id='run_coffea_group') as run_coffea_group:
        run_coffea_op()
    
    pull_operator >> prepare_operator >> filelist_group >> runpoet_group >> flattentrees_group >> prepare_coffea_group >> run_coffea_group
    




'''
############### DOCKER OPERATORS ###############

############### PREPARE DOCKER ###############
def prepare_op():
    return DockerOperator(
        task_id = "prepare",
        image='ubuntu:latest',
        api_version='auto',
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        command="bash {}/shell-scripts/prepare.sh {} ".format(dir_path, dir_path),
        mounts=[Mount(source = dir_path, target = dir_path, type='bind')]
    )

############### FILELIST DOCKER ###############
def filelist_op(recid):
    filelist_operator = DockerOperator(
        task_id = "filelist_{}".format(recid),
        image='cernopendata/cernopendata-client:0.3.0',
        api_version='auto',
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        #command="/bin/bash {}/filelist.sh {} {} ".format(shell_scipts_path, recid, vol_path),
        #command= "/bin/bash get-file-locations --recid {} --protocol xrootd > {}/files_{}.txt;".format(recid, vol_path, recid),
        command= "/bin/bash pwd",
        mounts=[Mount(source = dir_path, target = dir_path, type='bind')]
    )

############### RUNPOET DOCKER ###############
def runpoet_op(nFiles, recid, nJobs):
    runpoet_operator = DockerOperator(
        task_id = "runpoet_{}".format(recid),
        image='cmsopendata/cmssw_7_6_7-slc6_amd64_gcc493',
        api_version='auto',
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        command="/bin/bash {}/runpoet.sh {} {} {} {} ".format(shell_scipts_path, vol_path, nFiles, recid, nJobs),
        mounts=[Mount(source = dir_path, target = dir_path, type='bind')]
    )

############### FLATTENTREES DOCKER ###############
def flattentrees_op(recid):
    flattentrees_operator = DockerOperator(
        task_id = "flattentrees_{}".format(recid),
        image='gitlab-registry.cern.ch/cms-cloud/python-vnc:latest',
        api_version='auto',
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        command="/bin/bash {}/flattentrees.sh {} {} ".format(shell_scipts_path, vol_path, recid),
        mounts=[Mount(source = dir_path, target = dir_path, type='bind')]
    )

############### PREPARE COFFEA DOCKER ###############
def prepare_coffea_op():
    prepare_coffea_operator = DockerOperator(
        task_id = "prepare_coffea",
        image='gitlab-registry.cern.ch/cms-cloud/python-vnc:latest',
        api_version='auto',
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        #command="/bin/bash {}/preparecoffea.sh {} ".format(shell_scipts_path,vol_path),
        command="bash {}/preparecoffea.sh {}".format(shell_scipts_path,vol_path),
        mounts=[Mount(source = dir_path, target = dir_path, type='bind')]
    )

############### RUN COFFEA DOCKER ###############
def run_coffea_op():
    run_coffea_operator = DockerOperator(
        task_id = "run_coffea",
        image='gitlab-registry.cern.ch/cms-cloud/python-vnc:latest',
        api_version='auto',
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        command="/bin/bash {}/code/commands.sh ".format(vol_path),
        mounts=[Mount(source = dir_path, target = dir_path, type='bind')]
    )
'''