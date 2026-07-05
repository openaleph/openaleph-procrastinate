# Command line

```
openaleph-procrastinate [OPTIONS] COMMAND [ARGS]...
```

## Options

| Option | Description |
| --- | --- |
| `--version` / `--no-version` | Show version `[default: no-version]` |
| `--settings` / `--no-settings` | Show current settings `[default: no-settings]` |
| `--install-completion` | Install completion for the current shell. |
| `--show-completion` | Show completion for the current shell, to copy it or customize the installation. |
| `--help` | Show this message and exit. |

## Commands

### defer-entities

Defer jobs for a stream of proxies

```
openaleph-procrastinate defer-entities [OPTIONS]
```

| Option | Type | Description |
| --- | --- | --- |
| `-i` | TEXT | Input uri, default stdin `[default: -]` |
| `-d` | TEXT | Dataset `[required]` |
| `-q` | TEXT | Queue name `[required]` |
| `-t` | TEXT | Task module path `[required]` |
| `--help` | | Show this message and exit. |

### defer-jobs

Defer jobs from an input json stream

```
openaleph-procrastinate defer-jobs [OPTIONS]
```

| Option | Type | Description |
| --- | --- | --- |
| `-i` | TEXT | Input uri, default stdin `[default: -]` |
| `--help` | | Show this message and exit. |

### init-db

Initialize procrastinate database schema

```
openaleph-procrastinate init-db [OPTIONS]
```

| Option | Type | Description |
| --- | --- | --- |
| `--help` | | Show this message and exit. |

### ensure-indexes

Ensure desired indexes exist and drop stale ones.

Runs db.configure() to create desired schema and indexes, then drops any indexes on procrastinate_jobs not in the known-good set.

Use --force to drop and recreate all custom indexes.

```
openaleph-procrastinate ensure-indexes [OPTIONS]
```

| Option | Type | Description |
| --- | --- | --- |
| `--force` | | Drop and recreate all custom indexes |
| `--help` | | Show this message and exit. |

### requeue-failed

Requeue failed jobs matching the given filters.

This command finds all jobs with status='failed' that match the optional filters (dataset, queue, task) and retries them by setting their status back to 'todo'.

```
openaleph-procrastinate requeue-failed [OPTIONS]
```

| Option | Type | Description |
| --- | --- | --- |
| `-d` | TEXT | Dataset |
| `-q` | TEXT | Queue name |
| `-t` | TEXT | Task module path |
| `--help` | | Show this message and exit. |

### requeue-stalled

Requeue stalled/orphaned jobs matching the given filters.

This command finds all jobs with status='doing' whose worker no longer exists (orphaned jobs) and retries them by setting their status back to 'todo'.

Orphaned jobs can occur when the foreign key constraint on worker_id is dropped (for performance) and workers are pruned before completing their jobs.

```
openaleph-procrastinate requeue-stalled [OPTIONS]
```

| Option | Type | Description |
| --- | --- | --- |
| `-d` | TEXT | Dataset |
| `-q` | TEXT | Queue name |
| `-t` | TEXT | Task module path |
| `--help` | | Show this message and exit. |
