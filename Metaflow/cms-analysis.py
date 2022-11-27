#from wsgiref.handlers import BaseCGIHandler
from metaflow import FlowSpec, step, card
import subprocess
import os

os.environ.update({"METAFLOW_RUN_MAX_WORKERS": "4"})
dir_path = "/home/abd/Desktop/Work/Metaflow/CMS-Analysis"
vol_path = dir_path + "/vol"
shell_scripts_path = dir_path + "/shell-scripts/Bash"

recids = [24119, 24120, 19980, 19983, 19985, 19949, 19999, 19397, 19407, 19419, 19412, 20548]

#----------------------------------- Pull Images -----------------------------------
def pullCommand():
    return """
        docker pull ubuntu:latest
        docker pull cernopendata/cernopendata-client:0.3.0
        docker pull cmsopendata/cmssw_7_6_7-slc6_amd64_gcc493
        docker pull gitlab-registry.cern.ch/cms-cloud/python-vnc:latest
        """

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
        

#----------------------------------- Run Bash -----------------------------------
def run_bash(bashCommand):
    process = subprocess.Popen(bashCommand, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    output, error = process.communicate()
    print("The command is: \n",bashCommand)
    print("The output is: \n",output.decode())
    print("Return Code:", process.returncode)
    if process.returncode and error:
        print("The error is: \n",error.decode())


class CMS_Analysis(FlowSpec):
    
    @card
    @step
    def start(self):
        print("Start Flow")
        self.next(self.pull_images)
    
    @card
    @step
    def pull_images(self):
        bashCommand = pullCommand()
        run_bash(bashCommand)
        self.next(self.prepare_directory)

    @card
    @step
    def prepare_directory(self):
        bashCommand = prepareCommand()
        run_bash(bashCommand)
        self.recids = recids
        self.next(self.file_list, foreach="recids")
    
    @card
    @step
    def file_list(self):
        self.recid = self.input
        bashCommand = fileListCommand(self.recid)
        run_bash(bashCommand)
        self.next(self.file_list_join)

    @card
    @step
    def file_list_join(self, inputs):        
        self.next(self.file_list_runpoet_link)
    
    @card
    @step
    def file_list_runpoet_link(self):        
        self.recids = recids
        self.next(self.runpoet, foreach="recids")

    @card
    @step
    def runpoet(self):
        self.recid = self.input
        bashCommand = runpoetCommand(2, self.recid, 1)
        run_bash(bashCommand)
        self.next(self.runpoet_join)
    
    @card
    @step
    def runpoet_join(self, inputs):        
        self.next(self.runpoet_flattentrees_link)
    
    @card
    @step
    def runpoet_flattentrees_link(self):        
        self.recids = recids
        self.next(self.flattentrees, foreach="recids")

    @card
    @step
    def flattentrees(self):
        self.recid = self.input
        bashCommand = flattentreesCommand(self.recid)
        run_bash(bashCommand)
        self.next(self.flattentrees_join)
    
    @card
    @step
    def flattentrees_join(self, inputs):        
        self.recids = recids
        self.next(self.preparecoffea)

    @card
    @step
    def preparecoffea(self):
        bashCommand = prepareCoffeaCommand()
        run_bash(bashCommand)
        self.next(self.runcoffea)
    
    @card
    @step
    def runcoffea(self):
        bashCommand = runCoffeaCommand()
        run_bash(bashCommand)
        self.next(self.end)

    @card
    @step
    def end(self):
        print("End Flow")

if __name__ == '__main__':
    CMS_Analysis()

    '''
    @card
    @step
    def generate_operation(self):
        option = self.option
        jobnumber = self.input
        data = generate_data_generation(option, jobnumber)
        bashCommand = generate_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.merge_root_operation)

    @card
    @step
    def merge_root_operation(self,inputs):        
        self.merge_artifacts(inputs)
        option = self.option
        data = merge_root_data_generation(option)
        bashCommand = merge_root_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.merge_and_select_link)

    @card
    @step
    def merge_and_select_link(self):        
        option = self.option
        if(option['data_type'][2].isdigit()):
            data_type = 'mc'
        else:
            data_type = option['data_type']

        self.select_options = select_mc_options[data_type]

        self.next(self.select_operation, foreach="select_options")

    @card
    @step
    def select_operation(self):        
        option = self.option
        select_option = self.input
        data_type = option['data_type']
        data = select_data_genertion(option, select_option)
        bashCommand = select_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.join_select)
        
    @card
    @step
    def join_select(self,inputs):
        self.merge_artifacts(inputs)
        self.next(self.select_and_hist_link)

    @card   
    @step
    def select_and_hist_link(self):        
        option = self.option
        data_type = option['data_type']
        self.hist_options = []        
        if('data' in data_type):
            self.hist_options += histogram_options[data_type]
        else:
            self.hist_options.append(histogram_options[data_type])

        if('mc' in data_type):
            self.hist_options += histogram_options['shape']

        self.next(self.hist_operation, foreach='hist_options')
        
    @card
    @step
    def hist_operation(self):        
        option = self.option
        data_type = option['data_type']
        hist_option = self.input
        shapevar = hist_option['shapevar']
        variations = hist_option['variations']
        bashCommand = ''
        if(shapevar in ['shape_conv_up', 'shape_conv_dn']):
            data = hist_shape_data_genertion(self.option, shapevar, variations)
            bashCommand = hist_shape_GenerateCommand(data)
        else:
            if('data' in data_type):
                data = hist_weight_data_genertion(self.option, shapevar, variations, hist_option)
            else:
                data = hist_weight_data_genertion(self.option, shapevar, variations)
            
            bashCommand = hist_weight_GenerateCommand(data)

        run_bash(bashCommand)
        self.next(self.join_hists)
    
    @card
    @step
    def join_hists(self,inputs):
        self.merge_artifacts(inputs)
        option = self.option

        if('mc' in option['data_type']):
            data = merge_explicit_data_genertion(self.option, 'merge_hist_shape')
            bashCommand = merge_explicit_GenerateCommand(data)
            run_bash(bashCommand)
        
        data = merge_explicit_data_genertion(self.option, 'merge_hist_all')
        bashCommand = merge_explicit_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.final_join)

    @card
    @step
    def final_join(self, inputs):
        self.next(self.merge_hists)

    @card
    @step
    def merge_hists(self):
        data = merge_explicit_data_genertion()
        bashCommand = merge_explicit_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.makews)

    @card
    @step
    def makews(self):
        data_bkg_hists = base_dir + "/all_merged_hist.root"
        workspace_prefix = base_dir + "/results"
        xml_dir = base_dir + "/xmldir"
        data = makews_data_generation(data_bkg_hists, workspace_prefix, xml_dir)
        bashCommand = makews_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.plot)

    @card
    @step
    def plot(self):
        combined_model = base_dir + '/results_combined_meas_model.root'
        nominal_vals = base_dir + "/nominal_vals.yml"
        fit_results = base_dir + "/fit_results.yml"
        prefit_plot = base_dir + "/prefit.pdf"
        postfit_plot = base_dir + "/postfit.pdf"
        data = plot_data_generation(combined_model, nominal_vals, fit_results, prefit_plot, postfit_plot)
        bashCommand = plot_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.end)
        
    @card
    @step
    def end(self):
        print("End Flow")
'''


'''

list_of_tasks = []


plot_outputs = [
    base_dir + "/nominal_vals.yml",
    base_dir + "/fit_results.yml",
    base_dir + "/prefit.pdf",
    base_dir + "/postfit.pdf"
]




class BSM_Search(FlowSpec):
    
    @card
    @step
    def start(self):
        print("Start Flow")
        self.next(self.prepare_directory)

    @card
    @step
    def prepare_directory(self):
        bashCommand = generatePrepareCommand()
        run_bash(bashCommand)
        self.options = []
        for key in mc_options.keys():
            self.options.append(key)
        self.next(self.scatter_operation, foreach="options")
    
    @card
    @step
    def scatter_operation(self):
        self.option = mc_options[self.input]
        scatter(self.option)
        self.jobs = []
        for i in range (1,self.option['njobs']+1):
            self.jobs.append(str(i))
        self.next(self.generate_operation, foreach="jobs")

    @card
    @step
    def generate_operation(self):
        option = self.option
        jobnumber = self.input
        data = generate_data_generation(option, jobnumber)
        bashCommand = generate_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.merge_root_operation)

    @card
    @step
    def merge_root_operation(self,inputs):        
        self.merge_artifacts(inputs)
        option = self.option
        data = merge_root_data_generation(option)
        bashCommand = merge_root_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.merge_and_select_link)

    @card
    @step
    def merge_and_select_link(self):        
        option = self.option
        if(option['data_type'][2].isdigit()):
            data_type = 'mc'
        else:
            data_type = option['data_type']

        self.select_options = select_mc_options[data_type]

        self.next(self.select_operation, foreach="select_options")

    @card
    @step
    def select_operation(self):        
        option = self.option
        select_option = self.input
        data_type = option['data_type']
        data = select_data_genertion(option, select_option)
        bashCommand = select_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.join_select)
        
    @card
    @step
    def join_select(self,inputs):
        self.merge_artifacts(inputs)
        self.next(self.select_and_hist_link)

    @card   
    @step
    def select_and_hist_link(self):        
        option = self.option
        data_type = option['data_type']
        self.hist_options = []        
        if('data' in data_type):
            self.hist_options += histogram_options[data_type]
        else:
            self.hist_options.append(histogram_options[data_type])

        if('mc' in data_type):
            self.hist_options += histogram_options['shape']

        self.next(self.hist_operation, foreach='hist_options')
        
    @card
    @step
    def hist_operation(self):        
        option = self.option
        data_type = option['data_type']
        hist_option = self.input
        shapevar = hist_option['shapevar']
        variations = hist_option['variations']
        bashCommand = ''
        if(shapevar in ['shape_conv_up', 'shape_conv_dn']):
            data = hist_shape_data_genertion(self.option, shapevar, variations)
            bashCommand = hist_shape_GenerateCommand(data)
        else:
            if('data' in data_type):
                data = hist_weight_data_genertion(self.option, shapevar, variations, hist_option)
            else:
                data = hist_weight_data_genertion(self.option, shapevar, variations)
            
            bashCommand = hist_weight_GenerateCommand(data)

        run_bash(bashCommand)
        self.next(self.join_hists)
    
    @card
    @step
    def join_hists(self,inputs):
        self.merge_artifacts(inputs)
        option = self.option

        if('mc' in option['data_type']):
            data = merge_explicit_data_genertion(self.option, 'merge_hist_shape')
            bashCommand = merge_explicit_GenerateCommand(data)
            run_bash(bashCommand)
        
        data = merge_explicit_data_genertion(self.option, 'merge_hist_all')
        bashCommand = merge_explicit_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.final_join)

    @card
    @step
    def final_join(self, inputs):
        self.next(self.merge_hists)

    @card
    @step
    def merge_hists(self):
        data = merge_explicit_data_genertion()
        bashCommand = merge_explicit_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.makews)

    @card
    @step
    def makews(self):
        data_bkg_hists = base_dir + "/all_merged_hist.root"
        workspace_prefix = base_dir + "/results"
        xml_dir = base_dir + "/xmldir"
        data = makews_data_generation(data_bkg_hists, workspace_prefix, xml_dir)
        bashCommand = makews_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.plot)

    @card
    @step
    def plot(self):
        combined_model = base_dir + '/results_combined_meas_model.root'
        nominal_vals = base_dir + "/nominal_vals.yml"
        fit_results = base_dir + "/fit_results.yml"
        prefit_plot = base_dir + "/prefit.pdf"
        postfit_plot = base_dir + "/postfit.pdf"
        data = plot_data_generation(combined_model, nominal_vals, fit_results, prefit_plot, postfit_plot)
        bashCommand = plot_GenerateCommand(data)
        run_bash(bashCommand)
        self.next(self.end)
        
    @card
    @step
    def end(self):
        print("End Flow")



if __name__ == '__main__':
    BSM_Search()
'''