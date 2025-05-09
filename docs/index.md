# OpenAleph Procrastinate

The most dumbest task queue for [OpenAleph](https://openaleph.org) based on [procrastinate](https://procrastinate.readthedocs.io/en/stable/)

## Background

There have been several attempts for implementing the task queuing within Aleph. Initially, it was a self-written `redis`-based implementation in [servicelayer](https://github.com/alephdata/servicelayer/), which switched to `rabbitmq` with Aleph v4 (which still involved `redis` a lot).

Based on the experiences with task queues in Aleph and other projects we have worked on, we decided to rewrite it for [OpenAleph](https://openaleph.org) once again, but this time using a 3rd party library, [procrastinate](https://procrastinate.readthedocs.io/en/stable/).

We hope to achieve the following goals with this approach:

- Use as much 3rd party components as possible
- Improve visibility/trackability of tasks
- Persistent task queue
- Reduce complexity of codebase, improve development and maintenance experience
- Don't implement & run our own workers if possible (leave all the (multi-)threading stuff to a 3rd party)
- Orchestration: Have different workers for different queues on different architectures
- Have the ability to deploy programs that just subscribe to a single task queue (such as geocoding or audio/video extraction)

## Get started

- [Setup](./setup.md)
- [Architecture](./architecture.md)
- [How to create a service](./howto.md)
- [Conventions](./setup.md)
