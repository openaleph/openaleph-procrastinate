# Architecture and design principles

## OpenAleph Procrastinate

`openaleph-procrastinate` acts as a shared library for _services_ that can handle tasks within the **OpenAleph** infrastructure. It holds a [`Job`](./reference/model.md) model (via [pydantic](https://docs.pydantic.dev/)), `procrastinate.App` logic and [helpers](./reference/helpers.md) for reading/writing archive files and followthemoney data via the [repository](./reference/repository.md).

This base library doesn't know about the actual queues and tasks. The worker services would have `openaleph-procrastinate` as a dependency and import the helpers and Job model from there.

For task inspection, `openaleph-procrastinate` provides the [manage](./reference/manage.md) module: dataset, batch, queue and task status aggregation plus bulk job operations, queried directly against the procrastinate tables and exposed via the [command line](./reference/cli.md).

## Services

Services subscribing to `openaleph_procrastinate` are completely independent programs that could run on separate (or same) infrastructure or as containers. They only need to be able to connect to the `postgresql` database holding the `procrastinate` task queue data.

Due to the possibility to defer `Jobs` to _unknown_ tasks (outside of the codebase of the current running service), `openaleph-procrastinate`, a _service_ and the _OpenAleph_ programs doesn't need to share much codebase, and by using mostly out-of-the-box logic from `procrastinate` the implementation stays simple and maintainable.
