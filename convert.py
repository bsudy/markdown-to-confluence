from typing import Any, Tuple, Union
from record import Article
import mistune
import os
import textwrap
import yaml
import logging
import html
from urllib.parse import urlparse

log = logging.getLogger(__name__)

YAML_BOUNDARY = '---'


def parse(path: str) -> Tuple[dict, str]:
    raw_yaml = ''
    markdown = ''
    in_yaml = False
    with open(path, 'r') as post:
        line_count = 0
        for line in post.readlines():
            line_count += 1
            if line_count == 1 and line.strip() == YAML_BOUNDARY:
                log.debug('Starting with Front matter')
                in_yaml = True
                continue
            # Check if this is the ending tag
            if line.strip() == YAML_BOUNDARY:
                log.debug('End of Front matter')
                if in_yaml:
                    in_yaml = False
                    continue
            if in_yaml:
                raw_yaml += line
            else:
                markdown += line
    log.debug('Front matter: {}'.format(raw_yaml))
    front_matter = yaml.load(raw_yaml, Loader=yaml.SafeLoader)
    markdown = markdown.strip()
    return front_matter or {}, markdown


class ConfluenceRenderer(mistune.Renderer):#
    full_with_template = textwrap.dedent('''
        <ac:layout-section ac:type=\"fixed-width\" ac:breakout-mode=\"default\">
            <ac:layout-cell>
                {}
            </ac:layout-cell>
        </ac:layout-section>
    ''')

    two_column_template = textwrap.dedent('''
        <ac:layout-section ac:type=\"two_left_sidebar\" ac:breakout-mode=\"default\">
            <ac:layout-cell>
                {sidebar}
            </ac:layout-cell><ac:layout-cell>
                {main_content}
            </ac:layout-cell>
        </ac:layout-section>
    ''')

    page_template = textwrap.dedent('''
            <ac:layout>
                {}
            </ac:layout>
        ''')

    def __init__(self, article: Article, authors=[], warning: Union[bool, str] = True, render_toc: bool = True, two_column_layout: bool = False):
        self.attachments = []
        if authors is None:
            authors = []
        self.authors = authors
        self.has_toc = False
        self.render_toc = render_toc
        self.article = article
        self.warning = warning
        self.two_column_layout = two_column_layout
        super().__init__()

    def layout(self, content: str) -> str:
        """Renders the final layout of the content.
        """

        # Ignore the TOC if we haven't processed any headers to avoid making a
        # blank one
        if self.has_toc and self.render_toc:
            toc = textwrap.dedent('''
                <h1>Table of Contents</h1>
                <p><ac:structured-macro ac:name="toc" ac:schema-version="1">
                    <ac:parameter ac:name="exclude">^(Authors|Table of Contents)$</ac:parameter>
                </ac:structured-macro></p>
            ''')
        else:
            toc = ''

        authors = self.render_authors()

        warning = self._render_warning()

        if self.two_column_layout and (toc or authors):
            # Render two column
            if warning:
                warning = self.full_with_template.format(warning)

            content = self.page_template.format(
                warning
                + self.two_column_template.format(
                    sidebar=toc + authors,
                    main_content=content
                )
            )
        else:
            content = warning + toc + authors + content

        return content

    def _render_warning(self):
        if self.warning:
            warning_template = "<ac:structured-macro ac:name=\"note\" ac:schema-version=\"1\" ac:macro-id=\"f5f3fbe6-6a62-4eb2-867b-3e1254cef301\"><ac:rich-text-body><p>{copy}</p></ac:rich-text-body></ac:structured-macro>"
            if self.warning == True:
                warning_copy = "This page is automatically generated and can be overwritten. Please don't modify it here."
            else:
                warning_copy = self.warning

            print('Warning copy {}'.format(warning_copy))
            return warning_template.format(copy=html.escape(warning_copy))
        else:
            return ''

    def header(self, text, level, raw=None):
        """Processes a Markdown header.

        In our case, this just tells us that we need to render a TOC. We don't
        actually do any special rendering for headers.
        """
        self.has_toc = True
        return super().header(text, level, raw)

    def render_authors(self):
        """Renders a header that details which author(s) published the post.

        This is used since Confluence will show the post published as our
        service account.
        
        Arguments:
            author_keys {str} -- The Confluence user keys for each post author
        
        Returns:
            str -- The HTML to prepend to the post specifying the authors
        """
        if len(self.authors) > 0:
            author_template = '''<ac:structured-macro ac:name="profile-picture" ac:schema-version="1">
                    <ac:parameter ac:name="User"><ri:user ri:userkey="{user_key}" /></ac:parameter>
                </ac:structured-macro>&nbsp;
                <ac:link><ri:user ri:userkey="{user_key}" /></ac:link>'''
            author_content = '<br />'.join(
                author_template.format(user_key=user_key)
                for user_key in self.authors)
            return '<h1>Authors</h1><p>{}</p>'.format(author_content)
        else:
            return ''

    def block_code(self, code, lang):
        return textwrap.dedent('''\
            <ac:structured-macro ac:name="code" ac:schema-version="1">
                <ac:parameter ac:name="language">{l}</ac:parameter>
                <ac:plain-text-body><![CDATA[{c}]]></ac:plain-text-body>
            </ac:structured-macro>
        ''').format(c=code, l=lang or '')

    def image(self, src, title, alt_text):
        """Renders an image into XHTML expected by Confluence.

        Arguments:
            src {str} -- The path to the image
            title {str} -- The title attribute for the image
            alt_text {str} -- The alt text for the image

        Returns:
            str -- The constructed XHTML tag
        """
        # Check if the image is externally hosted, or hosted as a static
        # file within Journal
        is_external = bool(urlparse(src).netloc)
        tag_template = '<ac:image>{image_tag}</ac:image>'
        image_tag = '<ri:url ri:value="{}" />'.format(src)
        if not is_external:
            # TODO I don't think image path should be like that.
            image_path = os.path.normpath(os.path.join(self.article.absolute_director, src))
            image_tag = '<ri:attachment ri:filename="{}" />'.format(
                os.path.basename(image_path))
            log.debug('Found attachment: {}'.format(image_path))
            self.attachments.append(image_path)
        return tag_template.format(image_tag=image_tag)
