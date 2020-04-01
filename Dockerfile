FROM python:3.6.4-stretch
ADD . /opt/app
WORKDIR /opt/app
RUN pip install -r requirements.txt
CMD ["python", "bot.py"]