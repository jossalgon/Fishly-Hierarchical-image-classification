#!/bin/bash
  
NAME=fishly-api

echo "Eliminando contenedores antiguos"
ContainerId2=`docker ps -qa --filter "name=$NAME"`
if [ -n "$ContainerId2" ]
then
        echo "Stopping and removing existing $NAME container"
        docker stop $ContainerId2
        docker rm -v $ContainerId2
fi

echo "[DOCKER]"
docker run -d --name $NAME \
        -v "/home/jossalgon/workspace/fishly-api2/":/myapp \
        -v "/media/Toshiba/ML/fishes/weights/":/myapp/models \
        -w /myapp \
    --expose=5000 \
    -e VIRTUAL_HOST="fishly.duckdns.org, www.fishly.duckdns.org" \
    -e VIRTUAL_PORT=5000 \
    -e "LETSENCRYPT_HOST=fishly.duckdns.org, www.fishly.duckdns.org" \
    -e "LETSENCRYPT_EMAIL=joseluis25sg@gmail.com" \
    floydhub/pytorch:1.6.0-py3.56 \
    bash -c "pip install -r requirements.txt && python3 app.py"
echo "[/DOCKER]"

echo "Aplicación desplegada"
