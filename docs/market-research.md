# Market and competitor research

The research stage does not only look for papers. It also looks for what
already exists: open-source projects, launch threads and, with a key,
commercial products. The findings and opportunities that follow name those
alternatives and the gaps they leave.

Every item is a real record returned by a service, with a link you can open.
Nothing here comes from the model's memory, and the research stage rejects any
draft that cites something that was not retrieved.

## Sources

| Source | Finds | Key needed |
| --- | --- | --- |
| GitHub | Open-source projects that already do something similar, with stars and last activity | No (a token raises the rate limit) |
| Hacker News | Launch threads and discussions about existing products | No |
| Brave Search | Commercial products and competitor pages across the web | Yes |

Papers (arXiv, OpenAlex, Semantic Scholar) are searched as before. Up to five
papers and up to five market items go into each research proposal.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `ATLAS_RESEARCH_MARKET_SOURCES` | `true` | Search for existing products as well as papers |
| `ATLAS_RESEARCH_MAX_MARKET_CANDIDATES` | `5` | Market items kept per proposal |
| `ATLAS_GITHUB_TOKEN` | unset | Optional, raises GitHub's search limit |
| `ATLAS_BRAVE_API_KEY` | unset | Turns on web search for commercial competitors |

The project's keywords are sent to GitHub, Hacker News and, if configured,
Brave. Set `ATLAS_RESEARCH_MARKET_SOURCES=false` to keep research to papers.

## How the search works

GitHub and Hacker News only return items that match every word, so a long,
specific query finds nothing. Each source tries the first four keywords of the
project, then three, then two, and keeps the first set of results.

Evidence from these sources has the type `repository`, `discussion` or
`web page`, and its citation says so, for example
`owner/name [repository]. https://github.com/owner/name`.

## Limits

- GitHub and Hacker News find open-source projects and discussions. Without a
  Brave key, commercial competitors that are not open source will be missed.
- Stars and points show attention, not quality or market size.
- ATLAS does not estimate market size, pricing or demand.
- The citation eval in `evals/citations` turns market research off so its
  numbers stay about papers.
