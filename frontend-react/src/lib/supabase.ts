import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://ofeephkbumqlihdedtgt.supabase.co';
const supabaseAnonKey = 'sb_publishable_MERtO8ahC6dCpn6s8wN73g_nkTRoQtB';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
