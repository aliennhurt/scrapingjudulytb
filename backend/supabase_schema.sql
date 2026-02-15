-- Enable UUID extension (usually enabled by default in Supabase, but good practice)
create extension if not exists "uuid-ossp";

-- Table: runs
create table runs (
    id uuid primary key default uuid_generate_v4(),
    keyword text not null,
    hl text default 'id',
    gl text default 'ID',
    status text default 'queued',
    started_at timestamp with time zone default timezone('utc'::text, now()),
    finished_at timestamp with time zone,
    error_message text
);

-- Table: videos
create table videos (
    id uuid primary key default uuid_generate_v4(),
    run_id uuid not null references runs(id) on delete cascade,
    source_type text not null,
    rank integer not null,
    title text not null,
    channel_name text not null,
    video_id text not null,
    video_url text not null,
    views_raw text not null,
    views_num bigint,
    published_raw text,
    duration_raw text,
    collected_from text not null,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Table: templates
create table templates (
    id uuid primary key default uuid_generate_v4(),
    run_id uuid not null references runs(id) on delete cascade,
    template_text text not null,
    example_1 text,
    example_2 text
);

-- Indexes for performance
create index idx_runs_keyword on runs(keyword);
create index idx_videos_run_id on videos(run_id);
create index idx_templates_run_id on templates(run_id);
