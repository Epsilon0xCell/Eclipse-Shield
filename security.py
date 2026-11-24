"""
Security configuration and utilities for Eclipse Shield.
Contains security settings, validators, and middleware.
"""

import os
import secrets
import hashlib
import hmac
import time
from functools import wraps
from typing import Optional, Dict, Any
import ipaddress
import re
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration class with secure defaults."""
    
    # Generate secure secret key
    # If the environment holds no key, I mint a fresh one at import.
    # That keeps a local run working with no setup. It also means
    # sessions and tokens die on every restart, and each worker process
    # holds a different key, so the Docker setup has to supply one
    # through the environment for sessions to survive across workers.
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    
    # Session configuration (localhost-friendly)
    SESSION_COOKIE_SECURE = False  # False for localhost HTTP
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # CSRF configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Security headers (localhost-optimized)
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',  # Allow same origin for localhost
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': (
            "default-src 'self' http://localhost:* http://127.0.0.1:*; "
            "script-src 'self' 'unsafe-inline' http://localhost:* http://127.0.0.1:*; "
            "style-src 'self' 'unsafe-inline' http://localhost:* http://127.0.0.1:*; "
            "img-src 'self' data: blob: http://localhost:* http://127.0.0.1:*; "
            "connect-src 'self' http://localhost:* http://127.0.0.1:* chrome-extension:; "
            "font-src 'self' data: http://localhost:* http://127.0.0.1:*; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    # Rate limiting configuration
    RATE_LIMIT_STORAGE_URL = 'memory://'
    RATE_LIMIT_DEFAULT = '100/hour'
    RATE_LIMIT_STRICT = '10/minute'
    
    # API key validation
    API_KEY_MIN_LENGTH = 20
    
    # CORS configuration (Chrome extension friendly)
    CORS_ORIGINS = [
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'chrome-extension://*',
        'moz-extension://*'  # Firefox support
    ]
    
    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {'txt', 'json'}
    MAX_CONTENT_LENGTH = 1024 * 1024  # 1MB

class InputValidator:
    """Input validation utilities."""
    
    # URL validation is parse based (see validate_url below). The old
    # URL_PATTERN regex capped the top level domain at six letters and
    # falsely rejected valid long-TLD sites, so it was removed rather
    # than widened.
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    DOMAIN_PATTERN = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    )
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format and security.

        Parse based, not regex based. The old URL_PATTERN capped the
        top level domain at six letters, so valid sites under .technology,
        .international and other long TLDs were rejected as malformed.
        Credentials embedded in the URL (user:pass@host) are rejected
        deliberately: they are a classic host confusion trick
        (https://example.com@evil.com/) and never a legitimate browsing
        target for classification.
        """
        if not url or not isinstance(url, str) or len(url) > 2048:
            return False

        try:
            parsed = urlparse(url.strip())

            if parsed.scheme not in ['http', 'https']:
                return False

            # Reject embedded credentials outright.
            if parsed.username or parsed.password:
                logger.warning("Blocked URL with embedded credentials")
                return False

            hostname = parsed.hostname
            if not hostname:
                return False
            hostname = hostname.rstrip('.').lower()

            # Single-label hosts are intranet names, not browsing targets.
            if hostname != 'localhost' and '.' not in hostname:
                try:
                    ipaddress.ip_address(hostname)
                except ValueError:
                    return False

            # Host must be a plausible DNS name, localhost, or an IP.
            if hostname != 'localhost' and not InputValidator.DOMAIN_PATTERN.match(hostname):
                # DOMAIN_PATTERN also matches bare integers and hex-ish
                # labels; those are handled by the IP checks below.
                try:
                    ipaddress.ip_address(hostname)
                except ValueError:
                    return False

            # Block loopback hosts. The URLs submitted to /analyze are
            # productivity classification targets, never destinations this
            # server fetches, and loopback targets (router admin panels,
            # local services, this app itself) are not legitimate browsing
            # targets for the extension to classify.
            if hostname in ['localhost', '::1']:
                logger.warning(f"Blocked loopback access: {url}")
                return False

            # Block private, loopback, link-local and reserved IP ranges,
            # including obfuscated integer and hex IPv4 forms
            # (http://2130706433/ and http://0x7f000001/ are 127.0.0.1).
            ip = None
            try:
                ip = ipaddress.ip_address(hostname)
            except ValueError:
                if hostname.isdigit():
                    try:
                        ip = ipaddress.IPv4Address(int(hostname))
                    except (ValueError, ipaddress.AddressValueError):
                        ip = None
                elif hostname.startswith('0x'):
                    try:
                        ip = ipaddress.IPv4Address(int(hostname, 16))
                    except (ValueError, ipaddress.AddressValueError):
                        ip = None
            if ip is not None and (ip.is_private or ip.is_loopback
                                   or ip.is_link_local or ip.is_reserved
                                   or ip.is_multicast or ip.is_unspecified):
                logger.warning(f"Blocked private/reserved IP access: {url}")
                return False

            return True

        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False
    
    @staticmethod
    def validate_domain(domain: str) -> bool:
        """Validate domain format."""
        if not domain or len(domain) > 253:
            return False
        return bool(InputValidator.DOMAIN_PATTERN.match(domain))
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not isinstance(text, str):
            return ""
        
        # Remove null bytes and control characters
        text = text.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        
        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def validate_json_payload(data: Dict[str, Any], required_fields: list) -> tuple[bool, str]:
        """Validate JSON payload structure."""
        if not isinstance(data, dict):
            return False, "Invalid JSON format"
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        return True, "Valid"

class SecurityMiddleware:
    """Security middleware for request processing."""
    
    def __init__(self, app):
        self.app = app
        self.failed_attempts = {}  # Simple in-memory store
        self.cleanup_time = time.time()
    
    # I only drop an IP entry when every attempt in it is old. The list
    # inside a kept entry is not trimmed, so old timestamps stay in it.
    # is_rate_limited recounts inside its own window each time, so the
    # stale entries cost memory, not wrong blocks.
    def cleanup_failed_attempts(self):
        """Clean up old failed attempts."""
        current_time = time.time()
        if current_time - self.cleanup_time > 3600:  # Clean every hour
            cutoff_time = current_time - 3600  # Keep last hour
            self.failed_attempts = {
                ip: attempts for ip, attempts in self.failed_attempts.items()
                if any(attempt_time > cutoff_time for attempt_time in attempts)
            }
            self.cleanup_time = current_time
    
    def is_rate_limited(self, client_ip: str, max_attempts: int = 10, window: int = 3600) -> bool:
        """Check if client IP is rate limited."""
        self.cleanup_failed_attempts()
        
        current_time = time.time()
        if client_ip not in self.failed_attempts:
            return False
        
        # Count attempts in the time window
        recent_attempts = [
            attempt_time for attempt_time in self.failed_attempts[client_ip]
            if current_time - attempt_time < window
        ]
        
        return len(recent_attempts) >= max_attempts
    
    def record_failed_attempt(self, client_ip: str):
        """Record a failed attempt."""
        current_time = time.time()
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []
        self.failed_attempts[client_ip].append(current_time)

def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str, session_token: str) -> bool:
    """Validate CSRF token."""
    if not token or not session_token:
        return False
    return hmac.compare_digest(token, session_token)

def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            logger.warning(f"API key missing for {request.endpoint}")
            return jsonify({'error': 'API key required'}), 401
        
        # Validate API key format
        if len(api_key) < SecurityConfig.API_KEY_MIN_LENGTH:
            logger.warning(f"Invalid API key format for {request.endpoint}")
            return jsonify({'error': 'Invalid API key format'}), 401
        
        # Here you would validate against your API key store
        # As written, if no server key is set in the environment, any
        # header value that meets the minimum length passes this check.
        # secure_app imports this decorator but no route applies it, so
        # that gap is dormant today. I keep it written down here so a
        # future route does not inherit it by surprise.
        # For now, we'll check against environment variable
        valid_api_key = os.environ.get('ECLIPSE_SHIELD_API_KEY')
        if valid_api_key and not hmac.compare_digest(api_key, valid_api_key):
            logger.warning(f"Invalid API key for {request.endpoint}")
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def secure_filename(filename: str) -> str:
    """Secure a relative file path for safe serving.

    Path aware: legitimate subdirectory separators are preserved so nested
    assets (for example matrix-animation/js/main.js) keep working, while
    traversal segments, backslashes, and leading dots are removed. Callers
    should still pass the result through a safe join (Flask's
    send_from_directory does this) as a second layer of defense.
    """
    if not filename or not isinstance(filename, str):
        return 'unnamed'

    parts = []
    for part in filename.replace('\\', '/').split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            # Traversal attempt: drop the whole path; the resulting
            # placeholder name will not resolve to a real file.
            return 'unnamed'
        # Remove dangerous characters, then leading dots and spaces
        part = re.sub(r'[^\w\-_\.]', '', part).lstrip('. ')
        if part:
            parts.append(part)

    cleaned = '/'.join(parts)

    # Limit length of the final path segment
    if parts and len(parts[-1]) > 255:
        name, ext = os.path.splitext(parts[-1])
        parts[-1] = name[:255 - len(ext)] + ext
        cleaned = '/'.join(parts)

    return cleaned or 'unnamed'
