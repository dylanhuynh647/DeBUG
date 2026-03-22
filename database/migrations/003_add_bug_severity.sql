-- Add severity support to bugs and allow all roles to update bugs via API workflows.

-- 1) Create enum for bug severity when it doesn't exist.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'bug_severity' AND n.nspname = 'public'
    ) THEN
        CREATE TYPE public.bug_severity AS ENUM ('low', 'medium', 'high', 'critical');
    END IF;
END
$$;

-- 2) Add severity column with default and backfill existing rows.
ALTER TABLE public.bugs
    ADD COLUMN IF NOT EXISTS severity public.bug_severity;

UPDATE public.bugs
SET severity = 'medium'
WHERE severity IS NULL;

ALTER TABLE public.bugs
    ALTER COLUMN severity SET DEFAULT 'medium',
    ALTER COLUMN severity SET NOT NULL;

-- 3) Let all platform roles update bugs (needed for severity quick actions).
DROP POLICY IF EXISTS "Allow developers/admins to update bugs" ON public.bugs;

CREATE POLICY "Allow reporters/developers/admins to update bugs" ON public.bugs
    FOR UPDATE
    USING (get_user_role(auth.uid()) IN ('reporter', 'developer', 'admin'))
    WITH CHECK (get_user_role(auth.uid()) IN ('reporter', 'developer', 'admin'));
