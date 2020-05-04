import sys
import re
import argparse
import pandas as pd
import warnings
from pathlib import Path
from pandasql import sqldf
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit import print_formatted_text, HTML

__version__ = '0.1.2'

def get_ext(f):
    return str(f).split('.')[-1]

class LocalSQL():
    def __init__(self):
        self.extensions = ['csv', 'xlsx', 'json']
        self.history_file = '.lsql_history'
        self.tables = {}
        self.verbose = False

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
        if not self.quiet:
            print_formatted_text(*args, **kwargs)

    def eprint(self, *args, **kwargs):
        if not self.quiet:
            print_formatted_text(*args, file=sys.stderr, **kwargs)

    def eeprint(self, *args, **kwargs):
        return_code = 1
        if 'return_code' in kwargs:
            return_code = kwargs['return_code']
            del kwargs['return_code']
        print_formatted_text(*args, file=sys.stderr, **kwargs)
        exit(return_code)

    def main(self):
        argp = argparse.ArgumentParser(description="Querying local files using SQL.")
        argp.add_argument('files', nargs='*', help=f"Files with tables: {', '.join(self.extensions)}.")
        argp.add_argument('-d', '--directory', help="Search files in this directory.")
        argp.add_argument('-r', '--recursive', default=False, action='store_true', help="Search files in the directory and subdirectories.")
        argp.add_argument('-v', '--verbose', default=False, action='store_true', help="Verbose mode.")
        argp.add_argument('-q', '--quiet', default=False, action='store_true', help="Quiet mode.")
        argp.add_argument('--version', '-V', action='version', version=f"LocalSQL/{__version__}")
        args = argp.parse_args()

        self.verbose = args.verbose
        self.quiet = args.quiet

        if not self.quiet:
            print(f'LocalSQL {__version__}')

        if self.verbose:
            warnings.filters('ignore')

        if args.files:
            files = [Path(f) for f in args.files]
        else:
            glob = '**/*.*' if args.recursive else '*.*'
            path = args.directory if args.directory else '.'
            cdir = Path(path)
            files = cdir.glob(glob)

        for f in files:
            ext = get_ext(str(f))
            if not ext in self.extensions:
                continue

            file_name = f.name
            table_name = re.sub('[:*?<>|"\'.{}\[\]\(\) ]', '_', file_name)
            table_name = re.sub('[_]+', '_', table_name)
            if table_name[0].isdigit():
                table_name = 't' + table_name

            self.print(HTML(f'<orange>{f}: </orange>'), end='')
            try:
                if ext == 'csv':
                    self.tables[table_name] = pd.read_csv(f)
                elif ext == 'json':
                    try:
                        self.tables[table_name] = pd.read_json(f)
                    except:
                        self.tables[table_name] = pd.read_json(f, lines=True)
                elif ext == 'xlsx':
                    self.tables[table_name] = pd.read_excel(f, engine="openpyxl")
                self.print(HTML(f'<yellow>{table_name}</yellow>'))
            except Exception as e:
                self.eprint(HTML(f'<ansired>{f} error: {e}</ansired>'))

        if not self.tables:
            self.eeprint(HTML(f'<ansired>Supported files not found. Try --help</ansired>'))

        table_names = list(self.tables.keys())
        completions = table_names

        from prompt_toolkit.completion import WordCompleter
        html_completer = WordCompleter(completions)
        session = PromptSession(history=FileHistory(self.history_file))
        while 1:
            try:
                query = session.prompt(HTML('<white>lsql></white> '), completer=html_completer)
            except KeyboardInterrupt:
                continue

            query = query.strip()
            try:
                if query in self.tables:
                    print(self.tables[query])
                    continue

                if query == '\\t':
                    print('\n'.join(table_names))
                    continue

                if query == '\\t+':
                    print(self.get_tables_descr())
                    continue

                if query in ['\\?', '?', '\help', '/help', 'help']:  # tables list
                    print("\\t   tables list\n"
                          "\\t+  tables list with details\n")
                    continue

                if query == '':
                    continue

                result = sqldf(query, self.tables)
                print(result)
            except Exception as e:
                error_str = str(e)
                e = re.sub(r'\n\(Background on this error at: htt.*\)', '', error_str)
                e = re.sub(r'\n\[SQL: .*\]', '', e)
                self.eprint(HTML(f'<ansired>Error: {e}</ansired>'))
                if 'syntax error' in e:
                    self.eprint(HTML(f'<ansired>SQLite syntax -> http://www.sqlite.org/lang.html</ansired>'))
