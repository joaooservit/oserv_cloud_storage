docker build -t ocs-centos7 -f Dockerfile.centos7 .
sudo docker run --name ocs_temp_container ocs
sudo docker cp ocs_temp_container:/app/dist/ocs $(pwd)/dist/ocs
sudo docker rm ocs_temp_container


docker build -t ocs-windows -f Dockerfile.windows .
