# Revenue Intelligence Council — Evaluation Report

**Evaluation mode:** synthetic replay  
**Last local result:** 4 tests passed on Python 3.12 with MCP SDK 2.0

| Check | Observed | Result |
|---|---:|---|
| Account scenarios grounded | 10/10 | Pass |
| Strategy claim IDs resolve | 100% | Pass |
| Draft claim IDs resolve | 100% | Pass |
| Low-fit scenario suppressed | Yes | Pass |
| Drafts marked draft-only | 100% | Pass |
| MCP tools | 3 read-only tools | Pass |
| MCP email or CRM tools | 0 | Pass |
| Mutations after approval | 0 | Pass |

## Public deployment verification

- Live URL: https://revenue-intelligence-council.vercel.app
- Runtime commit: `dd8b15194abd085e72c78660f7dfff015fae13b1`
- GitHub CI: pass
- Postman CLI against the commit-specific preview: 5 requests and 14 assertions, 0 failures
- Browser journeys: 1280×800 and 390×844, 0 console errors and 0 horizontal overflow
- Release: the tested preview artifact was promoted without rebuilding
