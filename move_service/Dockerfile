FROM ubuntu:bionic as movebuilder

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev graphviz graphviz-dev \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip


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
RUN pip install antlr4-python3-runtime==4.9.3
RUN pip install tree-sitter==0.20.1

COPY . /root/
WORKDIR /root/
RUN mv /usr/sbin/libgvc6-config-update /usr/bin/dot
RUN python ./move_parser/build_parser.py
RUN pyinstaller --add-binary /usr/local/lib/python3.6/dist-packages/z3/lib/libz3.so:. --add-binary /usr/lib/x86_64-linux-gnu/graphviz/*:./graphviz -F move_service.py


FROM ubuntu:bionic as prod
WORKDIR /root
RUN  apt-get update \
   && apt-get install -y graphviz curl
RUN curl -sL https://deb.nodesource.com/setup_16.x | bash  -
RUN apt-get install -y nodejs
COPY --from=jsbuilder //root/move_parser/build/my-languages.so /root/move_parser/build/
COPY --from=jsbuilder /root/dist/move_service /root/
COPY --from=jsbuilder /root/move_service/config.yaml /root/
ENTRYPOINT ["./move_service"]

