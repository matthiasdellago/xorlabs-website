# Adding a publication figure

Every entry under **Select Publications** carries the paper's *first figure*, with the
white page background knocked out to transparency so it sits on the site's off-white
(`--bg: #fbfbfa`) without a visible white rectangle.

`make-pub-figure.py` does the image work. The rest of this file is the surrounding
process, including the parts that are fiddly.

## 1. Get the figure

Preferred source is the publisher link the paper was given with. Publisher sites sit
behind Cloudflare and reject bare `curl`; a full browser header set usually gets
through:

```sh
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
curl -s --compressed -H "User-Agent: $UA" \
  -H 'Accept: image/avif,image/webp,image/*,*/*;q=0.8' \
  -H 'Referer: <the article page>' \
  -H 'Sec-Fetch-Dest: image' -H 'Sec-Fetch-Site: same-origin' \
  '<image url>' -o fig1.png
```

What has worked, per publisher:

- **MDPI** — serves figures directly, high resolution:
  `https://www.mdpi.com/<journal>/<article-id>/article_deploy/html/images/<article-id>-g001.png`
- **Royal Society, APS** — article pages and figure endpoints both return 403. Fall back
  to a PDF (below). For Royal Society titles the PMC mirror is fetchable and its HTML
  lists the figure files as `.../<article>-g1.jpg`, but those are small (~700 px wide),
  so a PDF render is usually better.
- **OpenReview** — workshop and conference papers that never reached arXiv live only here,
  and every endpoint (`/pdf`, `/attachment`, `api2`) answers a bot challenge, so no header
  set gets through. Open the PDF in a real browser and save it by hand.
- **PDF fallback** — the arXiv version. Find it via the API, e.g.
  `curl -sL --data-urlencode 'search_query=ti:"<title>"' -G http://export.arxiv.org/api/query`,
  then `curl -sL https://arxiv.org/pdf/<id> -o paper.pdf`. Vector figures render at
  whatever resolution you ask for, so this often beats the publisher's raster.

## 2. Locate the figure in the PDF

```sh
pdfinfo paper.pdf | grep Pages                     # `file` reports the wrong count
for p in $(seq 1 8); do
  echo -n "p$p: "; pdftotext -f $p -l $p paper.pdf - | grep -oE 'FIG\. 1|Figure 1' | head -1
done
pdftoppm -png -r 150 -f <page> -l <page> paper.pdf page   # render, then look at it
```

Read off a **generous** crop box from the 150 dpi render and scale it to your target
dpi (`×4` for 600 dpi, `×2.667` for 400). Generous is safe — the script trims to the
content afterwards. What is *not* safe is including anything else that isn't white:
the page number, the caption, a neighbouring column of text. Those survive the knockout
and get swept into the trim.

## 3. Process

```sh
./tools/make-pub-figure.py paper.pdf img/papers/<slug>.png \
    --page 4 --dpi 600 --crop 2560,380,4900,1450

./tools/make-pub-figure.py fig1.png img/papers/<slug>.png     # already-extracted image
```

The knockout rule, matching the five figures the site launched with: a pixel is
transparent iff **all of R, G and B are ≥ 240**, otherwise fully opaque. Alpha is
binary — no feathering — and transparent pixels keep their original RGB. The 240
threshold clears JPEG noise and off-white paper while leaving light greys (a legend
fill, a shaded ellipse) intact.

Aim for **2000–2800 px** wide, in line with the existing figures.

## 4. Check it

Composite onto the site background before trusting it, because a stray caption or a
clipped axis label is obvious here and invisible in the raw PNG:

```sh
python3 -c "
from PIL import Image
im = Image.open('img/papers/<slug>.png').convert('RGBA')
bg = Image.new('RGBA', im.size, (251,251,250,255)); bg.alpha_composite(im)
bg.convert('RGB').save('/tmp/check.png')"
```

## 5. Add the markup

In the Publications tab, newest first:

```html
<div class="pub">
  <a class="title" href="<publisher link>">Title in sentence case</a>
  <span class="meta">Surnames. Journal volume(issue), pages, year.</span>
  <img class="pub-fig pub-fig--wide" src="img/papers/<slug>.png" alt="… figure" loading="lazy">
</div>
```

Use `pub-fig--wide` (full column width) for figures wider than about 2:1, and
`pub-fig--square` (60% width, centred) for anything squarer.

## Height limit

**No figure may render taller than 192 px (`max-height: 12rem`).** The cap lives on
`.pub-fig` in `styles.css` and applies to every figure, so nothing here needs doing by
hand — but it governs which figures are worth using, so it is worth understanding.

The text column is 592 px wide (`--maxw: 40rem` less padding). A figure filling that
column is 192 px tall at an aspect ratio of **3.08:1**, which is the hinge:

- **Wider than ~3:1** — bounded by the column, fills the full width, cap never bites.
  On the current page: *AI in a vat* (592×170), *From monoliths* (592×151),
  *Semantic information* (592×190).
- **Squarer than that** — bounded by the cap and centred, so it renders *narrower* than
  the text column: a 2:1 figure comes out 384 px wide, a 1.5:1 figure 288 px.

The reasoning: an entry is a title, one line of metadata, and a figure. Much past 192 px
and the figure stops illustrating the entry and starts being the entry — the list reads
as a gallery and scanning six papers turns into scrolling. Holding every figure to a
single height also keeps the cards visually level, so no one entry looms over the rest.

Two practical consequences:

- **Prefer a wide, landscape figure.** A tall multi-panel stack shrinks to a small
  centred block and reads as an afterthought. Crop to the informative panel row instead
  of shipping the whole thing.
- **Check the labels survive.** A square-ish figure ends up under 300 px wide, so axis
  text set for a journal column can end up too small. If it does, crop tighter — that
  raises the aspect ratio, which buys back width.
- **A stacked two-panel figure can be re-laid-out side by side.** Crop each panel, then
  paste them into one transparent canvas with a gap of about 5% of the height. Keep the
  panels at their *native* relative scale and centre the shorter one vertically; scaling
  both to a common height makes whichever panel is shortest balloon and dominate. This is
  what *Inferring entropy production* does — its Fig. 2 is 0.9:1 stacked, 3.0:1 side by
  side. Only rearrange panels, never redraw them.

Source pixel dimensions are unrelated to any of this; they only set resolution, and the
2000–2800 px target above still stands.

`pub-fig--square` caps width at 60% independently of the height cap. It only bites for
aspect ratios between roughly 1.9:1 and 3:1; anything squarer is governed by the height
cap alone, which is why it makes no difference to the two square figures currently on
the page.
