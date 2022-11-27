mkdir -p $1/data
mkdir -p $1/code
mkdir -p $1/output
mkdir -p $1/nevents
rm -f $1/nevents/*
chmod -R 777 $1
echo "pip install vector hist mplhep coffea" > $1/code/commands.sh
echo "git clone https://github.com/cms-opendata-workshop/workshop2022-lesson-ttbarljetsanalysis-payload.git" >> $1/code/commands.sh
echo "cd workshop2022-lesson-ttbarljetsanalysis-payload" >> $1/code/commands.sh
echo "cp $1/code/ntuples.json ." >> $1/code/commands.sh
echo "python coffeaAnalysis_ttbarljets.py" >> $1/code/commands.sh
echo "mv *root $1" >> $1/code/commands.sh
cat $1/code/commands.sh