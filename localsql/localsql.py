import os
import sys
import re
import argparse
import pandas as pd
import warnings
from pathlib import Path
from pandasql import sqldf
from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import SqlLexer
from localsql import __version__

class LocalSQL():
    def __init__(self):
        self.extensions = ['csv', 'xlsx', 'json']
        self.history_file = '.lsql_history'
        self.tables = {}
        self.verbose = False
        self.silent = False
        self.latest_result = None
        self.lexer = False

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

    def df_from_file(self, file):
        fstr = str(file)

        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html
        for compressor in ['.gz', '.bz2', '.zip', '.xz']:
            if fstr.endswith(compressor):
                fstr = fstr[:-len(compressor)]
                break

        if fstr.endswith('.csv'):
            return pd.read_csv(file)
        elif fstr.endswith('.json'):
            try:
                return pd.read_json(file)
            except:
                return pd.read_json(file, lines=True)
        elif fstr.endswith('.xlsx'):
            return pd.read_excel(file, engine="openpyxl")

        return None

    def tablename_from_file(self, file):
        file_name = file.name
        table_name = re.sub('[:*?\-<>|"\'.{}\[\]\(\) ]', '_', file_name)
        table_name = re.sub('[_]+', '_', table_name)
        if table_name[0].isdigit():
            table_name = 't' + table_name
        return table_name

    def special(self, query):
        query_args = query.split(' ')
        function_name = query_args[0]
        function = 'special_' + function_name

        if not hasattr(self, function):
            print(f'Unrecognized special command: {function_name}\n')
            print(f'Commands:\n'
                  f'  \\t   List of tables.\n'
                  f'  \\td  Detailed list of tables.\n'
                  f'  \\s   Save last not empty results to file.\n')
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

    def run_query(self, query):
        query = query.strip()
        try:
            if query == '':
                return None

            if query[0] == '\\':
                self.special(query[1:])
                return None

            if query in self.tables:
                print(self.tables[query])
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


    def main(self):
        argp = argparse.ArgumentParser(description="Querying local files using SQL.")
        argp.add_argument('files', nargs='*', help=f"Files with tables: {', '.join(self.extensions)}.")
        argp.add_argument('-d', '--directory', help="Search files in this directory.")
        argp.add_argument('-r', '--recursive', default=False, action='store_true', help="Search files in the directory and subdirectories.")
        argp.add_argument('-q', '--query', help="Run SQL query and return result.")
        argp.add_argument('-v', '--verbose', default=self.verbose, action='store_true', help="Verbose mode.")
        argp.add_argument('-s', '--silent', default=self.silent, action='store_true', help="Silent mode.")
        argp.add_argument('--version', '-V', action='version', version=f"LocalSQL/{__version__}")
        args = argp.parse_args()

        self.verbose = args.verbose
        self.silent = args.silent

        if not self.silent:
            self.eprint(f'LocalSQL {__version__}')

        if self.verbose:
            warnings.filters('ignore')

        if args.files:
            files = [Path(f) for f in args.files]
        else:
            glob = '**/*.*' if args.recursive else '*.*'
            path = args.directory if args.directory else '.'
            cdir = Path(path)
            files = cdir.glob(glob)

        for file in files:
            try:
                df = self.df_from_file(file)
                if df is not None:
                    self.print(HTML(f'<orange>{file}: </orange>'), end='')
                    table_name = self.tablename_from_file(file)
                    self.tables[table_name] = df
                    self.print(HTML(f'<yellow>{table_name}</yellow>'))
                else:
                    continue
            except Exception as e:
                self.eprint(HTML(f'<ansired>{file} error: {e}</ansired>'))

        if not self.tables:
            self.eprint(HTML(f'<yellow>Supported files not found. Try -r, -d or --help</yellow>'))

        if args.query:
            result = self.run_query(args.query)
            if result is not None:
                print(result)
        else:
            table_names = list(self.tables.keys())
            completions = table_names
            for n, d in self.tables.items():
                for c in d.columns:
                    col = c
                    if ' ' in col:
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
                    query = session.prompt(HTML('<white>lsql></white> '), completer=html_completer)
                except KeyboardInterrupt:
                    continue
                result = self.run_query(query)
                if result is not None:
                    print(result)
