"""
Supabase Database Client

Initializes and provides access to the Supabase client for database operations.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment. "
        "Check your .env file."
    )

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)


def get_supabase_client() -> Client:
    """
    Get the Supabase client instance.

    Returns:
        Client: Supabase client for database operations
    """
    return supabase
