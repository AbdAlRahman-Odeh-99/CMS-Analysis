#sudo apt install docker.io
#sudo systemctl start docker
#docker pull cernopendata/cernopendata-client:0.3.0
#docker run cernopendata-client get-file-locations --recid $1 --protocol xrootd > $2/vol/files_$1.txt;
get-file-locations --recid $1 --protocol xrootd > $2/files_$1.txt;
