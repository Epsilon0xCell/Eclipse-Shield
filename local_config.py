# macOS-specific configuration for Eclipse Shield local deployment
# Nothing in the running app imports this file. I keep it as the
# written record of the local choices that the Docker files and the
# secure_app settings were picked from, so the numbers have one place
# to be read together. Changing a value here changes nothing at run
# time, and I do not want a future edit to assume it does.

# Localhost-specific security settings
LOCAL_ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0'
]

# Docker container networking
CONTAINER_NETWORK = 'eclipse-network'
REDIS_CONTAINER = 'redis'

# macOS-specific paths and settings
MACOS_SETTINGS = {
    'logs_path': './logs',
    'cache_path': './cache',
    'temp_path': '/tmp/eclipse-shield',
    'max_file_descriptors': 1024,
    'socket_timeout': 30
}

# Security settings optimized for localhost
LOCALHOST_SECURITY = {
    'allow_insecure_transport': True,  # HTTP allowed for localhost
    'csrf_protection': True,
    'rate_limiting': True,
    'input_validation': True,
    'session_security': True,
    'container_isolation': True
}

# Chrome extension compatibility
CHROME_EXTENSION_SETTINGS = {
    'allowed_origins': [
        'chrome-extension://*',
        'http://localhost:5000',
        'http://127.0.0.1:5000'
    ],
    'content_security_policy': {
        'script_src': "'self' 'unsafe-inline' 'unsafe-eval' http://localhost:*",
        'connect_src': "'self' http://localhost:* chrome-extension:",
        'style_src': "'self' 'unsafe-inline' http://localhost:*"
    }
}

# Docker resource limits for local development
DOCKER_LIMITS = {
    'memory': '256m',
    'cpu': '0.5',
    'restart_policy': 'unless-stopped'
}

# Development features
DEV_FEATURES = {
    'hot_reload': False,  # Disabled for security
    'debug_mode': False,
    'detailed_errors': False,  # Hide stack traces
    'profiling': False
}
