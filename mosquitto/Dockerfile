FROM eclipse-mosquitto:2

COPY docker-entrypoint-disti.sh /usr/local/bin/docker-entrypoint-disti

ENTRYPOINT ["/usr/local/bin/docker-entrypoint-disti"]
CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
