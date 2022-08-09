FROM ubuntu:bionic as soliditybuilder

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

# RUN apt-get install gcc g++ make cmake gfortran libffi-dev openssl-dev libtool

RUN apt-get install graphviz graphviz-dev -y

# RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install pyinstaller

RUN pip install certifi==2021.10.8
RUN pip install charset-normalizer==2.0.12
RUN pip install coloredlogs==15.0.1
RUN pip install future==0.18.2
RUN pip install graphviz==0.19
RUN pip install grpcio==1.45.0
RUN pip install humanfriendly==10.0
RUN pip install idna==3.3
RUN pip install networkx==2.5
RUN pip install protobuf==3.19.0
RUN pip install py-solc-x==1.1.1
RUN pip install pyevmasm==0.2.3
RUN pip install pygraphviz==1.6
RUN pip install PyYAML==6.0
RUN pip install requests==2.27.1
RUN pip install semantic-version==2.9.0
RUN pip install six==1.16.0
RUN pip install urllib3==1.26.9
RUN pip install z3-solver==4.8.17.0
RUN pip install memory_profiler==0.60.0

COPY . /root/
WORKDIR /root/
# # RUN pip install -r requirements.txt
RUN mv /usr/sbin/libgvc6-config-update /usr/bin/dot
RUN pyinstaller --add-binary /usr/local/lib/python3.6/dist-packages/z3/lib/libz3.so:. --add-binary /usr/lib/x86_64-linux-gnu/graphviz/*:./graphviz -F solidity_service.py


FROM ubuntu:bionic as prod
WORKDIR /root
RUN  apt-get update \
   && apt-get install graphviz nodejs npm -y --no-install-recommends
COPY --from=soliditybuilder /root/dist/solidity_service /root
COPY --from=soliditybuilder /root/config.yaml /root/
ENTRYPOINT ["./solidity_service"]

