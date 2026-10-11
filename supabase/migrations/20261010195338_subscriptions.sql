-- One subscription row per signed-in user. Webhook URLs stay on that row.
-- The service role reads them when a digest is delivered. The browser never receives another user's URL.

create table public.subscriptions (
  user_id uuid primary key references auth.users (id) on delete cascade,
  teams_webhook_url text,
  slack_webhook_url text,
  active boolean not null default true,
  updated_at timestamptz not null default now(),
  constraint subscriptions_teams_https check (
    teams_webhook_url is null or teams_webhook_url ~ '^https://'
  ),
  constraint subscriptions_slack_https check (
    slack_webhook_url is null or slack_webhook_url ~ '^https://'
  )
);

alter table public.subscriptions enable row level security;

grant select, insert, update, delete on table public.subscriptions to authenticated;

create policy "subscribers read their row"
  on public.subscriptions
  for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy "subscribers insert their row"
  on public.subscriptions
  for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy "subscribers update their row"
  on public.subscriptions
  for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "subscribers delete their row"
  on public.subscriptions
  for delete
  to authenticated
  using ((select auth.uid()) = user_id);
