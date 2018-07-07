"""
Tests for various datasette helper functions.
"""

from datasette import utils
import json
import os
import pytest
from sanic.request import Request
import sqlite3
import tempfile
from unittest.mock import patch


@pytest.mark.parametrize('path,expected', [
    ('foo', ['foo']),
    ('foo,bar', ['foo', 'bar']),
    ('123,433,112', ['123', '433', '112']),
    ('123%2C433,112', ['123,433', '112']),
    ('123%2F433%2F112', ['123/433/112']),
])
def test_urlsafe_components(path, expected):
    assert expected == utils.urlsafe_components(path)


@pytest.mark.parametrize('path,added_args,expected', [
    ('/foo', {'bar': 1}, '/foo?bar=1'),
    ('/foo?bar=1', {'baz': 2}, '/foo?bar=1&baz=2'),
    ('/foo?bar=1&bar=2', {'baz': 3}, '/foo?bar=1&bar=2&baz=3'),
    ('/foo?bar=1', {'bar': None}, '/foo'),
    # Test order is preserved
    ('/?_facet=prim_state&_facet=area_name', (
        ('prim_state', 'GA'),
    ), '/?_facet=prim_state&_facet=area_name&prim_state=GA'),
    ('/?_facet=state&_facet=city&state=MI', (
        ('city', 'Detroit'),
    ), '/?_facet=state&_facet=city&state=MI&city=Detroit'),
    ('/?_facet=state&_facet=city', (
        ('_facet', 'planet_int'),
    ), '/?_facet=state&_facet=city&_facet=planet_int'),
])
def test_path_with_added_args(path, added_args, expected):
    request = Request(
        path.encode('utf8'),
        {}, '1.1', 'GET', None
    )
    actual = utils.path_with_added_args(request, added_args)
    assert expected == actual


@pytest.mark.parametrize('path,args,expected', [
    ('/foo?bar=1', {'bar'}, '/foo'),
    ('/foo?bar=1&baz=2', {'bar'}, '/foo?baz=2'),
    ('/foo?bar=1&bar=2&bar=3', {'bar': '2'}, '/foo?bar=1&bar=3'),
])
def test_path_with_removed_args(path, args, expected):
    request = Request(
        path.encode('utf8'),
        {}, '1.1', 'GET', None
    )
    actual = utils.path_with_removed_args(request, args)
    assert expected == actual


@pytest.mark.parametrize('path,args,expected', [
    ('/foo?bar=1', {'bar': 2}, '/foo?bar=2'),
    ('/foo?bar=1&baz=2', {'bar': None}, '/foo?baz=2'),
])
def test_path_with_replaced_args(path, args, expected):
    request = Request(
        path.encode('utf8'),
        {}, '1.1', 'GET', None
    )
    actual = utils.path_with_replaced_args(request, args)
    assert expected == actual


@pytest.mark.parametrize(
    "row,pks,expected_path",
    [
        ({"A": "foo", "B": "bar"}, ["A", "B"], "foo,bar"),
        ({"A": "f,o", "B": "bar"}, ["A", "B"], "f%2Co,bar"),
        ({"A": 123}, ["A"], "123"),
        (
            utils.CustomRow(
                ["searchable_id", "tag"],
                [
                    (
                        "searchable_id",
                        {"value": 1, "label": "1"},
                    ),
                    (
                        "tag",
                        {
                            "value": "feline",
                            "label": "feline",
                        },
                    ),
                ],
            ),
            ["searchable_id", "tag"],
            "1,feline",
        ),
    ],
)
def test_path_from_row_pks(row, pks, expected_path):
    actual_path = utils.path_from_row_pks(row, pks, False)
    assert expected_path == actual_path


@pytest.mark.parametrize('obj,expected', [
    ({
        'Description': 'Soft drinks',
        'Picture': b"\x15\x1c\x02\xc7\xad\x05\xfe",
        'CategoryID': 1,
    }, """
        {"CategoryID": 1, "Description": "Soft drinks", "Picture": {"$base64": true, "encoded": "FRwCx60F/g=="}}
    """.strip()),
])
def test_custom_json_encoder(obj, expected):
    actual = json.dumps(
        obj,
        cls=utils.CustomJSONEncoder,
        sort_keys=True
    )
    assert expected == actual


@pytest.mark.parametrize('args,expected_where,expected_params', [
    (
        {
            'name_english__contains': 'foo',
        },
        ['"name_english" like :p0'],
        ['%foo%']
    ),
    (
        {
            'foo': 'bar',
            'bar__contains': 'baz',
        },
        ['"bar" like :p0', '"foo" = :p1'],
        ['%baz%', 'bar']
    ),
    (
        {
            'foo__startswith': 'bar',
            'bar__endswith': 'baz',
        },
        ['"bar" like :p0', '"foo" like :p1'],
        ['%baz', 'bar%']
    ),
    (
        {
            'foo__lt': '1',
            'bar__gt': '2',
            'baz__gte': '3',
            'bax__lte': '4',
        },
        ['"bar" > :p0', '"bax" <= :p1', '"baz" >= :p2', '"foo" < :p3'],
        [2, 4, 3, 1]
    ),
    (
        {
            'foo__like': '2%2',
            'zax__glob': '3*',
        },
        ['"foo" like :p0', '"zax" glob :p1'],
        ['2%2', '3*']
    ),
    (
        {
            'foo__isnull': '1',
            'baz__isnull': '1',
            'bar__gt': '10'
        },
        ['"bar" > :p0', '"baz" is null', '"foo" is null'],
        [10]
    ),
])
def test_build_where(args, expected_where, expected_params):
    f = utils.Filters(sorted(args.items()))
    sql_bits, actual_params = f.build_where_clauses()
    assert expected_where == sql_bits
    assert {
        'p{}'.format(i): param
        for i, param in enumerate(expected_params)
    } == actual_params


@pytest.mark.parametrize('bad_sql', [
    'update blah;',
    'PRAGMA case_sensitive_like = true'
    "SELECT * FROM pragma_index_info('idx52')",
])
def test_validate_sql_select_bad(bad_sql):
    with pytest.raises(utils.InvalidSql):
        utils.validate_sql_select(bad_sql)


@pytest.mark.parametrize('good_sql', [
    'select count(*) from airports',
    'select foo from bar',
    'select 1 + 1',
    'SELECT\nblah FROM foo',
    'WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt LIMIT 10) SELECT x FROM cnt;'
])
def test_validate_sql_select_good(good_sql):
    utils.validate_sql_select(good_sql)


def test_detect_fts():
    sql = '''
    CREATE TABLE "Dumb_Table" (
      "TreeID" INTEGER,
      "qSpecies" TEXT
    );
    CREATE TABLE "Street_Tree_List" (
      "TreeID" INTEGER,
      "qSpecies" TEXT,
      "qAddress" TEXT,
      "SiteOrder" INTEGER,
      "qSiteInfo" TEXT,
      "PlantType" TEXT,
      "qCaretaker" TEXT
    );
    CREATE VIEW Test_View AS SELECT * FROM Dumb_Table;
    CREATE VIRTUAL TABLE "Street_Tree_List_fts" USING FTS4 ("qAddress", "qCaretaker", "qSpecies", content="Street_Tree_List");
    CREATE VIRTUAL TABLE r USING rtree(a, b, c);
    '''
    conn = sqlite3.connect(':memory:')
    conn.executescript(sql)
    assert None is utils.detect_fts(conn, 'Dumb_Table')
    assert None is utils.detect_fts(conn, 'Test_View')
    assert None is utils.detect_fts(conn, 'r')
    assert 'Street_Tree_List_fts' == utils.detect_fts(conn, 'Street_Tree_List')


@pytest.mark.parametrize('url,expected', [
    ('http://www.google.com/', True),
    ('https://example.com/', True),
    ('www.google.com', False),
    ('http://www.google.com/ is a search engine', False),
])
def test_is_url(url, expected):
    assert expected == utils.is_url(url)


@pytest.mark.parametrize('s,expected', [
    ('simple', 'simple'),
    ('MixedCase', 'MixedCase'),
    ('-no-leading-hyphens', 'no-leading-hyphens-65bea6'),
    ('_no-leading-underscores', 'no-leading-underscores-b921bc'),
    ('no spaces', 'no-spaces-7088d7'),
    ('-', '336d5e'),
    ('no $ characters', 'no--characters-59e024'),
])
def test_to_css_class(s, expected):
    assert expected == utils.to_css_class(s)


def test_temporary_docker_directory_uses_hard_link():
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        open('hello', 'w').write('world')
        # Default usage of this should use symlink
        with utils.temporary_docker_directory(
            files=['hello'],
            name='t',
            metadata=None,
            extra_options=None,
            branch=None,
            template_dir=None,
            plugins_dir=None,
            static=[],
            install=[],
            spatialite=False,
            version_note=None,
        ) as temp_docker:
            hello = os.path.join(temp_docker, 'hello')
            assert 'world' == open(hello).read()
            # It should be a hard link
            assert 2 == os.stat(hello).st_nlink


@patch('os.link')
def test_temporary_docker_directory_uses_copy_if_hard_link_fails(mock_link):
    # Copy instead if os.link raises OSError (normally due to different device)
    mock_link.side_effect = OSError
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        open('hello', 'w').write('world')
        # Default usage of this should use symlink
        with utils.temporary_docker_directory(
            files=['hello'],
            name='t',
            metadata=None,
            extra_options=None,
            branch=None,
            template_dir=None,
            plugins_dir=None,
            static=[],
            install=[],
            spatialite=False,
            version_note=None,
        ) as temp_docker:
            hello = os.path.join(temp_docker, 'hello')
            assert 'world' == open(hello).read()
            # It should be a copy, not a hard link
            assert 1 == os.stat(hello).st_nlink


def test_compound_keys_after_sql():
    assert '((a > :p0))' == utils.compound_keys_after_sql(['a'])
    assert '''
((a > :p0)
  or
(a = :p0 and b > :p1))
    '''.strip() == utils.compound_keys_after_sql(['a', 'b'])
    assert '''
((a > :p0)
  or
(a = :p0 and b > :p1)
  or
(a = :p0 and b = :p1 and c > :p2))
    '''.strip() == utils.compound_keys_after_sql(['a', 'b', 'c'])


def table_exists(table):
    return table == "exists.csv"


@pytest.mark.parametrize(
    "table_and_format,expected_table,expected_format",
    [
        ("blah", "blah", None),
        ("blah.csv", "blah", "csv"),
        ("blah.json", "blah", "json"),
        ("blah.baz", "blah.baz", None),
        ("exists.csv", "exists.csv", None),
    ],
)
def test_resolve_table_and_format(
    table_and_format, expected_table, expected_format
):
    actual_table, actual_format = utils.resolve_table_and_format(
        table_and_format, table_exists
    )
    assert expected_table == actual_table
    assert expected_format == actual_format


@pytest.mark.parametrize(
    "path,format,extra_qs,expected",
    [
        ("/foo?sql=select+1", "csv", {}, "/foo.csv?sql=select+1"),
        ("/foo?sql=select+1", "json", {}, "/foo.json?sql=select+1"),
        ("/foo/bar", "json", {}, "/foo/bar.json"),
        ("/foo/bar", "csv", {}, "/foo/bar.csv"),
        ("/foo/bar.csv", "json", {}, "/foo/bar.csv?_format=json"),
        ("/foo/bar", "csv", {"_dl": 1}, "/foo/bar.csv?_dl=1"),
        ("/foo/b.csv", "json", {"_dl": 1}, "/foo/b.csv?_dl=1&_format=json"),
        (
            "/sf-trees/Street_Tree_List?_search=cherry&_size=1000",
            "csv",
            {"_dl": 1},
            "/sf-trees/Street_Tree_List.csv?_search=cherry&_size=1000&_dl=1",
        ),
    ],
)
def test_path_with_format(path, format, extra_qs, expected):
    request = Request(
        path.encode('utf8'),
        {}, '1.1', 'GET', None
    )
    actual = utils.path_with_format(request, format, extra_qs)
    assert expected == actual
