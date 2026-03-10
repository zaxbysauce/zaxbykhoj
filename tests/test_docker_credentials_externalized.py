"""
Test suite to verify all credentials in docker-compose.yml are externalized.
Checks that no hardcoded secrets are present and all sensitive values use environment variable substitution.
"""

import pytest
import yaml
from pathlib import Path


# Path to the docker-compose file
DOCKER_COMPOSE_PATH = Path(__file__).parent.parent / "khoj-repo" / "docker-compose.yml"

# List of credential-like environment variable names that should be externalized
CREDENTIAL_VARS = [
    "POSTGRES_PASSWORD",
    "POSTGRES_USER", 
    "POSTGRES_DB",
    "KHOJ_DJANGO_SECRET_KEY",
    "DJANGO_SECRET_KEY",
    "DJANGO_ADMIN_EMAIL",
    "DJANGO_ADMIN_PASSWORD",
    "E2B_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "SERPER_DEV_API_KEY",
    "OLOSTEP_API_KEY",
    "FIRECRAWL_API_KEY",
    "EXA_API_KEY",
    # Additional common credential patterns
    "API_KEY",
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "CREDENTIAL",
]


def load_docker_compose():
    """Load and parse the docker-compose.yml file."""
    with open(DOCKER_COMPOSE_PATH, 'r') as f:
        return yaml.safe_load(f)


def is_credential_var(var_name: str) -> bool:
    """Check if an environment variable name suggests it's a credential."""
    var_upper = var_name.upper()
    return any(pattern in var_upper for pattern in CREDENTIAL_VARS)


def is_externalized(value: str) -> bool:
    """
    Check if a value is properly externalized using environment variable substitution.
    Accepts formats like: ${VAR} or ${VAR:-default}
    """
    if not isinstance(value, str):
        return True  # Non-string values are fine
    
    # Check for environment variable substitution pattern
    if value.startswith('${') and '}' in value:
        return True
    
    return False


def has_hardcoded_secret(value: str) -> bool:
    """
    Check if a value appears to be a hardcoded secret.
    Returns True if the value looks like an actual secret (not a placeholder).
    """
    if not isinstance(value, str):
        return False
    
    # Skip if it's already externalized
    if is_externalized(value):
        return False
    
    # Skip placeholders like "postgres" which are default/example values
    placeholder_patterns = ['postgres', 'localhost', 'your_', 'example.com']
    if any(pattern in value.lower() for pattern in placeholder_patterns):
        return False
    
    # Check for patterns that look like real secrets
    secret_patterns = [
        r'^[a-zA-Z0-9]{20,}$',  # Long alphanumeric strings
        r'^[A-Za-z0-9+/]{20,}={0,2}$',  # Base64-like strings
    ]
    
    import re
    for pattern in secret_patterns:
        if re.match(pattern, value):
            return True
    
    return False


class TestCredentialsExternalized:
    """Test suite to verify all credentials are externalized."""

    def test_docker_compose_exists(self):
        """Verify the docker-compose.yml file exists."""
        assert DOCKER_COMPOSE_PATH.exists(), f"docker-compose.yml not found at {DOCKER_COMPOSE_PATH}"

    def test_docker_compose_valid_yaml(self):
        """Verify the docker-compose.yml is valid YAML."""
        try:
            compose = load_docker_compose()
            assert compose is not None
            assert 'services' in compose
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML: {e}")

    def test_database_credentials_externalized(self):
        """Verify database credentials are externalized."""
        compose = load_docker_compose()
        database_env = compose.get('services', {}).get('database', {}).get('environment', [])
        
        # Convert list to dict if needed
        if isinstance(database_env, list):
            env_dict = {}
            for item in database_env:
                if '=' in item:
                    key, value = item.split('=', 1)
                    env_dict[key] = value
            database_env = env_dict
        
        # Check critical database credentials
        assert 'POSTGRES_PASSWORD' in database_env, "POSTGRES_PASSWORD not found"
        assert is_externalized(database_env['POSTGRES_PASSWORD']), \
            f"POSTGRES_PASSWORD is not externalized: {database_env['POSTGRES_PASSWORD']}"
        
        assert 'POSTGRES_USER' in database_env, "POSTGRES_USER not found"
        assert is_externalized(database_env['POSTGRES_USER']), \
            f"POSTGRES_USER is not externalized: {database_env['POSTGRES_USER']}"

    def test_server_django_secret_key_externalized(self):
        """Verify Django secret key is externalized."""
        compose = load_docker_compose()
        server_env = compose.get('services', {}).get('server', {}).get('environment', [])
        
        # Convert list to dict if needed
        if isinstance(server_env, list):
            env_dict = {}
            for item in server_env:
                if '=' in item:
                    key, value = item.split('=', 1)
                    env_dict[key] = value
            server_env = env_dict
        
        # Find KHOJ_DJANGO_SECRET_KEY
        secret_key = None
        for key, value in server_env.items():
            if 'DJANGO_SECRET_KEY' in key:
                secret_key = value
                break
        
        assert secret_key is not None, "KHOJ_DJANGO_SECRET_KEY not found in server environment"
        assert is_externalized(secret_key), \
            f"KHOJ_DJANGO_SECRET_KEY is not externalized: {secret_key}"

    def test_server_admin_credentials_externalized(self):
        """Verify admin email and password are externalized."""
        compose = load_docker_compose()
        server_env = compose.get('services', {}).get('server', {}).get('environment', [])
        
        # Convert list to dict if needed
        if isinstance(server_env, list):
            env_dict = {}
            for item in server_env:
                if '=' in item:
                    key, value = item.split('=', 1)
                    env_dict[key] = value
            server_env = env_dict
        
        # Check admin email
        admin_email = server_env.get('KHOJ_ADMIN_EMAIL')
        assert admin_email is not None, "KHOJ_ADMIN_EMAIL not found"
        assert is_externalized(admin_email), \
            f"KHOJ_ADMIN_EMAIL is not externalized: {admin_email}"
        
        # Check admin password
        admin_password = server_env.get('KHOJ_ADMIN_PASSWORD')
        assert admin_password is not None, "KHOJ_ADMIN_PASSWORD not found"
        assert is_externalized(admin_password), \
            f"KHOJ_ADMIN_PASSWORD is not externalized: {admin_password}"

    def test_no_hardcoded_secrets_in_all_services(self):
        """Verify no hardcoded secrets exist in any service environment variables."""
        compose = load_docker_compose()
        services = compose.get('services', {})
        
        hardcoded_secrets = []
        
        for service_name, service_config in services.items():
            environment = service_config.get('environment', [])
            
            # Convert list to dict if needed
            if isinstance(environment, list):
                env_dict = {}
                for item in environment:
                    if '=' in item:
                        key, value = item.split('=', 1)
                        env_dict[key] = value
                environment = env_dict
            
            for var_name, var_value in environment.items():
                # Skip non-credential variables
                if not is_credential_var(var_name):
                    continue
                
                # Check for hardcoded secrets
                if has_hardcoded_secret(var_value):
                    hardcoded_secrets.append(f"{service_name}.{var_name}={var_value}")
        
        assert len(hardcoded_secrets) == 0, \
            f"Found hardcoded secrets: {hardcoded_secrets}"

    def test_postgres_connection_credentials_externalized(self):
        """Verify Postgres connection credentials in server service are externalized."""
        compose = load_docker_compose()
        server_env = compose.get('services', {}).get('server', {}).get('environment', [])
        
        # Convert list to dict if needed
        if isinstance(server_env, list):
            env_dict = {}
            for item in server_env:
                if '=' in item:
                    key, value = item.split('=', 1)
                    env_dict[key] = value
            server_env = env_dict
        
        # Check that connection credentials reference env vars or defaults
        assert 'POSTGRES_PASSWORD' in server_env, "POSTGRES_PASSWORD not in server environment"
        assert is_externalized(server_env['POSTGRES_PASSWORD']), \
            f"Server POSTGRES_PASSWORD is not externalized: {server_env['POSTGRES_PASSWORD']}"


class TestCredentialPatterns:
    """Additional tests for credential pattern detection."""

    def test_all_credential_env_vars_use_substitution(self):
        """Verify all credential-named environment variables use ${VAR} substitution."""
        compose = load_docker_compose()
        services = compose.get('services', {})
        
        violations = []
        
        for service_name, service_config in services.items():
            environment = service_config.get('environment', [])
            
            # Convert list to dict if needed
            if isinstance(environment, list):
                env_dict = {}
                for item in environment:
                    if '=' in item:
                        key, value = item.split('=', 1)
                        env_dict[key] = value
                environment = env_dict
            
            for var_name, var_value in environment.items():
                if is_credential_var(var_name):
                    if not is_externalized(var_value):
                        violations.append(f"{service_name}.{var_name}={var_value}")
        
        assert len(violations) == 0, \
            f"Credential variables not externalized: {violations}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
