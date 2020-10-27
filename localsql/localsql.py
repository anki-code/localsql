from localsql import __version__

import os
import sys
import re
import argparse, argcomplete
import warnings
import json
import gzip
import pandas as pd
import tableprint as tp
from collections.abc import Iterable
from io import TextIOWrapper
from pathlib import Path
from pandasql import sqldf
from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import SqlLexer

class LocalSQL():
    def __init__(self):
        self.extensions = ['csv', 'xlsx', 'json']

        history_path = Path.home() / '.local/share/localsql'
        if not history_path.exists():
            history_path.mkdir(parents=True, exist_ok=True)
        self.history_file = history_path / 'lsql_history'

        self.tables = {}
        self.verbose = False
        self.silent = False
        self.latest_result = None
        self.lexer = False
        self.mode = 'lsql'
        self.json_normalize = False
        self.pretty_print = False

        self.re_quotated_column = re.compile(r'.*[ -.,\{\}\[\]\(\)<>?/\\\'!@#$%^&*:;`~ ].*')
        self.re_file_to_tablename = re.compile(r'[:*?\-<=>|"\'.{}\[\]\(\) ]')

        pd.set_option('display.width', None)
        pd.set_option('display.max_columns', 1000)
        pd.set_option('display.max_rows', 1000)
        pd.set_option('precision', 4)
        #pd.options.display.float_format = '{:,}'.format
        #pd.set_option('display.max_colwidth', 100)

    def get_tables_descr(self):
        stat = []
        for n, d in self.tables.items():
            stat.append([n, len(d), len(d.columns), d.memory_usage(index=True).sum()])
        return pd.DataFrame(stat, columns=['Table', 'Rows', 'Columns', 'Bytes']).set_index('Table')

    def print(self, *args, **kwargs):
        if not self.silent:
            print_formatted_text(*args, **kwargs)

    def eprint(self, *args, **kwargs):
        if not self.silent:
            print_formatted_text(*args, file=sys.stderr, **kwargs)

    def eeprint(self, *args, **kwargs):
        return_code = 1
        if 'return_code' in kwargs:
            return_code = kwargs['return_code']
            del kwargs['return_code']
        print_formatted_text(*args, file=sys.stderr, **kwargs)
        exit(return_code)

    def df_iterable_to_str(self, df):
        for c, t in df.dtypes.iteritems():
            if t == 'object':
                df[c] = df[c].apply(lambda v: str(v) if isinstance(v, Iterable) else v)
        return df

    def df_from_file(self, file, format=None):
        is_stream = False
        compressor = None
        if isinstance(file, TextIOWrapper):
            is_stream = True
            if not format:
                self.eprint('Format for IO stream is not found.')
        else:
            fstr = str(file)
            fparts = fstr.split('.')
            ext1 = fparts[-1]
            ext2 = fparts[-2]

            compressors = ['gz', 'bz2', 'zip', 'xz']

            if ext1 in self.extensions:
                format = ext1
            elif ext2 in self.extensions and ext1 in compressors:
                format = ext2
                compressor = ext1

            if not format:
                return None

        if format == 'csv':
            return pd.read_csv(file)
        elif format == 'xlsx':
            return pd.read_excel(file, engine="openpyxl")
        elif format == 'json':
            if not self.json_normalize:
                try:
                    return self.df_iterable_to_str(pd.read_json(file, lines=True))
                except:
                    return self.df_iterable_to_str(pd.read_json(file))
            else:
                json_supported_compressors = ['gz']
                if compressor is not None and compressor not in json_supported_compressors:
                    self.eprint(f'Compressor {compressor} is not supported for json normalize mode.')
                    return None

                if is_stream:
                    fopen = file
                else:
                    if compressor == 'gz':
                        fopen = gzip.open(file, 'rt')
                    else:
                        fopen = open(file, 'r')

                try:
                    result_df = pd.DataFrame()
                    with fopen as f:
                        l = 0
                        for line in f:
                            j = json.loads(line)
                            json_df = pd.json_normalize(j)
                            result_df = pd.concat([result_df, json_df])
                            l += 1
                    return self.df_iterable_to_str(result_df)
                except:
                    if l == 0:
                        if compressor == 'gz':
                            fopen = gzip.open(file, 'rt')
                        else:
                            fopen = open(file, 'r')

                        with fopen as f:
                            return self.df_iterable_to_str(pd.read_json(f))
        return None

    def tablename_from_file(self, file):
        file_name = file.name
        table_name = self.re_file_to_tablename.sub('_', file_name)
        table_name = re.sub(r'[_]+', '_', table_name)
        if table_name[0].isdigit():
            table_name = 't' + table_name
        return table_name

    def special(self, query):
        query_args = query.split(' ')
        function_name = query_args[0]
        function = 'special_' + function_name

        if not hasattr(self, function):
            print(f'Unrecognized special command: {function_name}')
            print(f'  \\t     List of tables.\n'
                  f'  \\td    Detailed list of tables.\n'
                  f'  \\s     Save last not empty results to file.\n'
                  f'  \\lpy   Python commands mode\n'
                  f'  \\lsql  SQL commands mode\n')
            return None

        getattr(self, function)(query_args[1:])

    def special_s(self, args):
        if len(args) != 1:
            self.eprint('Save result to file.\n'
                        'Usage: \s <filename>.<csv/json/xlsx>')
            return None

        if self.latest_result is not None:
            filename = args[0]
            if filename.endswith('.csv'):
                self.latest_result.to_csv(filename)
            elif filename.endswith('.json'):
                self.latest_result.to_json(filename, orient='records', lines=True)
            elif filename.endswith('.xlsx'):
                self.latest_result.to_excel(filename)
            else:
                self.eprint(HTML(f'<ansired>Unsupported saving format</ansired>'))
                return None
            self.eprint(HTML(f'<green>Result saved to {filename}</green>'))
        else:
            self.eprint(HTML(f'<yellow>Result not found. Run the query before save</yellow>'))
            return None

        return None

    def special_t(self, args):
        print('\n'.join(self.tables.keys()))
        return None

    def special_td(self, args):
        print(self.get_tables_descr())
        return None

    def special_pp(self, args):
        self.pretty_print = not self.pretty_print
        print('Pretty print ' + ['OFF', 'ON'][int(self.pretty_print)])
        return None

    def special_lpy(self, args):
        self.mode = 'lpy'
        return None

    def special_lsql(self, args):
        self.mode = 'lsql'
        return None

    def run_lsql(self, query):
        query = query.strip()
        try:
            if query == '':
                return None

            if query[0] == '\\':
                self.special(query[1:])
                return None

            if query in self.tables:
                self.tables[query].info()
                return None

            result = sqldf(query, self.tables)
            if result is not None:
                self.latest_result = result
            return result

        except Exception as e:
            error_str = str(e)
            e = re.sub(r'\n\(Background on this error at: htt.*\)', '', error_str)
            e = re.sub(r'\n\[SQL: .*\]', '', e)
            self.eprint(HTML(f'<ansired>Error: {e}</ansired>'))
            if 'syntax error' in e:
                self.eprint(HTML(f'<ansired>SQLite syntax -> http://www.sqlite.org/lang.html</ansired>'))

        return None

    def run_py(self, command):
        try:
            if command == '':
                return None

            if command[0] == '\\':
                self.special(command[1:])
                return None

            try:
                return eval(command)
            except:
                exec(command)
        except Exception as e:
            self.eprint(HTML(f'<ansired>Error: {e}</ansired>'))
        return None

    def print_result(self, result):
        if self.pretty_print:
            tp.dataframe(result)
        else:
            print(result)

    def main(self):
        argp = argparse.ArgumentParser(description="Querying local files using SQL.")
        argp.add_argument('files', nargs='*', help=f"Files with tables: {', '.join(self.extensions)}.")
        argp.add_argument('-d', '--directory', help="Search files in this directory.")
        argp.add_argument('-r', '--recursive', default=False, action='store_true', help="Search files in the directory and subdirectories.")
        argp.add_argument('-q', '--query', help="Run SQL query and return result.")
        argp.add_argument('-v', '--verbose', default=self.verbose, action='store_true', help="Verbose mode.")
        argp.add_argument('-s', '--silent', default=self.silent, action='store_true', help="Silent mode.")
        argp.add_argument('-jn', '--json-normalize', default=self.json_normalize, action='store_true', help="JSON normalize.")
        argp.add_argument('--version', '-V', action='version', version=f"LocalSQL/{__version__}")
        argcomplete.autocomplete(argp)
        args = argp.parse_args()

        self.verbose = args.verbose
        self.silent = args.silent
        self.json_normalize = args.json_normalize

        if self.verbose:
            warnings.filters('ignore')

        files = []
        if args.files:
            files = [Path(f) for f in args.files]
        else:
            path = None
            if args.directory:
                path = args.directory
            elif args.recursive:
                path = '.'

            if path:
                glob = '**/*.*' if args.recursive else '*.*'
                files = Path(path).glob(glob)

        for file in files:
            try:
                df = self.df_from_file(file)
                if df is not None:
                    self.eprint(HTML(f'<orange>{file}: </orange>'), end='')
                    table_name = self.tablename_from_file(file)
                    self.tables[table_name] = df
                    self.eprint(HTML(f'<grey>table=</grey><yellow>{table_name}</yellow>, <grey>columns=</grey><lightgrey>{len(df.columns)}</lightgrey>, <grey>rows=</grey><lightgrey>{len(df)}</lightgrey>'))
                else:
                    continue
            except Exception as e:
                self.eprint(HTML(f'<ansired>{file} error: {e}</ansired>'))

        if not self.tables:
            self.eprint(HTML(f'<yellow>Supported files not found. Try -r, -d or --help</yellow>'))

        if args.query:
            result = self.run_lsql(args.query)
            if result is not None:
                self.print_result(result)
        else:
            table_names = list(self.tables.keys())
            completions = table_names
            for n, d in self.tables.items():
                for c in d.columns:
                    col = c
                    if self.re_quotated_column.match(col):
                        col = f'"{col}"'
                    if col not in completions:
                        completions.append(col)

            html_completer = WordCompleter(completions)
            lexer = PygmentsLexer(SqlLexer) if self.lexer else None

            if self.history_file:
                history = FileHistory(self.history_file) if os.access('.', os.W_OK) else None
            else:
                history = None
            session = PromptSession(lexer=lexer, history=history)
            while 1:
                try:
                    query = session.prompt(HTML(f'<white><bold>{self.mode}></bold></white> '), completer=html_completer)
                    query = query.strip()
                except KeyboardInterrupt:
                    continue

                if self.mode == 'lsql':
                    transpose_rows = False
                    if query[-2:] == '/t':
                        query = query[:-2]
                        transpose_rows = True

                    result = self.run_lsql(query)
                    if result is not None:
                        if transpose_rows:
                            for i, r in result.iterrows():
                                print(r, end='\n\n')
                        else:
                            self.print_result(result)
                elif self.mode == 'lpy':
                    result = self.run_py(query)
                    if result is not None:
                        self.print_result(result)
