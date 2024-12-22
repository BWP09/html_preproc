import os
from . import html_inter, util, replace_lexer

class ComponentNotFound(Exception):
    ...

class TemplateNotFound(Exception):
    ...

class MalformedSyntax(Exception):
    ...

class CircularDependency(Exception):
    ...

class HTML_Preprocessor:
    def __init__(self, preproc_dir: str, make_dirs: bool = True, file_cache: bool = True, live_reload: bool = False, start_seq: str = "#[", end_seq: str = "]", indent_spaces: int = 4) -> None:
        self._preproc_dir = preproc_dir
        self._templates_dir = f"{preproc_dir}/templates"
        self._components_dir = f"{preproc_dir}/components"
        self._cache_dir = f"{preproc_dir}/cache"

        self._make_dirs = make_dirs
        self._file_cache = file_cache
        self._live_reload = live_reload

        self._start_seq = start_seq
        self._end_seq = end_seq

        self._indent_spaces = indent_spaces

        if make_dirs:
            util.mkdir(self._templates_dir)
            util.mkdir(self._components_dir)

            if file_cache:
                util.mkdir(self._cache_dir)
        
        self._templates: dict[str, str] = {}
        self._components: dict[str, str] = {}

        self._load_count = 0
        self._cache_last_count = 1
        self._first_load = True

        self.load_files()

    def load_files(self) -> None:
        for file in os.listdir(self._components_dir):
            with open(f"{self._components_dir}/{file}", "r", encoding = "utf-8") as f:
                self._components[file.rsplit(".", maxsplit = 1)[0]] = f.read()

        for file in os.listdir(self._templates_dir):
            with open(f"{self._templates_dir}/{file}", "r", encoding = "utf-8") as f:
                self._templates[file] = f.read()

        self._load_count += 1
    
    def process(self, template: str, max_loop: int = 1000) -> str:
        if self._live_reload:
            self.load_files()
        
        cache_path = f"{self._cache_dir}/{template}"

        if self._file_cache and self._load_count == self._cache_last_count and not self._first_load and os.path.exists(cache_path):
            with open(cache_path, "r", encoding = "utf-8") as f:
                return f.read()
        
        if self._first_load:
            self._first_load = False

        template_text = self._templates.get(template)

        if template_text is None:
            raise TemplateNotFound(f"Couldn't find '{self._templates_dir}/{template}'")
    
        lexer = html_inter.HTMLTokenizer()
        tokens = lexer.tokenize(template_text)

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type_ in [html_inter.LexTokenType.CONTENT, html_inter.LexTokenType.CODE]:
                lexer = replace_lexer.ReplaceTokenizer(self._start_seq, self._end_seq)
                tokens_ = lexer.tokenize(token.value)

                correct_grammar, err_at = replace_lexer.grammar_check(tokens_)

                if not correct_grammar:
                    raise MalformedSyntax(f"Malformed token grammar at token#{err_at}: {tokens_[err_at]}")

                token.value = ""

                for token_ in tokens_:
                    match token_.type_:
                        case replace_lexer.TokenType.CONTENT:
                            token.value += token_.value

                        case replace_lexer.TokenType.VALUE:
                            component = self._components.get(token_.value)

                            if component is None:
                                raise ComponentNotFound(f"Couldn't find '{token_.value}' component")
                            
                            lexer2 = html_inter.HTMLTokenizer()
                            tokens2 = lexer2.tokenize(component)[1:-1]

                            tokens.pop(i)

                            tokens[i:i] = tokens2
                
            if i >= max_loop:
                raise CircularDependency(f"On loop #{i}, please check for circularly dependent components! If this is a mistake, increase the `max_loops` param.")

            i += 1

        ast_builder = html_inter.HTML_AST_Builder()
        ast_root = ast_builder.build(tokens)

        builder = html_inter.HTMLBuilder()
        template_text_processed = builder.build(ast_root, indent_spaces = self._indent_spaces)

        if self._file_cache:
            with open(cache_path, "w", encoding = "utf-8") as f:
                f.write(template_text_processed)
            
            self._cache_last_count = self._load_count

        return template_text_processed