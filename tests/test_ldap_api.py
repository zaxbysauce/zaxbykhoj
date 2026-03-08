"""Tests for LDAP API endpoints."""
import pytest
from django.test import AsyncClient


@pytest.mark.asyncio
async def test_get_ldap_config_requires_admin():
    """Test that GET /api/settings/ldap requires admin access."""
    client = AsyncClient()
    
    # Non-admin user should get 403
    response = await client.get("/api/settings/ldap")
    assert response.status_code == 403


@pytest.mark.asyncio  
async def test_post_ldap_config_requires_admin():
    """Test that POST /api/settings/ldap requires admin access."""
    client = AsyncClient()
    
    data = {
        "server_url": "ldaps://ldap.example.com:636",
        "user_search_base": "OU=Users,DC=example,DC=com",
        "user_search_filter": "(sAMAccountName={username})",
        "use_tls": True,
        "tls_verify": True,
        "enabled": False
    }
    
    response = await client.post("/api/settings/ldap", data=data, content_type="application/json")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ldap_login_validates_input():
    """Test that LDAP login validates username and password."""
    client = AsyncClient()
    
    # Empty username should fail
    response = await client.post("/auth/ldap/login", data={
        "username": "",
        "password": "password"
    }, content_type="application/json")
    assert response.status_code == 422
    
    # Empty password should fail  
    response = await client.post("/auth/ldap/login", data={
        "username": "user",
        "password": ""
    }, content_type="application/json")
    assert response.status_code == 422
