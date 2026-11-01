from PySide6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name

class PygmentsSyntaxHighlighter(QSyntaxHighlighter):
    """Bridges Pygments lexers into PySide6's QSyntaxHighlighter framework."""
    def __init__(self, document, lexer_name, style_name="monokai"):
        super().__init__(document)
        self.set_lexer_and_style(lexer_name, style_name)

    def set_lexer_and_style(self, lexer_name, style_name):
        try:
            self.lexer = get_lexer_by_name(lexer_name)
        except Exception:
            self.lexer = get_lexer_by_name("text")
            
        try:
            self.style = get_style_by_name(style_name)
        except Exception:
            self.style = get_style_by_name("monokai")
            
        self._format_cache = {}
        self.rehighlight()

    def highlightBlock(self, text):
        try:
            tokens = lex(text, self.lexer)
        except Exception:
            return

        index = 0
        for token_type, value in tokens:
            length = len(value)
            if length == 0:
                continue

            fmt = self._format_cache.get(token_type)
            if fmt is None:
                fmt = QTextCharFormat()
                t = token_type
                while t:
                    t_style = self.style.style_for_token(t)
                    if t_style:
                        if t_style['color']:
                            fmt.setForeground(QColor(f"#{t_style['color']}"))
                        if t_style['bold']:
                            fmt.setFontWeight(QFont.Bold)
                        if t_style['italic']:
                            fmt.setFontItalic(True)
                        break
                    t = t.parent
                self._format_cache[token_type] = fmt

            self.setFormat(index, length, fmt)
            index += length
