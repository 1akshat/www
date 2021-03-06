import glob
from pathlib import Path
from typing import AsyncIterator, Iterable, Iterator, List

import aiofiles
import frontmatter as fm

from . import resources, settings
from .models import ContentItem, Frontmatter, MetaTag, Page


async def load_content() -> None:
    items = [item async for item in load_content_items()]
    resources.index.pages = build_pages(items)


def iter_content_paths() -> Iterator[Path]:
    pattern = str(settings.CONTENT_DIR / "**" / "*.md")
    for path in glob.glob(pattern, recursive=True):
        yield Path(path)


async def load_content_items() -> AsyncIterator[ContentItem]:
    for path in iter_content_paths():
        async with aiofiles.open(path) as f:
            content = await f.read()
            yield ContentItem(
                content=content, location=str(path.relative_to(settings.CONTENT_DIR)),
            )


def build_pages(items: List[ContentItem]) -> List[Page]:
    pages = []

    for page in _build_content_pages(items):
        pages.append(page)

    unique_tags = {tag for page in pages for tag in page.frontmatter.tags}

    for page in _generate_tag_pages(unique_tags):
        pages.append(page)

    return pages


def _build_content_pages(items: List[ContentItem]) -> Iterator[Page]:
    for item in items:
        post = fm.loads(item.content)
        html = resources.markdown.reset().convert(post.content)
        permalink = _build_permalink(item.location)
        frontmatter = Frontmatter(
            home=post.get("home", False),
            title=post["title"],
            description=post.get("description"),
            date=post.get("date"),
            image=post.get("image"),
            image_caption=post.get("image_caption"),
            tags=post.get("tags", []),
        )
        meta = _build_meta(permalink, frontmatter)

        yield Page(html=html, permalink=permalink, frontmatter=frontmatter, meta=meta)


def _generate_tag_pages(tags: Iterable[str]) -> Iterator[Page]:
    for tag in tags:
        frontmatter = Frontmatter(
            title=f"{tag.capitalize()} - {settings.SITE_TITLE}",
            description=f"Articles about #{tag}",
            tag=tag,
        )
        permalink = f"/tag/{tag}"
        meta = _build_meta(permalink, frontmatter)

        yield Page(permalink=permalink, frontmatter=frontmatter, meta=meta)


def _build_permalink(location: str) -> str:
    url, _, extension = location.partition(".")
    assert extension == "md"

    segments = url.split("/")
    assert segments

    return "/" + "/".join(segments)


def _build_meta(permalink: str, frontmatter: Frontmatter) -> List["MetaTag"]:
    url = f"https://florimond.dev/blog{permalink}"

    meta = [
        # General
        MetaTag(name="description", content=frontmatter.description),
        MetaTag(name="image", content=frontmatter.image),
        MetaTag(itemprop="name", content=frontmatter.title),
        MetaTag(itemprop="description", content=frontmatter.description),
        MetaTag(itemprop="image", content=frontmatter.image),
        # Twitter
        MetaTag(name="twitter:url", content=url),
        MetaTag(name="twitter:title", content=frontmatter.title),
        MetaTag(name="twitter:description", content=frontmatter.description),
        MetaTag(name="twitter:image", content=frontmatter.image),
        MetaTag(name="twitter:card", content="summary_large_image"),
        MetaTag(name="twitter:site", content="@florimondmanca"),
        # OpenGraph
        MetaTag(name="og:url", content=url),
        MetaTag(property="og:type", content="article"),
        MetaTag(property="og:title", content=frontmatter.title),
        MetaTag(property="og:description", content=frontmatter.description),
        MetaTag(property="og:image", content=frontmatter.image),
        MetaTag(property="og:site_name", content=settings.SITE_TITLE),
        MetaTag(property="article:published_time", content=frontmatter.date),
    ]

    for tag in frontmatter.tags:
        meta.append(MetaTag(property="article:tag", content=tag))

    return meta
