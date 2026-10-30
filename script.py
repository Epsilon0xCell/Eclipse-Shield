import os
import json
import requests
import google.generativeai as genai
from typing import Dict, List, Optional # Added Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
import re
import html
from datetime import datetime, timedelta

# Import security validators
try:
    from security import InputValidator
except ImportError:
    # Fallback if security module not available
    # This fallback is far weaker than security.py, and the difference
    # is concrete: its validate_url checks a scheme and a host and
    # nothing else, where the real one also blocks loopback and private
    # addresses. It exists so a checkout missing security.py still runs
    # the analyzer. The secure app imports the real class, never this
    # one.
    class InputValidator:
        @staticmethod
        def validate_url(url):
            # Basic URL validation
            try:
                result = urlparse(url)
                return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
            except:
                return False
        
        @staticmethod
        def validate_domain(domain):
            # Basic domain validation
            return bool(re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', domain))
        
        @staticmethod
        def sanitize_string(text, max_length=1000):
            if not isinstance(text, str):
                return ""
            # Remove dangerous characters and limit length
            text = html.escape(text.strip())
            return text[:max_length] if len(text) > max_length else text

# Setup logging for script.py - ENHANCED LOGGING
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for maximum verbosity
# Prevent duplicate handlers if script is reloaded in some environments
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(filename)s - %(lineno)d - %(message)s') # More detailed format
    handler.setFormatter(formatter)
    logger.addHandler(handler)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Placeholder values that ship in example files and must never be treated
# as a real, configured API key.
PLACEHOLDER_API_KEYS = {
    "", "api_key_value", "your-api-key", "your_api_key",
    "your-google-gemini-api-key", "your_api_key_here",
    "your-super-secret-key-change-this-in-production",
}

API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY", "API_KEY",
                    "ECLIPSE_GEMINI_API_KEY")


def _is_real_api_key(value) -> bool:
    return bool(value) and value.strip().lower() not in PLACEHOLDER_API_KEYS


def load_api_key() -> Optional[str]:
    """Load the Gemini API key from the environment or api_key.txt.

    Resolution order: GOOGLE_API_KEY, GEMINI_API_KEY, API_KEY,
    ECLIPSE_GEMINI_API_KEY, then api_key.txt located next to this module
    (never relative to the process working directory).

    Returns None when no real key is configured. A missing key is not an
    error: the analyzer then runs in local rules-only mode. Placeholder
    values from the shipped example files count as "not configured".
    """
    for env_var in API_KEY_ENV_VARS:
        value = os.getenv(env_var)
        if _is_real_api_key(value):
            logger.debug(f"load_api_key - API key loaded from ${env_var}")
            return value.strip()

    key_file = os.getenv("ECLIPSE_API_KEY_FILE") or os.path.join(BASE_DIR, "api_key.txt")
    try:
        with open(key_file, "r") as f:
            value = f.read().strip()
        if _is_real_api_key(value):
            logger.debug("load_api_key - API key loaded from api_key.txt")
            return value
        logger.warning("load_api_key - api_key.txt holds a placeholder or empty value; treating as not configured")
    except FileNotFoundError:
        logger.warning("load_api_key - No API key in environment or api_key.txt; AI features disabled")

    return None

def load_domain_settings(settings_path: Optional[str] = None) -> Dict:
    """Load domain settings from settings.json.

    The path resolves relative to this module's directory, not the process
    working directory, so the app can be launched from anywhere.
    """
    logger.debug("load_domain_settings - START")
    path = (settings_path or os.getenv("ECLIPSE_SETTINGS_FILE")
            or os.path.join(BASE_DIR, "settings.json"))
    try:
        with open(path, "r") as f:
            settings = json.load(f)
            logger.debug("load_domain_settings - Settings loaded from settings.json")
            logger.debug("load_domain_settings - END - SUCCESS")
            return settings
    except FileNotFoundError:
        error_msg = f"settings.json file not found at {path}."
        logger.error(f"load_domain_settings - {error_msg}")
        raise FileNotFoundError(error_msg)
    except json.JSONDecodeError as e: # Pass error details
        error_msg = f"settings.json is not valid JSON: {e}"
        logger.error(f"load_domain_settings - {error_msg}")
        raise json.JSONDecodeError(error_msg, e.doc, e.pos) # Re-raise with original details
    except Exception as e:
        logger.error(f"load_domain_settings - Error loading settings: {e}")
        raise

class ProductivityAnalyzer:
    # Deterministic question sequence used when AI is unavailable (or an
    # AI call fails), so contextualization always terminates: after two
    # answers the analyzer reports DONE instead of looping forever.
    FALLBACK_QUESTIONS = [
        "What specific task are you working on?",
        "What are you trying to accomplish with this task?",
    ]

    # Local decision tables used when AI is unavailable. These only apply
    # to sites that matched no explicit allow or block rule in settings.
    LOCAL_PRODUCTIVE_CATEGORIES = {
        'educational', 'documentation/reference', 'development/code',
        'productivity/tools',
    }
    LOCAL_UNPRODUCTIVE_CATEGORIES = {
        'social media', 'streaming/entertainment', 'gaming',
        'e-commerce/shopping',
    }

    def __init__(self, api_key: Optional[str] = None,
                 settings_path: Optional[str] = None,
                 settings: Optional[Dict] = None,
                 model=None):
        logger.debug("ProductivityAnalyzer.__init__ - START")
        self.settings = settings if settings is not None else load_domain_settings(settings_path)

        self.model = None
        self.ai_available = False
        self.api_key = api_key if api_key is not None else load_api_key()

        if model is not None:
            # Injected model (used by tests with a clearly labeled fixture).
            self.model = model
            self.ai_available = True
        elif self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
                self.model = genai.GenerativeModel(model_name)
                self.ai_available = True
                logger.debug("ProductivityAnalyzer.__init__ - Google Generative AI configured and model created.")
            except Exception as e:
                # AI setup failure must not take down the whole analyzer:
                # explicit allow/block rules and local fallbacks still work.
                logger.error(f"ProductivityAnalyzer.__init__ - AI setup failed, continuing in local rules-only mode: {e}")
                self.model = None
                self.ai_available = False
        else:
            logger.warning("ProductivityAnalyzer.__init__ - No Gemini API key configured; running in local rules-only mode")

        self.context_data = {}
        logger.debug(f"ProductivityAnalyzer.__init__ - Analyzer initialized (ai_available={self.ai_available}).")
        logger.debug("ProductivityAnalyzer.__init__ - END")

    def _generate_text(self, prompt: str) -> str:
        """Generate text with the configured model, with a hard timeout."""
        if self.model is None:
            raise RuntimeError("AI model is not configured")
        try:
            response = self.model.generate_content(
                prompt, request_options={'timeout': 20}
            )
        except TypeError:
            # Fixture models and older SDKs may not accept request_options.
            response = self.model.generate_content(prompt)
        if not hasattr(response, 'text'):
            raise ValueError("Invalid response format from AI.")
        return response.text.strip()

    @staticmethod
    def _normalize_context(context) -> List[Dict]:
        """Normalize Q&A context to a list of {'question', 'answer'} dicts.

        Accepts the list form the browser extension sends and the mapping
        form {question: answer} that the HTTP API historically produced.
        """
        normalized = []
        if isinstance(context, dict):
            items = [{'question': k, 'answer': v} for k, v in context.items()]
        elif isinstance(context, list):
            items = context
        else:
            return normalized
        for item in items[:10]:  # Limit to 10 items
            if isinstance(item, dict):
                question = InputValidator.sanitize_string(str(item.get('question', '')), 500)
                answer = InputValidator.sanitize_string(str(item.get('answer', '')), 1000)
                if question and answer:
                    normalized.append({'question': question, 'answer': answer})
        return normalized

    def _fallback_question(self, context_list: List[Dict]) -> Dict:
        """Next question from the deterministic local sequence."""
        if len(context_list) < len(self.FALLBACK_QUESTIONS):
            return {"question": self.FALLBACK_QUESTIONS[len(context_list)]}
        return {"question": "DONE"}

    def _local_fallback_decision(self, url: str, url_signals: dict,
                                   context_relevance: dict) -> dict:
        """Rule-based decision used when AI is unavailable or fails.

        Built only from signals this module already computes locally:
        the categorized hostname, search state, and context relevance.
        """
        category = url_signals.get('domain_type', 'general')

        if context_relevance.get('score', 0.0) >= 0.5:
            matched = ', '.join(context_relevance.get('matched_terms', []))
            return {'isProductive': True,
                    'explanation': f"Allowed by local rules: matches your task context ({matched})."}

        if category in self.LOCAL_PRODUCTIVE_CATEGORIES:
            return {'isProductive': True,
                    'explanation': f"Allowed by local rules (AI unavailable): {category} site."}

        if url_signals.get('is_search') and url_signals.get('search_query'):
            return {'isProductive': True,
                    'explanation': "Allowed by local rules (AI unavailable): search with an explicit query."}

        if category in self.LOCAL_UNPRODUCTIVE_CATEGORIES:
            return {'isProductive': False,
                    'explanation': f"Blocked by local rules (AI unavailable): {category} site."}

        return {'isProductive': False,
                'explanation': "Blocked by local rules: AI is unavailable and no local rule matched this site."}

    def get_next_question(self, domain: str, context=None) -> Dict:
        """Get the next contextual question based on previous answers.

        Context may be a list of {'question', 'answer'} dicts (what the
        browser extension sends) or a {question: answer} mapping. When AI
        is unavailable, or an AI call fails, a deterministic local question
        sequence is used so the flow always reaches DONE.
        """
        logger.debug(f"ProductivityAnalyzer.get_next_question - START - Domain: {domain}, Context: {context}")

        # Security validation: domain is a configured profile name
        # (work, school, personal), not a hostname.
        domain = InputValidator.sanitize_string(domain, 100)
        if domain not in self.settings.get("domains", {}):
            logger.warning(f"Unknown domain profile provided: {domain}")
            return {"question": "What are you trying to accomplish?"}

        context = self._normalize_context(context)

        if not self.ai_available:
            return self._fallback_question(context)

        try:
            if not context:
                prompt = f"""As a productivity assistant, ask one direct question to understand what the user is working on in the {domain} domain.
                Keep it simple and focused on their immediate task.
                Example good questions:
                - What specific task are you working on?
                - What are you trying to accomplish?
                Respond with only the question text, no additional formatting."""
                logger.debug("ProductivityAnalyzer.get_next_question - First question - Prompt:\n" + prompt) # Log prompt
            else:
                # Format conversation history for the prompt
                history_str = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in context])
                prompt = f"""Based on this context about a {domain} task, determine if you have enough information or need to ask one more question.
                Previous Q&A:
                {history_str}

                First, analyze if you have enough information to understand:
                1. What specific task/activity the user is doing
                2. What they are trying to achieve (goal/outcome)

                If you have clear answers to BOTH of these, respond with exactly 'DONE'.
                If you're missing either of these key pieces of information, ask ONE focused follow-up question about what you're missing.
                Do not ask about time, duration, or scheduling.
                Keep the question concise and direct.
                Respond with either exactly 'DONE' or your single follow-up question (no other text)."""
                logger.debug("ProductivityAnalyzer.get_next_question - Subsequent question - Prompt:\n" + prompt) # Log prompt

            question = self._generate_text(prompt)
            logger.debug(f"ProductivityAnalyzer.get_next_question - AI Response Text: {question}") # Log response text

            if question.upper() == 'DONE':
                logger.debug("ProductivityAnalyzer.get_next_question - AI returned 'DONE'")
                logger.debug("ProductivityAnalyzer.get_next_question - END - DONE")
                return {"question": "DONE"}

            logger.debug(f"ProductivityAnalyzer.get_next_question - Next question: {question}")
            logger.debug("ProductivityAnalyzer.get_next_question - END - Question generated")
            return {"question": question}

        except Exception as e:
            # Degrade to the deterministic local sequence instead of
            # returning the same default question forever (which looped
            # contextualize() and the extension UI indefinitely).
            logger.error(f"ProductivityAnalyzer.get_next_question - AI error, using local fallback: {e}", exc_info=True)
            return self._fallback_question(context)

    def contextualize(self, domain: str) -> None:
        """Ask focused questions one at a time to contextualize the task."""
        logger.debug(f"ProductivityAnalyzer.contextualize - START - Domain: {domain}")
        conversation_history = []
        self.context_data = {} # Reset context data for each call
        logger.debug("ProductivityAnalyzer.contextualize - Conversation history and context data initialized.")

        while True:
            question_data = self.get_next_question(domain, conversation_history)
            question = question_data["question"]
            logger.debug(f"ProductivityAnalyzer.contextualize - Received question from get_next_question: {question}")

            if question.upper() == 'DONE':
                logger.info("ProductivityAnalyzer.contextualize - Context gathering complete (AI returned DONE).") # Changed to INFO
                # Consolidate context_data from conversation_history for consistency
                self.context_data = {item['question']: item['answer'] for item in conversation_history}
                logger.debug("ProductivityAnalyzer.contextualize - Final context data gathered:\n" + json.dumps(self.context_data, indent=2))
                logger.debug("ProductivityAnalyzer.contextualize - END - DONE")
                break

            print("\n" + question)
            print("-" * 40)
            answer = input("Answer: ")
            print()

            # Store Q&A pair in history list
            conversation_history.append({"question": question, "answer": answer})
            # Update context_data dictionary immediately (though it's rebuilt at the end)
            # self.context_data[question] = answer # Optional: can remove if rebuilt from history
            logger.debug(f"ProductivityAnalyzer.contextualize - User answer recorded. Added to history.")

        logger.debug("ProductivityAnalyzer.contextualize - END - Contextualization loop finished")

    def _get_domain_from_url(self, url: str) -> Optional[str]: # Return type hint Optional
        """Extract the base domain (network location) from a URL."""
        logger.debug(f"ProductivityAnalyzer._get_domain_from_url - START - URL: {url}")
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
             logger.warning(f"ProductivityAnalyzer._get_domain_from_url - Invalid or non-HTTP(S) URL provided: '{url}'")
             return None
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if not domain:
                logger.warning(f"ProductivityAnalyzer._get_domain_from_url - Could not parse network location from URL: '{url}'")
                return None
            logger.debug(f"ProductivityAnalyzer._get_domain_from_url - Parsed domain: {domain}")
            logger.debug("ProductivityAnalyzer._get_domain_from_url - END - SUCCESS")
            return domain
        except Exception as e:
            logger.warning(f"ProductivityAnalyzer._get_domain_from_url - Error parsing URL '{url}': {e}") # Changed to logger.warning
            logger.debug("ProductivityAnalyzer._get_domain_from_url - END - ERROR, returning None")
            return None

    def _is_allowed_platform(self, url: str, domain: str) -> bool:
        """Check if URL belongs to allowed platforms for specific domain."""
        base_domain = self._get_domain_from_url(url)
        logger.debug(f"_is_allowed_platform - Checking domain: {base_domain} for URL: {url} in {domain} context")

        if not base_domain:
            return False

        try:
            # Ensure the domain exists in settings
            if domain not in self.settings.get("domains", {}):
                 logger.warning(f"_is_allowed_platform - Domain '{domain}' not found in settings.")
                 return False
            settings = self.settings["domains"][domain]

            url_lower = url.lower()
            hostname_lower = base_domain # Already lowercased by _get_domain_from_url

            # Only check platform types that exist in this domain's settings
            allowed_platform_types = ['lms_platforms', 'productivity_tools', 'ai_tools']

            for platform_type in allowed_platform_types:
                if platform_type not in settings:
                    continue # Skip if this platform type isn't defined for the domain

                # Ensure the setting is actually a list
                if not isinstance(settings.get(platform_type), list):
                    logger.warning(f"_is_allowed_platform - Setting '{platform_type}' for domain '{domain}' is not a list.")
                    continue

                for platform in settings[platform_type]:
                    if not isinstance(platform, str): # Ensure platform entry is a string
                        logger.warning(f"_is_allowed_platform - Non-string entry found in '{platform_type}' for domain '{domain}': {platform}")
                        continue
                    platform_lower = platform.lower()
                    # I know substring matching is wide. A platform string
                    # can match inside a longer hostname that is not that
                    # platform. I accept it here because the platform lists
                    # are mine in settings.json and I keep the entries
                    # specific. A list I did not control would need exact
                    # host checks instead of this.
                    # Check if the platform is a substring of the hostname OR the full URL
                    # This allows matching subdomains (e.g., classroom.google.com) or specific paths if needed
                    if platform_lower in hostname_lower or platform_lower in url_lower:
                        logger.info(f"_is_allowed_platform - Platform match in {domain} domain - Type: {platform_type}, Platform: {platform} for URL {url}")
                        return True

            logger.debug(f"_is_allowed_platform - No allowed platform match for {url} in {domain} domain")
            return False
        except KeyError:
             logger.error(f"_is_allowed_platform - Malformed settings for domain '{domain}'.")
             return False
        except Exception as e:
            logger.error(f"_is_allowed_platform - Error during check: {e}", exc_info=True)
            return False

    # This function seems redundant if _is_allowed_platform checks 'ai_tools'
    # Kept for potential specific logic, but consider merging/removing.
    def _is_ai_site(self, url: str) -> bool:
        """Check if the URL belongs to a known AI tool site (can be domain specific via settings)."""
        logger.debug(f"ProductivityAnalyzer._is_ai_site - START - URL: {url}")
        base_domain = self._get_domain_from_url(url)
        logger.debug(f"ProductivityAnalyzer._is_ai_site - Base domain from URL: {base_domain}")
        if not base_domain:
            logger.debug("ProductivityAnalyzer._is_ai_site - Base domain is None, returning False")
            return False

        # Generic AI patterns (can be expanded or moved entirely to settings.json)
        ai_patterns = [
            "chat.openai.com", "chatgpt.com",
            "bard.google.com",
            "claude.ai",
            "gemini.google.com",
            "copilot.microsoft.com", # Updated copilot domain
            "perplexity.ai"
        ]
        logger.debug(f"ProductivityAnalyzer._is_ai_site - Generic AI patterns: {ai_patterns}")

        # Check generic patterns
        if any(base_domain == ai_domain or base_domain.endswith('.' + ai_domain) for ai_domain in ai_patterns):
             logger.debug(f"ProductivityAnalyzer._is_ai_site - Generic AI site match found.")
             logger.debug("ProductivityAnalyzer._is_ai_site - END - Returning True")
             return True

        # Check domain-specific AI tools from settings
        # This requires knowing the current domain context, which this function doesn't have.
        # Refactoring might be needed if domain-specific check is required here.
        # For now, it only checks generic list.
        # Alternative: Call _is_allowed_platform(url, current_domain) and check if type was 'ai_tools'

        logger.debug("ProductivityAnalyzer._is_ai_site - No AI site match found.")
        logger.debug("ProductivityAnalyzer._is_ai_site - END - Returning False")
        return False

    # This function also seems less useful now that analyze_website handles logic directly.
    # Kept for potential direct use, but analyze_website is the main entry point.
    def _is_productive_domain(self, url: str, domain: str) -> Optional[bool]:
        """Check if the domain is explicitly allowed or blocked based on settings."""
        logger.debug(f"ProductivityAnalyzer._is_productive_domain - START - URL: {url}, Domain: {domain}")
        base_domain = self._get_domain_from_url(url)
        logger.debug(f"ProductivityAnalyzer._is_productive_domain - Base domain from URL: {base_domain}")

        if not base_domain:
            logger.debug("ProductivityAnalyzer._is_productive_domain - Base domain is None, returning None")
            return None # Cannot determine without a base domain

        try:
             if domain not in self.settings.get("domains", {}):
                 logger.warning(f"_is_productive_domain - Domain '{domain}' not found in settings.")
                 return None # Cannot determine if domain settings are missing
             settings = self.settings["domains"][domain]
             logger.debug(f"ProductivityAnalyzer._is_productive_domain - Domain settings: {settings}")

             # Check if explicitly allowed platform
             if self._is_allowed_platform(url, domain):
                 logger.debug("ProductivityAnalyzer._is_productive_domain - Is allowed platform, returning True")
                 return True

             # Check if explicitly blocked specific domain/URL
             # Ensure 'blocked_specific' exists and is a list
             blocked_specific = settings.get("blocked_specific", [])
             if isinstance(blocked_specific, list):
                 for blocked in blocked_specific:
                      if not isinstance(blocked, str): continue # Skip non-string entries
                      # Simple endswith check for domains, or exact match for full URLs
                      if base_domain.endswith(blocked.lower()) or url.lower() == blocked.lower():
                          logger.debug(f"ProductivityAnalyzer._is_productive_domain - Blocked specific rule '{blocked}' match. Returning False")
                          return False
             else:
                  logger.warning(f"_is_productive_domain - 'blocked_specific' for domain '{domain}' is not a list.")


             # Check for blocked keywords in the URL
             blocked_keywords = settings.get("blocked_keywords", [])
             url_lower = url.lower()
             if isinstance(blocked_keywords, list):
                 for keyword in blocked_keywords:
                     if not isinstance(keyword, str): continue
                     if keyword.lower() in url_lower:
                         logger.debug(f"ProductivityAnalyzer._is_productive_domain - Blocked keyword '{keyword}' found in URL. Returning False")
                         return False
             else:
                 logger.warning(f"_is_productive_domain - 'blocked_keywords' for domain '{domain}' is not a list.")

             logger.debug("ProductivityAnalyzer._is_productive_domain - No explicit productive/blocked rule matched based on settings. Returning None for further analysis.")
             return None # Needs further analysis (like context or AI)

        except KeyError:
             logger.error(f"_is_productive_domain - Malformed settings for domain '{domain}'.")
             return None
        except Exception as e:
            logger.error(f"_is_productive_domain - Error during check: {e}", exc_info=True)
            return None


    def _analyze_url_components(self, url: str) -> dict:
        """Basic URL component analysis without context relevance."""
        logger.debug(f"_analyze_url_components - START - URL: {url}")
        signals = {
            'is_search': False,
            'is_educational': False,
            'is_reference': False,
            'search_query': None,
            'domain_type': 'general', # Default category
            'path_indicators': [],
            'hostname': None,
            'has_blocked_keywords_generic': False, # More specific name
            'suspicious_paths': False,
            'error': None
        }
        try:
            parsed = urlparse(url)
            signals['hostname'] = parsed.netloc.lower()
            if not signals['hostname']:
                 raise ValueError("Could not parse hostname")

            path_parts = [part for part in parsed.path.lower().split('/') if part] # Filter empty parts
            query_parts = parsed.query.lower().split('&')

            # Extract search query if present
            for param in query_parts:
                if '=' in param:
                    key, value = param.split('=', 1)
                    if key in ['q', 'query', 'search', 's', 'k', 'keyword']:
                         try:
                              signals['search_query'] = requests.utils.unquote(value) # Decode URL encoding
                         except Exception as decode_err:
                              logger.warning(f"_analyze_url_components - Error decoding search query param '{value}': {decode_err}")
                              signals['search_query'] = value # Use raw value if decoding fails
                         break # Found one, stop looking

            # Basic URL analysis based on keywords
            netloc_lower = signals['hostname']
            path_lower = parsed.path.lower()

            signals['is_search'] = any(term in netloc_lower for term in ['search.', 'google.', 'bing.', 'duckduckgo.', 'startpage.']) or \
                                   any(term in path_lower for term in ['/search', '/s/', '/find', '/sp/search']) or \
                                   signals['search_query'] is not None

            signals['is_educational'] = any(term in netloc_lower for term in ['.edu', '.ac.', 'school', 'learn', 'course', 'study', 'academic', 'khanacademy', 'coursera', 'udemy']) or \
                                      any(term in path_lower for term in ['/edu', '/learn', '/course'])

            signals['is_reference'] = any(term in netloc_lower for term in ['wiki', 'docs', 'developer.', 'reference', 'stackexchange', 'stackoverflow', 'github.io']) or \
                                     any(term in path_lower for term in ['/wiki', '/docs', '/documentation', '/ref'])

            signals['domain_type'] = self._categorize_domain(netloc_lower) # Use helper
            signals['path_indicators'] = path_parts

            # Generic keyword/path checks (domain-specific checks happen in analyze_website)
            generic_blocked_keywords = ['game', 'unblocked', 'entertainment', 'proxy', 'bypass', 'hack', 'cheat']
            url_lower = url.lower()
            signals['has_blocked_keywords_generic'] = any(keyword in url_lower for keyword in generic_blocked_keywords)
            signals['suspicious_paths'] = any(keyword in path_parts for keyword in generic_blocked_keywords)

            logger.debug(f"_analyze_url_components - Analysis result: {signals}")
            return signals

        except Exception as e:
            logger.error(f"_analyze_url_components - Error analyzing URL components for '{url}': {e}", exc_info=True)
            signals['error'] = str(e)
            return signals

    def _check_context_relevance(self, url: str, url_signals=None) -> dict:
        """Check relevance of URL and its signals against stored context data.
        
        Args:
            url: The URL to check
            url_signals: Either a dictionary of URL signals or a string containing
                        the search query directly
        """
        # Initialize result structure
        relevance = {
            'score': 0.0,
            'matched_terms': [],
            'matches': [],
            'error': None
        }
        logger.debug(f"_check_context_relevance - START - URL: {url}")

        if not self.context_data:
            logger.warning("_check_context_relevance - No context data available for analysis.")
            return relevance # Return default zero score if no context

        try:
            # --- Prepare context terms ---
            context_terms_set = set()
            logger.debug(f"_check_context_relevance - Processing context data: {self.context_data}")
            for question, answer in self.context_data.items():
                if isinstance(answer, str) and answer.strip():
                    # Clean and split into words, remove punctuation, lowercase
                    words = [word.strip('.,?!();:"\'').lower() for word in answer.split()]
                    words = [word for word in words if len(word) > 2] # Keep words longer than 2 chars

                    # Add single words
                    context_terms_set.update(words)

                    # Add 2-word phrases (bi-grams)
                    context_terms_set.update([f"{words[i]} {words[i+1]}" for i in range(len(words)-1)])

                    # Add 3-word phrases (tri-grams) - Optional, can increase noise
                    context_terms_set.update([f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)])

            context_terms = list(context_terms_set)
            if not context_terms:
                 logger.warning("_check_context_relevance - No usable terms extracted from context data.")
                 return relevance
            
            logger.debug(f"_check_context_relevance - Context terms generated ({len(context_terms)}): {context_terms[:20]}...") # Log first few terms

            # --- Check against URL components ---
            url_lower = url.lower()
            
            # Handle different types of url_signals input
            search_query = ""
            if isinstance(url_signals, dict):
                # If url_signals is a dictionary, get search_query from it
                search_query = url_signals.get('search_query', '')
            elif isinstance(url_signals, str):
                # If url_signals is a string, treat it as the search query directly
                search_query = url_signals
            
            # I weight a search query match at 0.5, in the block below,
            # over a plain URL match at 0.3. The query holds words I typed
            # for the task. The URL mostly holds the site's own naming, so
            # it says less about what I am doing.
            # Check full URL (weight: 0.3)
            for term in context_terms:
                if term in url_lower:
                    relevance['score'] += 0.3
                    relevance['matched_terms'].append(term)
                    relevance['matches'].append({'term': term, 'location': 'url', 'weight': 0.3})

            # Check search query (higher weight: 0.5)
            if search_query:
                query_lower = search_query.lower()
                logger.debug(f"_check_context_relevance - Checking search query: '{query_lower}'")
                
                for term in context_terms:
                    if term in query_lower:
                        relevance['score'] += 0.5
                        relevance['matched_terms'].append(term)
                        relevance['matches'].append({'term': term, 'location': 'search_query', 'weight': 0.5})

            # --- TODO: Future Enhancement: Check Website Content ---
            # Placeholder for fetching and analyzing title/meta description/body text
            # try:
            #     page_content = self._fetch_website_text(url) # Implement this helper
            #     if page_content:
            #         content_lower = page_content.lower()
            #         for term in context_terms:
            #             if term in content_lower:
            #                 relevance['score'] += 0.2 # Lower weight for general content match
            #                 relevance['matched_terms'].append(term)
            #                 relevance['matches'].append({'term': term, 'location': 'content', 'weight': 0.2})
            # except Exception as fetch_err:
            #     logger.warning(f"_check_context_relevance - Could not fetch or analyze content for {url}: {fetch_err}")

            # Normalize score (cap at 1.0) and deduplicate terms
            relevance['score'] = min(1.0, round(relevance['score'], 2))
            relevance['matched_terms'] = sorted(list(set(relevance['matched_terms']))) # Sort for consistency

            logger.debug(f"_check_context_relevance - END - Relevance result: {relevance}")
            return relevance

        except Exception as e:
            logger.error(f"_check_context_relevance - Error: {e}", exc_info=True)
            relevance['error'] = str(e)
            return relevance


    def _categorize_domain(self, hostname: str) -> str:
        """Categorize domain type based on hostname patterns."""
        hostname = hostname.lower() # Ensure lowercase

        # Prioritize more specific categories first
        # The order of these checks is the rule, not a style choice.
        # Education and documentation hosts are tested before the search
        # engine line, and the Google line splits workspace hosts away
        # from plain search. Moving a line changes answers.
        if any(term in hostname for term in ['.edu', '.ac.', 'school', 'learn', 'course', 'study', 'academic', 'khanacademy', 'coursera', 'udemy', 'blackboard', 'canvas', 'moodle']):
            return 'educational'
        if any(term in hostname for term in ['wiki', 'docs.', 'developer.', 'reference', 'stackexchange', 'stackoverflow', 'github.io', 'mdn.']):
            return 'documentation/reference'
        if any(term in hostname for term in ['github.com', 'gitlab.com', 'bitbucket.org', 'dev.azure', 'dev.to']):
             return 'development/code'
        if any(term in hostname for term in ['google.com', 'bing.com', 'duckduckgo.com', 'startpage.com', 'search.']): # Add specific search engines
             if 'google.com' in hostname and any(sub in hostname for sub in ['docs.', 'sheets.', 'slides.', 'drive.', 'mail.', 'calendar.']):
                  return 'productivity/tools' # Google Workspace tools are productivity
             return 'search engine'
        if any(term in hostname for term in ['mail.', 'calendar.', 'drive.', 'office.com', 'microsoft365.com', 'onedrive.', 'dropbox', 'notion.', 'evernote', 'trello', 'asana', 'jira', 'slack', 'zoom.us', 'teams.microsoft']):
             return 'productivity/tools'
        if any(term in hostname for term in ['news', 'cnn', 'bbc', 'nytimes', 'reuters', 'wsj', 'guardian']):
             return 'news/media'
        if any(term in hostname for term in ['facebook', 'twitter', 'instagram', 'linkedin', 'reddit', 'pinterest', 'tiktok']):
            return 'social media'
        if any(term in hostname for term in ['youtube', 'netflix', 'hulu', 'twitch', 'spotify', 'vimeo']):
             return 'streaming/entertainment'
        if any(term in hostname for term in ['amazon', 'ebay', 'walmart', 'target', 'etsy', 'shopping']):
             return 'e-commerce/shopping'
        if any(term in hostname for term in ['game', 'steam', 'origin', 'playstation', 'xbox', 'nintendo', 'ign']):
             return 'gaming'

        # Default if no specific category matches
        return 'general'

    def analyze_website(self, url: str, domain: str) -> dict: # Return dict now
        """Analyze if a website is productive based on domain settings, context, and AI.

        Returns:
            dict: {'isProductive': bool, 'explanation': str, 'confidence': float (optional)}
        """
        logger.debug(f"analyze_website - START - URL: {url}, Domain: {domain}")
        
        # Security validation. Note: "domain" here is a configured
        # profile name (work, school, personal), not a hostname, so it is
        # checked against settings keys rather than hostname syntax.
        if not InputValidator.validate_url(url):
            logger.warning(f"Invalid URL provided for analysis: {url}")
            return {'isProductive': False, 'explanation': 'Invalid URL format.'}

        domain = InputValidator.sanitize_string(domain, 100)
        if domain not in self.settings.get("domains", {}):
            logger.warning(f"Unknown domain profile provided for analysis: {domain}")
            return {'isProductive': False, 'explanation': f"Configuration for domain '{domain}' not found."}
        
        # Rate limiting check - prevent too many requests in short time
        current_time = datetime.now()
        if not hasattr(self, '_last_analysis_times'):
            self._last_analysis_times = []
        
        # Remove old timestamps (older than 1 minute)
        self._last_analysis_times = [
            t for t in self._last_analysis_times 
            if current_time - t < timedelta(minutes=1)
        ]
        
        # This limit lives on the analyzer object, in memory. It counts
        # calls on this one instance only, so it stops a tight local loop.
        # It is not a network defense. The Flask layer carries its own
        # limiter for requests that arrive over HTTP.
        # Check if too many requests in the last minute
        if len(self._last_analysis_times) > 50:  # Max 50 requests per minute
            logger.warning(f"Rate limit exceeded for analyze_website")
            return {'isProductive': False, 'explanation': 'Rate limit exceeded. Please try again later.'}
        
        self._last_analysis_times.append(current_time)

        # --- Initial Checks ---
        base_domain = self._get_domain_from_url(url)
        if not base_domain:
            logger.warning(f"analyze_website - Cannot analyze URL without a valid domain: {url}")
            # Cannot be productive if URL is invalid
            return {'isProductive': False, 'explanation': 'Invalid URL format.'}

        if domain not in self.settings.get("domains", {}):
            logger.error(f"analyze_website - Domain '{domain}' configuration not found in settings.")
            # Cannot analyze without domain settings
            return {'isProductive': False, 'explanation': f"Configuration for domain '{domain}' not found."}

        settings = self.settings["domains"][domain]

        # I keep the order in this method fixed: allowed platforms, then
        # blocked specifics, then blocked keywords, then context, then AI
        # or the local fallback. A host that matches both an allowed
        # platform and a blocked specific is allowed, because step 1
        # returns before step 2 runs. That outcome is my choice.
        # --- 1. Check Explicitly Allowed Platforms ---
        if self._is_allowed_platform(url, domain):
            logger.info(f"analyze_website - ALLOWED: URL '{url}' matches an allowed platform for domain '{domain}'.")
            return {'isProductive': True, 'explanation': f"Allowed platform for '{domain}' domain."}

        # --- 2. Check Explicitly Blocked Specific URLs/Domains ---
        blocked_specific = settings.get("blocked_specific", [])
        if isinstance(blocked_specific, list):
            for blocked in blocked_specific:
                if not isinstance(blocked, str): continue
                # Check if the blocked rule matches the base domain or the full URL
                if base_domain.endswith(blocked.lower()) or url.lower() == blocked.lower():
                    logger.info(f"analyze_website - BLOCKED: URL '{url}' matches blocked specific rule '{blocked}' for domain '{domain}'.")
                    return {'isProductive': False, 'explanation': f"Blocked specific rule: '{blocked}'."}
        else:
            logger.warning(f"analyze_website - 'blocked_specific' is not a list for domain '{domain}'.")

        # --- 3. Check Blocked Keywords in URL ---
        blocked_keywords = settings.get("blocked_keywords", [])
        url_lower = url.lower()
        if isinstance(blocked_keywords, list):
            for keyword in blocked_keywords:
                if not isinstance(keyword, str): continue
                if keyword.lower() in url_lower:
                    logger.info(f"analyze_website - BLOCKED: URL '{url}' contains blocked keyword '{keyword}' for domain '{domain}'.")
                    return {'isProductive': False, 'explanation': f"Blocked keyword found: '{keyword}'."}
        else:
            logger.warning(f"analyze_website - 'blocked_keywords' is not a list for domain '{domain}'.")


        # --- 4. Contextual Analysis (if applicable) ---
        contextualization_required = settings.get("contextualization_required", domain == "personal") # Default to True for personal
        # Context check runs if required AND context data exists
        run_context_check = contextualization_required and self.context_data

        context_relevance = {'score': 0.0} # Default score if no context check
        url_signals = self._analyze_url_components(url) # Analyze components once

        if run_context_check:
            context_relevance = self._check_context_relevance(url, url_signals)
            logger.debug(f"analyze_website - Context relevance result: {context_relevance}")

            # Decision based on high context relevance
            if context_relevance.get('score', 0.0) > 0.7: # Ensure default is 0.0 for comparison
                matched_terms_str = ', '.join(context_relevance.get('matched_terms',[]))
                explanation = f"High context relevance ({context_relevance['score']}). Matched: {matched_terms_str}"
                logger.info(f"analyze_website - ALLOWED: {explanation} for URL '{url}'.")
                return {'isProductive': True, 'explanation': explanation}

        # --- 5. AI Analysis (Borderline Cases or when context is insufficient) ---
        # Condition to use AI:
        # - Context exists AND relevance score is moderate (0.3 to 0.7)
        # - OR Contextualization is required but context is empty (needs AI to decide based on URL alone vs. generic productivity)
        # - OR Contextualization is *not* required (e.g., work/school) and URL didn't hit explicit allow/block rules.
        use_ai = (run_context_check and 0.3 <= context_relevance.get('score', 0.0) <= 0.7) or \
                 (contextualization_required and not self.context_data) or \
                 (not contextualization_required) # Use AI if not explicitly allowed/blocked and context isn't needed/used

        if use_ai and not self.ai_available:
            # No API key configured: decide with local rules only, and say so.
            logger.info(f"analyze_website - AI unavailable, using local fallback for URL: {url}")
            return self._local_fallback_decision(url, url_signals, context_relevance)

        if use_ai:
            logger.debug(f"analyze_website - Proceeding to AI analysis for URL: {url}")
            try:
                context_summary = "No specific task context provided."
                if self.context_data:
                     # Ensure context_data is serializable (it should be dict)
                     try:
                         context_summary = json.dumps(self.context_data, indent=2)
                     except TypeError as json_err:
                         logger.error(f"analyze_website - Context data not JSON serializable: {json_err}")
                         context_summary = "Error: Context data could not be formatted."


                # Prepare detailed prompt for AI
                analysis_prompt = f"""Analyze if visiting this URL is productive for the user in the '{domain}' domain, considering their current task context (if provided).

                Domain Policy Context:
                - Current Domain: {domain}
                - Explicitly Allowed Platforms (already checked): LMS, Productivity Tools, AI Tools defined for '{domain}'
                - Explicitly Blocked Keywords (already checked): {settings.get("blocked_keywords", [])}
                - Explicitly Blocked Specific Sites (already checked): {settings.get("blocked_specific", [])}

                User Task Context:
                {context_summary}

                URL Under Review:
                - URL: {url}
                - Detected Hostname: {url_signals.get('hostname', 'N/A')}
                - Detected Category: {url_signals.get('domain_type', 'N/A')}
                - Is Search?: {url_signals.get('is_search', 'N/A')}
                - Search Query: {url_signals.get('search_query', 'N/A')}
                - Context Relevance Score: {context_relevance.get('score', 'N/A')} (if applicable)
                - Context Matched Terms: {context_relevance.get('matched_terms', 'N/A')} (if applicable)

                Analysis Goal: Determine if accessing this URL is directly related to completing the user's stated task (if provided) OR is generally considered productive/necessary within the '{domain}' domain (e.g., documentation, core tools) and isn't explicitly blocked. Block common time-wasting sites (social media, games, excessive entertainment) unless context strongly justifies it.

                Respond with exactly 'ALLOW' or 'BLOCK' followed by a concise reason.
                Format: <ALLOW|BLOCK>: <Reasoning based on URL, context, and domain policy.>
                Example ALLOW: ALLOW: Accessing Python documentation is relevant to the programming task.
                Example BLOCK: BLOCK: Social media site is not related to the work task and is generally blocked in the 'work' domain.
                """

                logger.debug("analyze_website - AI Analysis Prompt:\n" + analysis_prompt)

                decision = self._generate_text(analysis_prompt)
                logger.info(f"analyze_website - AI Analysis Result for {url}: {decision}")

                # Parse AI decision
                if ':' in decision:
                    verdict, explanation = decision.split(':', 1)
                    verdict = verdict.strip().upper()
                    explanation = explanation.strip()

                    if verdict == 'ALLOW':
                        logger.info(f"analyze_website - AI Verdict: ALLOW. Reason: {explanation}")
                        # Log additional details for successful analysis that might be useful for debugging direct visits
                        logger.info(f"analyze_website - AI ALLOWED: URL={url}, DOMAIN={domain}, EXPLANATION={explanation}")
                        return {'isProductive': True, 'explanation': explanation} # Return dict
                    elif verdict == 'BLOCK':
                        logger.info(f"analyze_website - AI Verdict: BLOCK. Reason: {explanation}")
                        # Log additional details for unsuccessful analysis
                        logger.info(f"analyze_website - AI BLOCKED: URL={url}, DOMAIN={domain}, EXPLANATION={explanation}")
                        return {'isProductive': False, 'explanation': explanation} # Return dict
                    else:
                        explanation = f"AI returned unexpected verdict '{verdict}'."
                        logger.warning(f"analyze_website - {explanation} Defaulting to BLOCK.")
                        return {'isProductive': False, 'explanation': explanation} # Return dict
                else:
                    explanation = f"AI response format incorrect ('ALLOW:' or 'BLOCK:' expected). Response: '{decision}'."
                    logger.warning(f"analyze_website - {explanation} Defaulting to BLOCK.")
                    return {'isProductive': False, 'explanation': explanation} # Return dict

            except Exception as e:
                # Do not leak internal exception text to the client and do
                # not hard-block every unknown site: fall back to the same
                # local rules used when no key is configured.
                logger.error(f"analyze_website - AI analysis failed for {url}, using local fallback: {e}", exc_info=True)
                return self._local_fallback_decision(url, url_signals, context_relevance)

        # --- 6. Default Decision ---
        # If we reach here, it means:
        # - Not explicitly allowed or blocked by settings.
        # - Contextualization wasn't required OR context score was low (<0.3).
        # - AI analysis wasn't triggered or wasn't applicable.
        # In this scenario, default to blocking unless context strongly suggested otherwise (which it didn't).
        explanation = "Blocked by default rules (no specific allow match or low context relevance)."
        logger.info(f"analyze_website - BLOCKED (Default): URL '{url}'. Reason: {explanation}")
        return {'isProductive': False, 'explanation': explanation} # Return dict


# --- Main Execution Logic ---
def main():
    logger.info("main - START - Script execution started.")
    try:
        analyzer = ProductivityAnalyzer()

        while True:
            domain_input = input("Enter domain (work/school/personal) or 'quit': ").lower().strip()
            if domain_input == 'quit':
                logger.info("main - User chose to quit.")
                break
            if domain_input in analyzer.settings.get("domains", {}):
                domain = domain_input
                logger.debug(f"main - User selected valid domain: {domain}")

                # Check if contextualization is needed for this domain
                settings = analyzer.settings["domains"][domain]
                contextualization_required = settings.get("contextualization_required", domain == "personal") # Default to True for personal

                if contextualization_required:
                     print(f"\nContextualization needed for '{domain}' domain.")
                     analyzer.contextualize(domain) # Run context gathering
                     logger.info("main - Contextualization completed for domain: {domain}")
                else:
                     analyzer.context_data = {} # Ensure context is clear if not required
                     print(f"\nContextualization not required for '{domain}' domain based on settings.")
                     logger.info(f"main - Contextualization skipped for domain: {domain}")

                # Loop for URL analysis within the selected domain
                while True:
                    url = input(f"\nEnter URL to analyze in '{domain}' domain (or 'back' to change domain, 'quit' to exit): ").strip()
                    if url.lower() == 'quit':
                        logger.info("main - User chose to quit.")
                        return # Exit main function completely
                    if url.lower() == 'back':
                        logger.info("main - User chose to go back to domain selection.")
                        break # Break URL loop to re-enter domain loop
                    if not url:
                         print("Please enter a URL.")
                         continue
                    if not url.startswith(('http://', 'https://')):
                        print("URL must start with http:// or https://")
                        continue


                    logger.info(f"main - Analyzing URL: {url} in domain: {domain}")
                    analysis_result = analyzer.analyze_website(url, domain)
                    result_text = 'PRODUCTIVE' if analysis_result['isProductive'] else 'NOT PRODUCTIVE'
                    print(f"\n>>> Analysis Result for '{url}': {result_text} for your current context/domain.")
                    print(f"Explanation: {analysis_result['explanation']}")
                    logger.info(f"main - Analysis for URL: {url} - Result: {result_text}, Explanation: {analysis_result['explanation']}")

            else:
                print("Invalid domain. Please choose from work, school, or personal (or 'quit').")
                logger.warning(f"main - User entered invalid domain: {domain_input}")

    except FileNotFoundError as e:
         logger.critical(f"main - CRITICAL ERROR: Required file not found: {e}. Exiting.")
         print(f"\nERROR: Could not find required file: {e}")
    except Exception as e:
        logger.critical(f"main - An unexpected error occurred: {e}", exc_info=True)
        print(f"\nAn unexpected error occurred: {e}")

    logger.info("main - END - Script execution finished.")

if __name__ == "__main__":
    main()