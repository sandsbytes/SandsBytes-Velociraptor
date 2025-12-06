import json
import requests
from typing import Dict, Any, Optional
import logging
import urllib3
from functools import partial
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTTPClient:
    """
    A dynamic HTTP client that reads configuration and provides method-based API access.
    """
    
    def __init__(self, base_url: str, auth_path: str = "/auth/login", config_file: str = "config.json", ignore_ssl: bool = False):
        """
        Initialize the HTTP client.
        
        Args:
            base_url: The base URL of the API
            auth_path: The authentication endpoint path
            config_file: Path to the configuration JSON file
            ignore_ssl: Whether to ignore SSL certificate verification
        """
        self.base_url = base_url.rstrip('/')
        self.auth_path = auth_path
        self.session = requests.Session()
        self.access_token = None
        self.username = None
        self.password = None
        self.config = self._load_config(config_file)
        self._build_dynamic_methods()
        self.ignore_ssl = ignore_ssl
        if self.ignore_ssl:
            self.session.verify = False

            
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_file} not found")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return {}
    
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with the server and store the access token.
        
        Args:
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        # Store credentials for potential re-authentication
        self.username = username
        self.password = password
        
        auth_url = self.base_url + self.auth_path
        try:
            response = self.session.post(
                auth_url,
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token') or data.get('token')
                
                if self.access_token:
                    # Set the authorization header for future requests
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.access_token}"
                    })
                    logger.info("Authentication successful")
                    return True
                else:
                    logger.error("No access token found in response")
                    return False
            else:
                logger.error(f"Authentication failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Authentication request failed: {e}")
            return False
    
    def _is_token_expired_error(self, response: requests.Response) -> bool:
        """
        Check if the response indicates a token expiration error.
        
        Args:
            response: The HTTP response to check
            
        Returns:
            bool: True if token is expired, False otherwise
        """
        # Check for common token expiration indicators
        if response.status_code in [401, 403]:
            try:
                response_data = response.json()
                error_message = response_data.get('error', '').lower()
                error_description = response_data.get('error_description', '').lower()
                message = response_data.get('message', '').lower()
                
                # Check for various token expiration messages
                token_expired_indicators = ['Token has expired']
                
                for indicator in token_expired_indicators:
                    if (indicator in error_message or 
                        indicator in error_description or 
                        indicator in message):
                        return True
                        
            except (ValueError, KeyError):
                # If we can't parse JSON, check the raw text
                response_text = response.text.lower()
                if 'Token has expired' in response_text:
                    return True
        
        return False
    
    def _re_authenticate(self) -> bool:
        """
        Attempt to re-authenticate using stored credentials.
        
        Returns:
            bool: True if re-authentication successful, False otherwise
        """
        if not self.username or not self.password:
            logger.error("Cannot re-authenticate: no stored credentials")
            return False
        
        logger.info("Token expired, attempting to re-authenticate...")
        return self.authenticate(self.username, self.password)
    
    def _build_dynamic_methods(self):
        """Build dynamic methods based on configuration."""
        for resource_name, methods in self.config.items():
            # Create a resource class
            resource_class = type(resource_name.capitalize(), (), {})
            
            for method_name, method_config in methods.items():
                # Create a partial function that captures the current values
                method_func = partial(self._make_request, resource_name, method_name, method_config)
                setattr(resource_class, method_name, method_func)
            
            # Attach the resource class to the main client
            setattr(self, resource_name, resource_class())
    
    def _make_request(self, resource_name: str, method_name: str, method_config: Dict[str, Any], **kwargs) -> requests.Response:
        """
        Make an HTTP request based on the method configuration.
        
        Args:
            resource_name: Name of the resource (e.g., 'cases', 'users')
            method_name: Name of the method (e.g., 'create', 'delete')
            method_config: Configuration for the method
            **kwargs: Parameters for the request
            
        Returns:
            requests.Response: The HTTP response
        """
        path = method_config['path']
        http_method = method_config['method']
        
        # Replace path parameters
        for key, value in kwargs.items():
            if f"{{{key}}}" in path:
                path = path.replace(f"{{{key}}}", str(value))
        
        # Build the full URL
        url = self.base_url + path
        
        # Prepare request parameters
        params = kwargs.get('params', {})
        data = kwargs.get('data', {})
        json_data = kwargs.get('json', {})
        headers = kwargs.get('headers', {})
        files = kwargs.get('files', {})
        
        # Add headers to session
        if headers:
            self.session.headers.update(headers)
        
        # Maximum number of retry attempts for token expiration
        max_retries = 1
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Making {http_method} request to {url} (attempt {attempt + 1})")
                
                if http_method.upper() == 'GET':
                    response = self.session.get(url, params=params)
                elif http_method.upper() == 'POST':
                    response = self.session.post(url, params=params, data=data, json=json_data, files=files)
                elif http_method.upper() == 'PUT':
                    response = self.session.put(url, params=params, data=data, json=json_data, files=files)
                elif http_method.upper() == 'PATCH':
                    response = self.session.patch(url, params=params, data=data, json=json_data, files=files)
                elif http_method.upper() == 'DELETE':
                    response = self.session.delete(url, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {http_method}")
                
                logger.info(f"Response status: {response.status_code}")
                
                # Check if token expired and we can retry
                if (attempt < max_retries and 
                    self._is_token_expired_error(response) and 
                    self._re_authenticate()):
                    logger.info("Re-authentication successful, retrying request...")
                    continue
                

                try:
                    return response.json()
                except:
                    return response
                
            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                raise
    
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self.access_token is not None
    
    def logout(self):
        """Clear the authentication token and stored credentials."""
        self.access_token = None
        self.username = None
        self.password = None
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
        logger.info("Logged out successfully")


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    client = HTTPClient("https://api.example.com")
    
    # Authenticate
    if client.authenticate("username", "password"):
        print("Authentication successful!")
        
        # Use the dynamic methods
        try:
            # Create a case
            response = client.cases.create(json={"title": "Test Case", "description": "Test Description"})
            print(f"Create case response: {response.status_code}")
            
            # Get a case
            response = client.cases.get(case_id=4)
            print(f"Get case response: {response.status_code}")
            
            # Delete a case
            response = client.cases.delete(case_id=4)
            print(f"Delete case response: {response.status_code}")
            
            # Get a user
            response = client.users.get(user_id=1)
            print(f"Get user response: {response.status_code}")
            
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Authentication failed!") 