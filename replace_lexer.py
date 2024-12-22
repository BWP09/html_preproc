import enum

class TokenType(enum.Enum):
    SOF             = 0
    EOF             = 1
    CONTENT         = 2
    START           = 3
    END             = 4
    VALUE           = 5

class Token:
    def __init__(self, type_: TokenType, value: str | None = None) -> None:
        self.type_ = type_
        self.value = value if value else ""
    
    def __repr__(self) -> str:
        def pad(s: str, n: int) -> str:
            return s + (n - len(s)) * " "
        
        return f"Token(type='{pad(self.type_.name, max(map(len, TokenType._member_names_)))}'{f", value='{self.value}'" if self.value else ""})"

class ReplaceTokenizer:
    def __init__(self, start: str, end: str) -> None:
        self._start = start
        self._end = end
        
        self.clear()
    
    def clear(self) -> None:
        self.text = ""
        self.tokens: list[Token] = [Token(TokenType.SOF)]
        
    def tokenize(self, text: str, indent_spaces: int = 4) -> list[Token]:
        self.text = text

        def next_factory(text: str):
            def next_(pos: int, amount: int):
                if pos + amount > len(text):
                    return None
                
                return "".join([text[pos + i] for i in range(amount)])
            
            return next_
            
        next_text = next_factory(text)
        
        cc = 0

        while cc < len(text):
            char = text[cc]

            if self.tokens[-1].type_ == TokenType.VALUE and next_text(cc, len(self._end)) == self._end:
                self.tokens.append(Token(TokenType.END))
                cc += len(self._end) - 1

            elif self.tokens[-1].type_ == TokenType.VALUE:
                self.tokens[-1].value += char

            elif next_text(cc, len(self._start)) == self._start:
                self.tokens.append(Token(TokenType.START))
                self.tokens.append(Token(TokenType.VALUE))
                
                cc += len(self._start) - 1

            elif self.tokens[-1].type_ == TokenType.CONTENT:
                self.tokens[-1].value += char

            elif self.tokens[-1].type_ in [TokenType.SOF, TokenType.END]:
                self.tokens.append(Token(TokenType.CONTENT, char))

            cc += 1

        self.tokens.append(Token(TokenType.EOF))

        return self.tokens

def grammar_check(tokens: list[Token]) -> tuple[bool, int]:
    len_ = len(tokens)
    
    for i in range(len(tokens)):
        match tokens[i].type_:
            case TokenType.SOF:
                if i + 1 < len_ and not tokens[i + 1].type_ in [TokenType.CONTENT, TokenType.START]:
                    return False, i
            
            case TokenType.CONTENT:
                if i + 1 < len_ and not tokens[i + 1].type_ in [TokenType.START, TokenType.EOF]:
                    return False, i
                
            case TokenType.START:
                if i + 1 < len_ and not tokens[i + 1].type_ in [TokenType.VALUE, TokenType.END]:
                    return False, i
            
            case TokenType.VALUE:
                if i + 1 < len_ and not tokens[i + 1].type_ in [TokenType.END]:
                    return False, i
                
            case TokenType.END:
                if i + 1 < len_ and not tokens[i + 1].type_ in [TokenType.CONTENT, TokenType.EOF]:
                    return False, i

    return True, 0

if __name__ == "__main__":
    lexer = ReplaceTokenizer("#[", "]")
    tokens = lexer.tokenize("#[]")
    
    print("\n".join([repr(token) for token in tokens]))
    print(grammar_check(tokens))