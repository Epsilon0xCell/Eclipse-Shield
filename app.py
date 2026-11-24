"""Eclipse Shield Flask entry point.

This module used to carry a second, older copy of the whole Flask app
(556 lines) next to secure_app.py, and the two drifted: the legacy copy
bound 0.0.0.0, returned raw exception text to clients, started a thread
at import time, and validated URLs with a two-line check. Every route
fix had to be made twice or the wsgi fallback quietly served the old
behavior. It is now a thin shim over the one real app factory, so
`python app.py`, `flask --app app run`, and the wsgi fallback all serve
exactly the same application as secure_app.
"""

import os

from secure_app import create_app

app = create_app()

if __name__ == '__main__':
    # Local tool: loopback only. Binding 0.0.0.0 would expose the
    # key-holding backend to the whole LAN.
    app.run(host='127.0.0.1', port=5000,
            debug=os.environ.get('FLASK_DEBUG') == '1',
            use_reloader=False, threaded=True)
