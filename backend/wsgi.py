from app import app
import logging
# from flask_mqtt import Mqtt



if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    
    mqtt = Mqtt(app)
    

if __name__ == "__main__":
    app.run()
