# Publication validation

- Locked harness regression: 495 tests passed in 70.813 s.
- New report and model-only tests: Ruff check/format passed.
- New report: Astral ty passed with the locked Python environment.
- Modified lifecycle scripts: bash syntax checks passed.
- New pinned config: launcher dry run accepted exact model identity, separate
  Flint/JANGH gates, 512 MiB allocator cache cap, mmap and disabled compilation.
- Independent correctness, tests and simplicity review findings resolved;
  Kiem review 778c69f6-45d4-482e-8118-830b9fdaf48b.

The test log deliberately includes mocked failing gates and mocked chart
failures. Its final unittest result is OK; those cases never ran model work.
