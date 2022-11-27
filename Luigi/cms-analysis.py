import luigi
#from luigi.mock import MockFile
import subprocess

dir_path = "/home/abd/Desktop/Work/Luigi/CMS-Analysis"
vol_path = dir_path + "/vol"
shell_scripts_path = dir_path + "/shell-scripts/Bash"

list_of_tasks = []
recids = [24119, 24120, 19980, 19983, 19985, 19949, 19999, 19397, 19407, 19419, 19412, 20548]

prepare_directory_outputs = [
    vol_path + "/code",
    vol_path + "/code/commands.sh",
    vol_path + "/data",
    vol_path + "/nevents",
    vol_path + "/output",
]
#----------------------------------- Pull Images -----------------------------------
def pullCommand():
    return f"""
        docker pull ubuntu:latest
        docker pull cernopendata/cernopendata-client:0.3.0
        docker pull cmsopendata/cmssw_7_6_7-slc6_amd64_gcc493
        docker pull gitlab-registry.cern.ch/cms-cloud/python-vnc:latest
        echo "Done Pulling !">>{dir_path}/pull.txt
        """

class PullImages(luigi.Task):
    task_namespace = 'CMS-Analysis'
    
    def output(self):
        output_file = dir_path+"/pull.txt"
        return luigi.LocalTarget(output_file)
        #return MockFile("PullImages", mirror_on_stderr=True)

    def run(self):
        bashCommand = pullCommand()
        process = subprocess.Popen(bashCommand, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output, error = process.communicate()
        print("The command is: \n",bashCommand)
        print("The output is: \n",output.decode())
        print("Return Code:", process.returncode)
        if process.returncode and error:
            print("The error is: \n",error.decode())
    
#----------------------------------- Prepare -----------------------------------
def prepareCommand():
    return f"""
        docker run \
        --name ubuntu \
        --mount type=bind,source={dir_path},target={dir_path} \
        ubuntu:latest \
        bash {shell_scripts_path}/prepare-bash.sh {vol_path} && \
        docker stop ubuntu && \
        docker rm ubuntu
        """

class PrepareDirectory(luigi.Task):
    task_namespace = 'CMS-Analysis'

    def requires(self):
        return PullImages()

    def output(self):
        output_files = []
        for file in prepare_directory_outputs:
            output_files.append(luigi.LocalTarget(file))
        return output_files

    def run(self):
        bashCommand = prepareCommand()
        process = subprocess.Popen(bashCommand, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output, error = process.communicate()
        print("The command is: \n",bashCommand)
        print("The output is: \n",output.decode())
        print("Return Code:", process.returncode)
        if process.returncode and error:
            print("The error is: \n",error.decode())

#----------------------------------- Filelist -----------------------------------
def fileListCommand(recid):
    return f"""
        docker run \
        --rm \
        --name cernopendata-client-{recid} \
        --mount type=bind,source={dir_path},target={dir_path} \
        cernopendata/cernopendata-client:0.3.0 \
        get-file-locations --recid {recid} --protocol xrootd > {vol_path}/files_{recid}.txt;
        """

class FileList(luigi.Task):
    task_namespace = 'CMS-Analysis'
    recid = luigi.IntParameter()

    def requires(self):
        return PrepareDirectory()

    def output(self):
        output_file = f"{vol_path}/files_{self.recid}.txt"
        return luigi.LocalTarget(output_file)

    def run(self):
        bashCommand = fileListCommand(self.recid)
        process = subprocess.Popen(bashCommand, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output, error = process.communicate()
        print("The command is: \n",bashCommand)
        print("The output is: \n",output.decode())
        print("Return Code:", process.returncode)
        if process.returncode and error:
            print("The error is: \n",error.decode())

#----------------------------------- Runpoet -----------------------------------
def runpoetCommand(nFiles, recid, nJobs):
    return f"""
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
        """

class Runpoet(luigi.Task):
    task_namespace = 'CMS-Analysis'
    recid = luigi.IntParameter()

    def requires(self):
        filelist_list = []
        for recid in recids:
            filelist_list.append(FileList(recid=recid))
        return filelist_list
    
    def output(self):
        output_file = f"{vol_path}/output/{self.recid}/myoutput.root"
        return luigi.LocalTarget(output_file)

    def run(self):
        bashCommand = runpoetCommand(2, self.recid, 1)
        process = subprocess.Popen(bashCommand, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output, error = process.communicate()
        print("The command is: \n",bashCommand)
        print("The output is: \n",output.decode())
        print("Return Code:", process.returncode)
        if process.returncode and error:
            print("The error is: \n",error.decode())

#----------------------------------- Flattentrees -----------------------------------
def flattentreesCommand(recid):
    return f"""
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

class Flattentrees(luigi.Task):
    task_namespace = 'CMS-Analysis'
    recid = luigi.IntParameter()

    def requires(self):
        runpoet_list = []
        for recid in recids:
            runpoet_list.append(Runpoet(recid=recid))
        return runpoet_list
    
    def output(self):
        output_file = f"{vol_path}/output/{self.recid}/myoutput_merged.root"
        return luigi.LocalTarget(output_file)

    def run(self):
        bashCommand = flattentreesCommand(self.recid)
        process = subprocess.Popen(bashCommand, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output, error = process.communicate()
        print("The command is: \n",bashCommand)
        print("The output is: \n",output.decode())
        print("Return Code:", process.returncode)
        if process.returncode and error:
            print("The error is: \n",error.decode())

#----------------------------------- Prepare Coffea -----------------------------------
def prepareCoffeaCommand():
    return f"""
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

class PrepareCoffea(luigi.Task):
    task_namespace = 'CMS-Analysis'

    def requires(self):
        flattentrees_list = []
        for recid in recids:
            flattentrees_list.append(Flattentrees(recid=recid))
        return flattentrees_list
    
    def output(self):
        output_file = f"{vol_path}/code/ntuples.json"
        return luigi.LocalTarget(output_file)

    def run(self):
        bashCommand = prepareCoffeaCommand()
        process = subprocess.Popen(bashCommand, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output, error = process.communicate()
        print("The command is: \n",bashCommand)
        print("The output is: \n",output.decode())
        print("Return Code:", process.returncode)
        if process.returncode and error:
            print("The error is: \n",error.decode())
    
#----------------------------------- Run Coffea -----------------------------------
def runCoffeaCommand():
    return f"""
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

class RunCoffea(luigi.Task):
    task_namespace = 'CMS-Analysis'

    def requires(self):
        return PrepareCoffea()
    
    def output(self):
        output_file = f"{vol_path}/histograms.root"
        return luigi.LocalTarget(output_file)

    def run(self):
        bashCommand = runCoffeaCommand()
        process = subprocess.Popen(bashCommand, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output, error = process.communicate()
        print("The command is: \n",bashCommand)
        print("The output is: \n",output.decode())
        print("Return Code:", process.returncode)
        if process.returncode and error:
            print("The error is: \n",error.decode())

if __name__ == '__main__':
    #------------------------------------ COMBINING START ------------------------------------
    list_of_tasks.append(RunCoffea())
    luigi.build(list_of_tasks, workers = 4)
    #------------------------------------ COMBINING END ------------------------------------