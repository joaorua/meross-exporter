# meross-exporter
Exporter metrics from Meross device


How to use

docker run -d --name meross-exporter -e MEROSS_EMAIL=<EMAIL> -e MEROSS_PASSWORD=<PASSWORD> -p 8888:8000 meross-exporter
