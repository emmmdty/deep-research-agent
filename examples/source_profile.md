# Source Profiles

Source profiles live in `configs/source_profiles/`.

- `company_trusted`: company research with trusted public domains.
- `company_broad`: company research with broader public retrieval.
- `industry_trusted`: industry research with trusted public domains.
- `industry_broad`: industry research with broader public retrieval.
- `public_then_private`: public retrieval plus local file inputs when provided.
- `trusted_only`: stricter trusted-source retrieval.

Use a profile from the CLI:

```bash
uv run python main.py submit --topic "$(cat examples/topic.txt)" --source-profile company_trusted
```
