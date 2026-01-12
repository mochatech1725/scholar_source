"""
Supabase Database Client

Initializes and provides access to the Supabase client for database operations.
"""

import os
from supabase import create_client, Client
from typing import Optional
from backend.env_loader import load_environment

# Load environment variables
load_environment()

# Get Supabase credentials from environment
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment. "
        "Check your .env file."
    )

# Initialize default Supabase client (for operations that don't need user context)
default_supabase: Client = create_client(supabase_url, supabase_key)

# Initialize service role client (bypasses RLS - for trusted server-side operations)
service_supabase: Optional[Client] = None
if supabase_service_key:
    service_supabase = create_client(supabase_url, supabase_service_key)


def get_supabase_client(access_token: Optional[str] = None, use_service_role: bool = False) -> Client:
    """
    Get the Supabase client instance.
    
    If an access_token is provided, creates a client authenticated with that token.
    This is required for RLS (Row Level Security) policies to work correctly.
    
    If use_service_role is True, returns a client with service role key (bypasses RLS).
    This should only be used for trusted server-side operations.
    
    Args:
        access_token: Optional JWT access token from authenticated user.
                    If provided, the client will be authenticated as that user.
        use_service_role: If True, use service role key (bypasses RLS). Default False.

    Returns:
        Client: Supabase client for database operations
    """
    if use_service_role:
        if not service_supabase:
            raise ValueError(
                "Service role client requested but SUPABASE_SERVICE_ROLE_KEY is not set. "
                "This is required for background operations."
            )
        return service_supabase
    
    if access_token:
        # Create a new client instance with the user's token for RLS
        # Set the Authorization header on the PostgREST client
        client = create_client(supabase_url, supabase_key)
        # Set the auth header for RLS to work
        client.postgrest.auth(access_token)
        return client
    return default_supabase
