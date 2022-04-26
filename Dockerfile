FROM tensorflow/tensorflow:1.15.2-gpu-py3

ENV DEBIAN_FRONTEND=noninteractive

RUN pip3 install bpython
RUN apt-get update
RUN apt-get update && apt-get install -q -y \
  wget \
  vim \
  git \
  python3-opencv \
  cython3 \
  build-essential

RUN pip3 install --no-cache-dir git+https://github.com/waleedka/coco.git#subdirectory=PythonAPI
RUN pip3 install imgaug
RUN pip3 install keras==2.1
RUN pip3 install scikit-learn
RUN pip3 install notebook
RUN apt-get install python3-opencv  # install opencv for python3

WORKDIR "/root"
CMD ["/bin/bash"]


