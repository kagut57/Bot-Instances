# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11

# Upgrade pip and setuptools
RUN pip install --upgrade pip setuptools

# Install apt requirements (some basic stuff)
RUN apt-get update \
    && apt-get install -y \
        git \
        wget \
        curl \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/*

#Work dir for bots
WORKDIR /app

#Copy code to /app
COPY . /app/

#install dependencies
RUN pip install -r requirements.txt

#Run cmd
CMD ["python3", "bots.py"]
