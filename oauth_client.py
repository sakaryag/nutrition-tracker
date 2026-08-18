try:
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth()
except ImportError:
    oauth = None
