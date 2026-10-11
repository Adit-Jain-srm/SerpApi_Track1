# Lessons

## One card from 63 URLs

The classifier was tightened so listicles are `not_ai_tool`. That was correct, and it also hid the real miss: those listicles were still fetched, and a launch article that named one product was not turned into a homepage fetch until later. Tightening the label does not create products.

Rule: spend the fetch on pages that can become a card. Drop obvious lists from the title before HTTP. Follow one named product URL. Do not loosen the model so a roundup counts as a tool.

## Review of that rank

A first cut treated any number as a list, including "1 AI tool" and "GPT-4", and it treated a list quoted in the snippet as the page itself. It also imported the extractor just to recognize a blog URL. The drop looks at the title (or the snippet only when the title is empty), counts from 3 up, and the article check lives in `agents/page_kind.py`.

## A second host is not a second product

The hop treated every extra registrable domain as a listicle. A font stylesheet, an image CDN, or a Cloudflare footer then erased the one real product URL, and the homepage was never fetched.

Rule: only anchors and URLs written in the text are product links. Infrastructure domains are not products. The publisher's own domain is not a second product. Several other product domains still means do not pick one. A multi-label suffix such as `.co.uk` is not the site. An anchor still counts when the closing tag was truncated.
