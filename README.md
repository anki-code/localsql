<p align="center">
<b>LocalSQL</b> is for querying local csv, xlsx, json files using SQL. 
</p>

<p align="center">  
If you like the idea of pipeliner click ⭐ on the repo and stay tuned.
</p>

## Install
```bash
pip install git+https://github.com/localsql/localsql
```

## Usage

```
$ lsql --help
usage: lsql [-h] [-d DIRECTORY] [-r] [-q QUERY] [-v] [-s] [-jn] [--version] [files [files ...]]

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
  -jn, --json-normalize
                        JSON normalize.
  --version, -V         show program's version number and exit
```

### SQL syntax
LocalSQL uses [SQLite syntax](http://www.sqlite.org/lang.html).

## Use cases
To repeat the use cases get the repository:
```bash
$ cd ~ && git clone --depth 1 https://github.com/localsql/localsql && cd localsql
$ lsql -d examples
examples/one.json: table=one_json, columns=4, rows=3
examples/lines.json: table=lines_json, columns=3, rows=3
examples/nested.json: table=nested_json, columns=5, rows=3
examples/excel.xlsx: table=excel_xlsx, columns=3, rows=5
examples/csv.csv: table=csv_csv, columns=3, rows=3
lsql>
```

### Interactive
```bash
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
$ lsql -d examples -q "SELECT c, count(*) as cnt FROM one_json GROUP BY c ORDER BY 1 ASC NULLS LAST" -s
     c  cnt
0  5.0    1
1  NaN    2
```

### Transpose output
To transpose the output add `/t` to the end of query:
```
lsql> SELECT * FROM nested_json LIMIT 1 /t
id                1
nest.a            1
nest.b    [1, 2, 3]
nest           None
c              None
Name: 0, dtype: object

```

### Python mode
```
lsql> \lpy
lpy> print(self.tables['csv_csv'])
   id  b  c
0   1  4  7
1   2  5  8
2   3  6  9
```

### Pretty print

```
lsql> \pp
Pretty print ON
lsql> select * from one_json
╭─────┬─────┬─────┬─────╮
│  id │   b │   c │   d │
├─────┼─────┼─────┼─────┤
│   1 │   4 │ nan │ nan │
│   2 │ nan │   5 │ nan │
│   3 │ nan │ nan │   6 │
╰─────┴─────┴─────┴─────╯
```
