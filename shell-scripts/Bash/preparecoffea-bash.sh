wget https://raw.githubusercontent.com/cms-opendata-analyses/PhysObjectExtractorTool/odws2022-ttbaljets-prod/PhysObjectExtractor/scripts/ntuples-gen.py
cp $1/nevents/nevts_recid.txt .
python ntuples-gen.py
cat ntuples.json
mv ntuples.json $1/code