pip install vector hist mplhep coffea
git clone https://github.com/cms-opendata-workshop/workshop2022-lesson-ttbarljetsanalysis-payload.git
cd workshop2022-lesson-ttbarljetsanalysis-payload
cp /home/abd/Desktop/Work/Snakemake/CMS-Analysis/vol/code/ntuples.json .
python coffeaAnalysis_ttbarljets.py
mv *root /home/abd/Desktop/Work/Snakemake/CMS-Analysis/vol
