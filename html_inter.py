import string, enum

class LexTokenType(enum.Enum):
    SOF             = 0
    EOF             = 1
    COMMENT_START   = 2
    COMMENT_END     = 3
    COMMENT_BODY    = 4
    TAG_OPEN_START  = 5
    TAG_CLOSE_START = 6
    TAG_END         = 7
    TAG_NAME        = 8
    TAG_ATTR_NAME   = 9
    TAG_ATTR_EQUALS = 10
    TAG_ATTR_VALUE  = 11
    CONTENT         = 12
    CODE            = 13
    NEWLINE         = 14
    INDENT          = 15

class LexToken:
    def __init__(self, type_: LexTokenType, value: str | None = None) -> None:
        self.type_ = type_
        self.value = value if value else ""
    
    def __repr__(self, pad_names: bool = True) -> str:
        def pad(s: str, n: int) -> str:
            return s + (n - len(s)) * " "
        
        name = self.type_.name

        if pad_names:
            name = pad(self.type_.name, max(map(len, LexTokenType._member_names_)))

        return f"LexToken(type='{name}'{f", value='{self.value}'" if self.value else ""})"

class HTMLTokenizer:
    def __init__(self) -> None:
        self.clear()
    
    def clear(self) -> None:
        self.html = ""
        self.tokens: list[LexToken] = [LexToken(LexTokenType.SOF)]
        
    def tokenize(self, html: str) -> list[LexToken]:
        self.html = html

        def next_factory(text: str):
            def next_(pos: int, amount: int):
                if pos + amount > len(text):
                    return None
                
                return "".join([text[pos + i] for i in range(amount)])
            
            return next_
            
        next_html = next_factory(html)
        
        cc = 0

        while cc < len(html):
            char = html[cc]

            if self.tokens[-1].type_ == LexTokenType.COMMENT_START:
                self.tokens.append(LexToken(LexTokenType.COMMENT_BODY, char))

            elif self.tokens[-1].type_ == LexTokenType.COMMENT_BODY and next_html(cc, 3) == "-->":
                self.tokens.append(LexToken(LexTokenType.COMMENT_END))
                cc += 2

            elif self.tokens[-1].type_ == LexTokenType.COMMENT_BODY:
                self.tokens[-1].value += char

            elif next_html(cc, 4) == "<!--":
                self.tokens.append(LexToken(LexTokenType.COMMENT_START))
                cc += 3
            
            elif next_html(cc, 2) == "</":
                self.tokens.append(LexToken(LexTokenType.TAG_CLOSE_START))
                cc += 1
            
            elif self.tokens[-1].type_ == LexTokenType.CODE:
                self.tokens[-1].value += char
            
            elif char == "<":
                self.tokens.append(LexToken(LexTokenType.TAG_OPEN_START))
            
            elif char == ">":
                self.tokens.append(LexToken(LexTokenType.TAG_END))
            
            elif self.tokens[-1].type_ == LexTokenType.TAG_NAME and char in string.ascii_letters + string.digits + "!":
                self.tokens[-1].value += char
            
            elif self.tokens[-1].type_ in [LexTokenType.TAG_OPEN_START, LexTokenType.TAG_CLOSE_START] and char in string.ascii_letters + "!" :
                self.tokens.append(LexToken(LexTokenType.TAG_NAME, char))
            
            elif self.tokens[-1].type_ == LexTokenType.TAG_ATTR_NAME and char in string.ascii_letters + "-_":
                self.tokens[-1].value += char
            
            elif self.tokens[-1].type_ in [LexTokenType.TAG_NAME, LexTokenType.TAG_ATTR_NAME] and char == " ":
                self.tokens.append(LexToken(LexTokenType.TAG_ATTR_NAME))
            
            elif self.tokens[-1].type_ == LexTokenType.TAG_ATTR_VALUE and next_html(cc - 1, 2) == "\" ":
                self.tokens.append(LexToken(LexTokenType.TAG_ATTR_NAME))

            elif self.tokens[-1].type_ == LexTokenType.TAG_ATTR_NAME and char == "=":
                self.tokens.append(LexToken(LexTokenType.TAG_ATTR_EQUALS))

            elif self.tokens[-1].type_ == LexTokenType.TAG_ATTR_VALUE and char in string.ascii_letters + string.digits + string.punctuation + " ":
                if char != "\"":
                    self.tokens[-1].value += char
            
            elif self.tokens[-1].type_ == LexTokenType.TAG_ATTR_EQUALS and char == "\"":
                self.tokens.append(LexToken(LexTokenType.TAG_ATTR_VALUE))

            elif len(self.tokens) >= 3 and self.tokens[-3].type_ == LexTokenType.TAG_OPEN_START \
                and (t := self.tokens[-2]).type_ == LexTokenType.TAG_NAME and t.value in ["script", "style"]:
                self.tokens.append(LexToken(LexTokenType.CODE, char))

            elif char == "\n":
                self.tokens.append(LexToken(LexTokenType.NEWLINE))

            elif self.tokens[-1].type_ == LexTokenType.CONTENT:
                self.tokens[-1].value += char
            
            elif self.tokens[-1].type_ in [LexTokenType.TAG_END, LexTokenType.NEWLINE, LexTokenType.INDENT] and char != " ":
                self.tokens.append(LexToken(LexTokenType.CONTENT, char))
            
            elif self.tokens[-1].type_ == LexTokenType.INDENT and char == " ":
                self.tokens[-1].value = str(int(self.tokens[-1].value) + 1)
                
            elif char == " ":
                self.tokens.append(LexToken(LexTokenType.INDENT, "1"))

            cc += 1

        self.tokens.append(LexToken(LexTokenType.EOF))

        return self.tokens

UNPAIRED_TAGS: list[str] = [
    "!DOCTYPE",
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
]

class AST_Token:
    def __init__(self, name: str | None = None, attrs: list[tuple[str, str]] | None = None, data: str | None = None, children: list["AST_Token"] | None = None) -> None:
        self.name = name if name else ""
        self.attrs = attrs if attrs else []
        self.data = data if data else ""
        self.children = children if children else []

    def __repr__(self) -> str:
        return f"AST_Token(name={self.name!r}, attrs={self.attrs!r}, data={self.data!r}, children={self.children!r})"
    
    def tree(self, indent_spaces: int = 2) -> str:
        output = f"TAG {self.name}:"

        def build_tree(ast_token: AST_Token, depth: int = 1):
            nonlocal output

            for child in ast_token.children:
                attrs = f" ({", ".join([f"\"{attr[0]}={attr[1]}\"" if attr[1] else f"\"{attr[0]}\"" for attr in child.attrs])})" if child.attrs else ""
                data = f"\n{" " * indent_spaces * (depth + 1)}DATA \"{child.data}\"" if child.data else ""

                output += f"\n{" " * indent_spaces * depth}TAG {child.name}{attrs}{":" if child.data or child.children else ""}{data}"

                build_tree(child, depth + 1)

        build_tree(self)

        return output
    
    def is_empty(self, ignore_data: bool = False) -> bool:
        return bool(self.name) \
            and bool(self.attrs) \
            and (bool(self.data) or ignore_data) \
            and bool(self.children)

class HTML_AST_Builder:
    def __init__(self) -> None:
        pass

    def build(self, lex_tokens: list[LexToken]) -> AST_Token:
        root: AST_Token = AST_Token(name="<ROOT>")
        path: list[AST_Token] = [root]

        i = 0
        while i < len(lex_tokens):
            token = lex_tokens[i]

            match token.type_:
                case LexTokenType.TAG_OPEN_START:
                    ast_token = AST_Token(name = lex_tokens[i + 1].value)

                    if path[-1].name in UNPAIRED_TAGS:
                        path.pop()

                    path[-1].children.append(ast_token)
                    path.append(ast_token)
                
                case LexTokenType.TAG_CLOSE_START:
                    path.pop()

                case LexTokenType.TAG_ATTR_NAME:
                    if lex_tokens[i + 2].type_ == LexTokenType.TAG_ATTR_VALUE:
                        path[-1].attrs.append((token.value, lex_tokens[i + 2].value))

                        i += 2
                    
                    else:
                        path[-1].attrs.append((token.value, ""))


                case LexTokenType.CONTENT:
                    path[-1].children.append(AST_Token(name = "<DATA>", data = token.value))
                
                case LexTokenType.CODE:
                    path[-1].children.append(AST_Token(name = "<DATA>", data = token.value))
                
                case LexTokenType.COMMENT_BODY:
                    path[-1].children.append(AST_Token(name = "<COMMENT>", data = token.value))

            i += 1

        return root


class HTMLBuilder:
    def __init__(self) -> None:
        self.clear()
    
    def clear(self) -> None:
        self.tokens = []
        self.html = ""

    def build(self, ast_root_token: AST_Token, indent_spaces: int = 4) -> str:
        html = ""

        def indent(depth: int):
            return " " * indent_spaces * depth

        def build_html(ast_token: AST_Token, depth: int = 0):
            nonlocal html

            for child in ast_token.children:
                attrs = (" " + " ".join([f"{attr[0]}=\"{attr[1]}\"" if attr[1] else attr[0] for attr in child.attrs])) if child.attrs else ""                

                if child.name == "<DATA>":
                    html += f"\n{indent(depth)}{child.data}"
                
                elif child.name == "<COMMENT>":
                    html += f"\n{indent(depth)}<!--{child.data}-->"

                else:
                    html += f"\n{indent(depth)}<{child.name}{attrs}>"

                    if child.name not in UNPAIRED_TAGS:
                        build_html(child, depth + 1)

                        html += f"\n{indent(depth)}</{child.name}>"

        build_html(ast_root_token)

        return html.removeprefix("\n") + "\n"