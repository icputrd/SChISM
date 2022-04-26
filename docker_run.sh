#!/bin/bash

run="run"
bash="bash"
remove="rm"

name="schism_anau"
#image="tensorflow/tensorflow:latest-gpu-py3-jupyter"
image="schism"

#-u $(id -u ${USER}):$(id -g ${USER}) \

# -p "port OUTSIDE OF Container" : "port in container"

if [ "$1" = "$run" ]; then
  docker run --gpus all -it --ipc=host \
	-v /home/anau/:/home/anau/ \
	-v /data:/data \
	-v /da1_data:/da1_data \
	-v /usb:/usb \
	--name "$name" \
	"$image" \
	/bin/bash

elif [ "$1" = "$bash" ]; then
  docker start "$name"
  docker exec -it "$name" /bin/bash

elif [ "$1" = "$remove" ]; then
  docker stop "$name"
  docker rm "$name"

else
  echo "Usage: sh $0 <run / bash / rm>"
fi
