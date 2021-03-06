# Copyright (C) 2011-2018  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file
import urwid
import os

from .buffer import Buffer
from ..settings.const import settings
from ..widgets.globals import HeadersList
from ..widgets.globals import AttachmentWidget
from ..helper import shorten_author_string
from ..helper import string_sanitize
from ..db.utils import render_part
from email.mime.text import MIMEText


class EnvelopeBuffer(Buffer):
    """message composition mode"""

    modename = 'envelope'

    def __init__(self, ui, envelope):
        self.ui = ui
        self.envelope = envelope
        self.all_headers = False
        self.displaypart = "plaintext"
        self.rebuild()
        Buffer.__init__(self, ui, self.body)

    def __str__(self):
        to = self.envelope.get('To', fallback='unset')
        return '[envelope] to: %s' % (shorten_author_string(to, 400))

    def get_info(self):
        info = {}
        info['to'] = self.envelope.get('To', fallback='unset')
        info['displaypart'] = self.displaypart
        return info

    def cleanup(self):
        if self.envelope.tmpfile:
            os.unlink(self.envelope.tmpfile.name)

    def rebuild(self):
        displayed_widgets = []
        hidden = settings.get('envelope_headers_blacklist')
        # build lines
        lines = []
        for (k, vlist) in self.envelope.headers.items():
            if (k not in hidden) or self.all_headers:
                for value in vlist:
                    lines.append((k, value))

        # sign/encrypt lines
        if self.envelope.sign:
            description = 'Yes'
            sign_key = self.envelope.sign_key
            if sign_key is not None and len(sign_key.subkeys) > 0:
                description += ', with key ' + sign_key.uids[0].uid
            lines.append(('GPG sign', description))

        if self.envelope.encrypt:
            description = 'Yes'
            encrypt_keys = self.envelope.encrypt_keys.values()
            if len(encrypt_keys) == 1:
                description += ', with key '
            elif len(encrypt_keys) > 1:
                description += ', with keys '
            key_ids = []
            for key in encrypt_keys:
                if key is not None and key.subkeys:
                    key_ids.append(key.uids[0].uid)
            description += ', '.join(key_ids)
            lines.append(('GPG encrypt', description))

        if self.envelope.tags:
            lines.append(('Tags', ','.join(self.envelope.tags)))

        # add header list widget iff header values exists
        if lines:
            key_att = settings.get_theming_attribute('envelope', 'header_key')
            value_att = settings.get_theming_attribute('envelope',
                                                       'header_value')
            gaps_att = settings.get_theming_attribute('envelope', 'header')
            self.header_wgt = HeadersList(lines, key_att, value_att, gaps_att)
            displayed_widgets.append(self.header_wgt)

        # display attachments
        lines = []
        for a in self.envelope.attachments:
            lines.append(AttachmentWidget(a, selectable=False))
        if lines:
            self.attachment_wgt = urwid.Pile(lines)
            displayed_widgets.append(self.attachment_wgt)

        # message body
        txt = self._find_body_text()
        self.body_wgt = urwid.Text(string_sanitize(txt))
        displayed_widgets.append(self.body_wgt)
        self.body = urwid.ListBox(displayed_widgets)

    def toggle_all_headers(self):
        """Toggle visibility of all envelope headers."""
        self.all_headers = not self.all_headers
        self.rebuild()

    def _find_body_text(self):
        txt = "no such part!"
        if self.displaypart == "html":
            htmlpart = MIMEText(self.envelope.body_html, 'html', 'utf-8')
            txt = render_part(htmlpart)
        elif self.displaypart == "src":
            txt = self.envelope.body_html
        elif self.displaypart == "plaintext":
            txt = self.envelope.body_txt
        return txt

    def set_displaypart(self, part):
        """Update the view to display body part (plaintext, html, src).

        ..note:: This assumes that selv.envelope.body_html exists in case
        the requested part is 'html' or 'src'!
        """
        self.displaypart = part
        txt = self._find_body_text()
        self.body_wgt.set_text(txt)
