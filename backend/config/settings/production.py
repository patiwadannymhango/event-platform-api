from .base import *


DEBUG = False

SECURE_BROWSER_XSS_FILTER = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

# Caddy terminates TLS and forwards plain HTTP to gunicorn, so without this
# Django thinks every request is insecure — request.is_secure() is False,
# so it computes the CSRF "expected origin" as http://... while the browser
# sends Origin: https://..., and every admin login gets rejected with a
# CSRF failure. Caddy's reverse_proxy sets X-Forwarded-Proto automatically.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")