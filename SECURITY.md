# Security policy

readme-runs executes the commands written in a Markdown file. By default they run inside a throwaway Docker container holding a copy of the project, so they can't modify your files. `--local` runs them on the host and should only be used on content you trust.

If you find a way for a README to escape this isolation or affect the host when not using `--local`, please report it privately through [GitHub's private vulnerability reporting](https://github.com/nicoleyangcoding/readme-runs/security/advisories/new) rather than opening a public issue. You can expect a reply within 7 days.
