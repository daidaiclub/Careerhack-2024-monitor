CREATE TABLE cloud_run_service (
  region TEXT NOT NULL,
  project_id TEXT NOT NULL,
  service_name TEXT NOT NULL,
  channel_id TEXT,
  lastest_llm_query_time TEXT,
  guild_id TEXT,
  PRIMARY KEY (region, project_id, service_name)
);
