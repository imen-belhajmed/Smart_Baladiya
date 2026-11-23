import re

import bleach
import markdown
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
    "br",
    "del",
    "h1",
    "h2",
    "h3",
    "hr",
    "mark",
    "p",
    "pre",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
}
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}
MEDIA_MARKER = re.compile(r"\[\[media:(\d+)\]\]")


@register.filter
def forum_markdown(value):
    if not value:
        return ""
    rendered = markdown.markdown(str(value), extensions=["extra"])
    clean_html = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return mark_safe(clean_html)


def _render_media(media, title):
    alt_or_title = media.caption or title
    if media.kind == media.Kind.IMAGE and media.file:
        return format_html(
            '<img class="thread-inline-image" src="{}" alt="{}" loading="lazy">',
            media.file.url,
            alt_or_title,
        )
    if media.kind == media.Kind.VIDEO and media.file:
        return format_html(
            '<video class="thread-inline-video" controls preload="metadata">'
            '<source src="{}" type="{}"></video>',
            media.file.url,
            media.file_content_type,
        )
    if media.embed_url:
        return format_html(
            '<iframe class="thread-inline-video" src="{}" title="{}" '
            'loading="lazy" referrerpolicy="strict-origin-when-cross-origin" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
            'gyroscope; picture-in-picture; web-share" allowfullscreen '
            'sandbox="allow-scripts allow-same-origin allow-presentation"></iframe>',
            media.embed_url,
            alt_or_title,
        )
    return ""


@register.simple_tag
def forum_thread_content(thread):
    media_by_position = {item.position: item for item in thread.media.all()}
    replacements = {}

    def replace_marker(match):
        media = media_by_position.get(int(match.group(1)))
        if media is None:
            return ""
        marker = f"FORUM_INLINE_MEDIA_{media.pk}_SAFE_MARKER"
        replacements[marker] = _render_media(media, thread.title)
        return marker

    source = MEDIA_MARKER.sub(replace_marker, thread.content)
    rendered = markdown.markdown(source, extensions=["extra"])
    clean_html = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    for marker, media_html in replacements.items():
        clean_html = clean_html.replace(marker, str(media_html))
    return mark_safe(clean_html)


@register.simple_tag
def forum_unplaced_media(thread):
    positions_in_content = {
        int(position)
        for position in MEDIA_MARKER.findall(thread.content)
    }
    return [
        item
        for item in thread.media.all()
        if item.position not in positions_in_content
    ]


@register.filter
def forum_media(media, title):
    return _render_media(media, title)
