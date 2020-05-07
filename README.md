LocalSQL is for querying local files using SQL. 

The `lsql` command without arguments finds csv, xlsx, json files in the current directory
and loads them in memory to querying using SQL.

## Install
```bash
pip install git+https://github.com/localsql/localsql
```

## Usage

```
$ lsql --help
usage: lsql [-h] [-d DIRECTORY] [-r] [-q QUERY] [-v] [-s] [--version] [files [files ...]]

Querying local files using SQL.

positional arguments:
  files                 Files with tables: csv, xlsx, json.

optional arguments:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory DIRECTORY
                        Search files in this directory.
  -r, --recursive       Search files in the directory and subdirectories.
  -q QUERY, --query QUERY
                        Run SQL query and return result.
  -v, --verbose         Verbose mode.
  -s, --silent          Silent mode.
  --version, -V         show program's version number and exit

```

## Example
### Interactive
```bash
$ cd ~ && git clone https://github.com/localsql/localsql && cd localsql 
$ lsql -r
examples/one.json: one_json
examples/lines.json: lines_json
examples/excel.xlsx: excel_xlsx
examples/csv.csv: csv_csv

lsql> select * from excel_xlsx
   id   b   c
0   1   6  11
1   2   7  12
2   3   8  13
3   4   9  14
4   5  10  15

lsql> SELECT * FROM excel_xlsx e LEFT JOIN one_json j ON e.id = j.id
   id   b   c   id    b    c    d
0   1   6  11  1.0  4.0  NaN  NaN
1   2   7  12  2.0  NaN  5.0  NaN
2   3   8  13  3.0  NaN  NaN  6.0
3   4   9  14  NaN  NaN  NaN  NaN
4   5  10  15  NaN  NaN  NaN  NaN
```
### Not interactive
```bash
$ lsql -r -q "SELECT c, count(*) as cnt FROM one_json GROUP BY c ORDER BY 1 ASC NULLS LAST" -s                                                                                    
     c  cnt
0  5.0    1
1  NaN    2

```

## SQL syntax
LocalSQL uses [pandasql](https://github.com/yhat/pandasql) library with [SQLite syntax](http://www.sqlite.org/lang.html).