from app import app
import logging
from flask import Blueprint



if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    
    bp = Blueprint('burritos', __name__,
                        template_folder='templates')
    

if __name__ == "__main__":
     app.run()
