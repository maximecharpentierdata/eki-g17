FROM python:3.9

WORKDIR /

COPY ./opti/requirements.txt /opti/requirements.txt

RUN pip3 install -r /opti/requirements.txt

COPY . .

CMD ["python3", "opti/optimize.py", "scenario_3/orders_s3.csv", "2", "scenario_3/new_routes_s3_2.csv"]