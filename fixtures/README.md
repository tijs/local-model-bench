Suites currently source straight from their real repo via `git worktree`
(repo path + base_ref live in each `tasks/<suite>.yaml`) — nothing needs to be
duplicated here. This directory is reserved for a suite that can't use
worktree mode (e.g. no usable git history) and needs a copied fixture
directory instead.
