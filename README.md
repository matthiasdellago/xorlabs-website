# XOR Labs site

Plain static site, no build step. Served by GitHub Pages.

```
index.html        single page: mission, publications, people
styles.css        all styling
xor-logo.svg      the XOR mark (also the favicon)
CNAME             custom domain (xorlabs.org)
```

## Edit
Everything is in `index.html`. The people list is a placeholder (core team
from the SFF application); add or remove `<li>` rows as needed. Set the real
contact address in the footer.

## Deploy (GitHub Pages)
1. Create a public repo and push these files to `main`.
2. Settings -> Pages -> Source: `Deploy from a branch`, branch `main`, folder `/ (root)`.
3. The site goes live at `https://<user>.github.io/<repo>/` within a minute.

## Custom domain
Once you own the domain, create a `CNAME` file containing just that domain
(e.g. `xorlabs.org`), commit it, then at your DNS provider add either:
- an `ALIAS`/`ANAME` (or `CNAME` on a subdomain) to `<user>.github.io`, or
- four `A` records to GitHub's Pages IPs: 185.199.108.153, 185.199.109.153,
  185.199.110.153, 185.199.111.153.
