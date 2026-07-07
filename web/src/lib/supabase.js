/**
 * Supabase Client Configuration
 *
 * Initializes the Supabase client for authentication and database access.
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim();
const isLocalSupabaseMode = import.meta.env.VITE_IN_LOCAL_SUPABASE_MODE === 'true';

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables. Please check your .env.local file.');
}

// Validate key format
if (!isLocalSupabaseMode && !supabaseAnonKey.startsWith('eyJ')) {
  console.error('❌ Invalid Supabase anon key format! Key must start with "eyJ" (JWT format)');
  console.error('Key starts with:', supabaseAnonKey.substring(0, 10));
  throw new Error('Invalid Supabase anon key format. Please check your VITE_SUPABASE_ANON_KEY in .env.local');
}

// Validate URL format
if (!isLocalSupabaseMode && (!supabaseUrl.startsWith('https://') || !supabaseUrl.includes('.supabase.co'))) {
  console.error('❌ Invalid Supabase URL format!');
  console.error('URL should be: https://xxxxxxxxxxxxx.supabase.co');
  console.error('Actual URL:', supabaseUrl);
  throw new Error('Invalid Supabase URL format. Please check your VITE_SUPABASE_URL in .env.local');
}

// Debug: Log configuration (remove after debugging - DO NOT log full keys in production)
if (import.meta.env.DEV) {
  console.log('✅ Supabase Config:', {
    url: supabaseUrl,
    urlLength: supabaseUrl?.length,
    keyLength: supabaseAnonKey?.length,
    keyPrefix: supabaseAnonKey?.substring(0, 20) + '...',
    keySuffix: '...' + supabaseAnonKey?.substring(supabaseAnonKey.length - 10),
    keyStartsWithJWT: supabaseAnonKey?.startsWith('eyJ'),
    keyEndsWithValid: supabaseAnonKey?.length > 100,
    isLocalSupabaseMode,
  });
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  }
});
