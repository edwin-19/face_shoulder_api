FROM continuumio/miniconda3

ARG WORK_DIR=/ml_api

COPY ./ $WORK_DIR
WORKDIR $WORK_DIR

RUN apt-get update && apt-get install ffmpeg g++ -y

RUN conda create -n deploy_env python=3.7 -y

RUN echo "conda activate deploy_env" >> ~/.bashrc
SHELL ["/bin/bash", "--login", "-c"]

RUN pip install -r requirements.txt

EXPOSE $PORT
# ENTRYPOINT ["uvicorn", "app:app", "--port=8000", "--host=0.0.0.0"]
ENTRYPOINT ["./deployment/entrypoint.sh"]
