We don't use _Dataset_ queues, only separate queues for the different kind of tasks (see [known defers](./reference/defer.md))

This introduces an expected problem as Procrastinate will process tasks _first in, first out_: A small job triggered from the UI might have to wait 2 weeks until many (long running) jobs for another dataset are finished.

To avoid this, we assign a random priority to each job during deferring. UI-Triggered (User CRUD) jobs get a higher random priority.

The randomness range can be configured for each _known task queue_ via it's settings:

    OPENALEPH_INDEX_DEFER_MIN_PRIORITY=75

- [Defer settings reference](./reference/defer.md)
- [Read more about priorities in procrastinate docs](https://procrastinate.readthedocs.io/en/stable/howto/advanced/priorities.html)
