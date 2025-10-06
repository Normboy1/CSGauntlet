from celery import Celery
from flask import Flask
from config import Config

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['REDIS_URL'],
        backend=app.config['REDIS_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# This is for when Celery worker starts independently
# It needs a way to load the Flask app context
flask_app = Flask(__name__)
flask_app.config.from_object(Config)
celery_app = make_celery(flask_app)