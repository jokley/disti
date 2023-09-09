from app import app
import logging
from flask_mqtt import Mqtt
from flask_sqlalchemy import SQLAlchemy


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    
    mqtt = Mqtt(app)
    mqtt.subscribe("/sensors")  
    
    db = SQLAlchemy(app)
    db.create_all()

if __name__ == "__main__":
    app.run()
