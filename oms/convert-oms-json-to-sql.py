import json
import sqlite3
import datetime
from functools import partial
from pathlib import Path
import argparse
import pandas as pd

def transform_row(row, component_set: set[str]):
    for each in row.pop('components'):
        row[each] = 1
    for each in row.pop('components_out'):
        row[each] = 0

    for each in component_set:
        if each not in row:
            row[each] = -1 # missing
    for key in ['start_time', 'end_time', 'last_update']:
        if row[key] is not None:
            # strptime don't preserve timezone... 
            row[key] = datetime.datetime.strptime(row[key], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
    return row

def run(input_path: Path,
        output_path: Path,
        table: str,
        if_exists: str,
        to_csv: bool,
        dump_schema: bool,
) -> None:
    with open(input_path, 'r') as json_file:
        data = json.load(json_file)
    data = [each['attributes'] for each in data['data']]

    component_set = {each for row in data for each in row['components'] + row['components_out']}

    row_transform_func = partial(transform_row, component_set=component_set)
    data = map(row_transform_func, data)
    data = pd.DataFrame(data)

    if dump_schema:
        schema = pd.io.sql.get_schema(data, table) # type: ignore
        print(schema)

    output_path = output_path or input_path.with_suffix('.sql')
    connection = sqlite3.connect(output_path)
    data.to_sql(name=table, con=connection, if_exists=if_exists)
    connection.commit()
    connection.close()

    if to_csv:
        data.to_csv(output_path.with_suffix('.csv'))

def main():
    """TODO: Docstring for main.

    :returns: TODO

    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("input_path", type=Path, help="Help text")
    parser.add_argument("--output-path", "--output-path", default=None,
                        help="a path to output file")
    parser.add_argument("-t", "--table", default="oms", type=str, help="table name")
    parser.add_argument("--if-exists", type=str, default='fail',
                        choices=('fail', 'replace', 'append'),
                        help="How to behave if the table already exists.")
    parser.add_argument("--to-csv", action="store_true", default=False, help="to csv")
    parser.add_argument("-s", "--dump-schema", action="store_true", default=False, help="dump schema")
    args = parser.parse_args()

    run(input_path=args.input_path,
        output_path=args.output_path,
        table=args.table,
        if_exists=args.if_exists,
        to_csv=args.to_csv,
        dump_schema=args.dump_schema)

if __name__ == "__main__":
    main()
