sudo chown $USER $1
sudo sed -i '$ d' /opt/cms/entrypoint.sh
source /opt/cms/entrypoint.sh
git clone -b odws2022-ttbaljets-prod https://github.com/cms-opendata-analyses/PhysObjectExtractorTool.git
cd PhysObjectExtractorTool/PhysObjectExtractor
scram b
echo $2
recid=$3
isData=False
if [[ $recid -eq 24119 ]] || [[ $recid -eq 24120 ]]; then isData=True; fi
itJobs=$(( $4 -1 ))
firstFile=$(( $2*$itJobs ))
lastFile=$(( firstFile + $2 ))
cmsRun python/poet_cfg_cloud.py $isData $lastFile $firstFile \"$1/files_$3.txt\"
tot=0
firstFile=$(( $firstFile + 2 ))
for ((i = $firstFile ; i <= $lastFile ; i++));
do
file=$(sed "${i}q;d" $1/files_$3.txt);
nevents=$(edmEventSize -v $file | grep Events |  awk '{print $NF}')
echo $nevents
tot=$(( tot + nevents ))
echo $tot
done
echo $recid $tot $1/output/$recid/myoutput_merged.root >> $1/nevents/nevts_recid.txt 
mkdir -p $1/output/$3
mv myoutput.root $1/output/$3/   # to be modified for nJobs > 1