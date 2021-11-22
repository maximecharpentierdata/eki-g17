FROM python:3.9

WORKDIR /

COPY ./opti/requirements.txt /opti/requirements.txt

RUN pip3 install -r /opti/requirements.txt

COPY . .

CMD ["python3", "opti/optimize.py", "scenario_2/orders_s2.csv", "3", "scenario_2/new_routes_s2_3.csv"]