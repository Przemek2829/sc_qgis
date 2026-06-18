import re


class SCUrlValidator:

    @staticmethod
    def validateUrl(url, line_edit=None):
        url_pattern = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
        url_match = re.match(url_pattern, url)
        if line_edit is not None:
            if url_match:
                line_edit.setStyleSheet('color: rgb(0, 0, 0);')
            else:
                line_edit.setStyleSheet('color: rgb(255, 0, 0);')
            if url.strip() == '':
                line_edit.setStyleSheet('color: rgb(125, 125, 125);')
        return url_match
