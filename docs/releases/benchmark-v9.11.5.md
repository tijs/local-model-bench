# local-model-bench benchmark-v9.11.5

The score-summary exporter now checks for existing chart and metric files before
writing. It refuses to overwrite those artifacts, including dangling symlinks,
and preserves existing historical summary files. The regular
`results/AGENT_SUMMARY.md` remains the mutable current view; an existing symlink
at that path is refused. The check does not coordinate concurrent writers.

This is a reporting safeguard. It adds no model runs or scores; the published
four-model scored comparison remains the frozen benchmark-v9.10 cohort. MiniCPM
remains a historical result pending fresh comparable repeats.
