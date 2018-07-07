from bs4 import BeautifulSoup as Soup
from .fixtures import ( # noqa
    app_client,
    app_client_shorter_time_limit,
)
import pytest
import re
import urllib.parse


def test_homepage(app_client):
    response = app_client.get('/')
    assert response.status == 200
    assert 'fixtures' in response.text


def test_database_page(app_client):
    response = app_client.get('/fixtures', allow_redirects=False)
    assert response.status == 302
    response = app_client.get('/fixtures')
    assert 'fixtures' in response.text


def test_invalid_custom_sql(app_client):
    response = app_client.get(
        '/fixtures?sql=.schema'
    )
    assert response.status == 400
    assert 'Statement must be a SELECT' in response.text


def test_sql_time_limit(app_client_shorter_time_limit):
    response = app_client_shorter_time_limit.get(
        '/fixtures?sql=select+sleep(0.5)'
    )
    assert 400 == response.status
    expected_html_fragment = """
        <a href="https://datasette.readthedocs.io/en/stable/config.html#sql-time-limit-ms">sql_time_limit_ms</a>
    """.strip()
    assert expected_html_fragment in response.text


def test_view(app_client):
    response = app_client.get('/fixtures/simple_view')
    assert response.status == 200


def test_row(app_client):
    response = app_client.get(
        '/fixtures/simple_primary_key/1',
        allow_redirects=False
    )
    assert response.status == 302
    assert response.headers['Location'].endswith('/1')
    response = app_client.get('/fixtures/simple_primary_key/1')
    assert response.status == 200


def test_add_filter_redirects(app_client):
    filter_args = urllib.parse.urlencode({
        '_filter_column': 'content',
        '_filter_op': 'startswith',
        '_filter_value': 'x'
    })
    # First we need to resolve the correct path before testing more redirects
    path_base = app_client.get(
        '/fixtures/simple_primary_key', allow_redirects=False
    ).headers['Location']
    path = path_base + '?' + filter_args
    response = app_client.get(path, allow_redirects=False)
    assert response.status == 302
    assert response.headers['Location'].endswith('?content__startswith=x')

    # Adding a redirect to an existing querystring:
    path = path_base + '?foo=bar&' + filter_args
    response = app_client.get(path, allow_redirects=False)
    assert response.status == 302
    assert response.headers['Location'].endswith('?foo=bar&content__startswith=x')

    # Test that op with a __x suffix overrides the filter value
    path = path_base + '?' + urllib.parse.urlencode({
        '_filter_column': 'content',
        '_filter_op': 'isnull__5',
        '_filter_value': 'x'
    })
    response = app_client.get(path, allow_redirects=False)
    assert response.status == 302
    assert response.headers['Location'].endswith('?content__isnull=5')


def test_existing_filter_redirects(app_client):
    filter_args = {
        '_filter_column_1': 'name',
        '_filter_op_1': 'contains',
        '_filter_value_1': 'hello',
        '_filter_column_2': 'age',
        '_filter_op_2': 'gte',
        '_filter_value_2': '22',
        '_filter_column_3': 'age',
        '_filter_op_3': 'lt',
        '_filter_value_3': '30',
        '_filter_column_4': 'name',
        '_filter_op_4': 'contains',
        '_filter_value_4': 'world',
    }
    path_base = app_client.get(
        '/fixtures/simple_primary_key', allow_redirects=False
    ).headers['Location']
    path = path_base + '?' + urllib.parse.urlencode(filter_args)
    response = app_client.get(path, allow_redirects=False)
    assert response.status == 302
    assert_querystring_equal(
        'name__contains=hello&age__gte=22&age__lt=30&name__contains=world',
        response.headers['Location'].split('?')[1],
    )

    # Setting _filter_column_3 to empty string should remove *_3 entirely
    filter_args['_filter_column_3'] = ''
    path = path_base + '?' + urllib.parse.urlencode(filter_args)
    response = app_client.get(path, allow_redirects=False)
    assert response.status == 302
    assert_querystring_equal(
        'name__contains=hello&age__gte=22&name__contains=world',
        response.headers['Location'].split('?')[1],
    )

    # ?_filter_op=exact should be removed if unaccompanied by _fiter_column
    response = app_client.get(path_base + '?_filter_op=exact', allow_redirects=False)
    assert response.status == 302
    assert '?' not in response.headers['Location']


def test_empty_search_parameter_gets_removed(app_client):
    path_base = app_client.get(
        '/fixtures/simple_primary_key', allow_redirects=False
    ).headers['Location']
    path = path_base + '?' + urllib.parse.urlencode({
        '_search': '',
        '_filter_column': 'name',
        '_filter_op': 'exact',
        '_filter_value': 'chidi',
    })
    response = app_client.get(path, allow_redirects=False)
    assert response.status == 302
    assert response.headers['Location'].endswith(
        '?name__exact=chidi'
    )


def test_sort_by_desc_redirects(app_client):
    path_base = app_client.get(
        '/fixtures/sortable', allow_redirects=False
    ).headers['Location']
    path = path_base + '?' + urllib.parse.urlencode({
        '_sort': 'sortable',
        '_sort_by_desc': '1',
    })
    response = app_client.get(path, allow_redirects=False)
    assert response.status == 302
    assert response.headers['Location'].endswith('?_sort_desc=sortable')


def test_sort_links(app_client):
    response = app_client.get(
        '/fixtures/sortable?_sort=sortable'

    )
    assert response.status == 200
    ths = Soup(response.body, 'html.parser').findAll('th')
    attrs_and_link_attrs = [{
        'attrs': th.attrs,
        'a_href': (
            th.find('a')['href'].split('/')[-1]
            if th.find('a')
            else None
        ),
    } for th in ths]
    assert [
        {
            "attrs": {"class": ["col-Link"], "scope": "col"},
            "a_href": None
        },
        {
            "attrs": {"class": ["col-pk1"], "scope": "col"},
            "a_href": None
        },
        {
            "attrs": {"class": ["col-pk2"], "scope": "col"},
            "a_href": None
        },
        {
            "attrs": {"class": ["col-content"], "scope": "col"},
            "a_href": None
        },
        {
            "attrs": {"class": ["col-sortable"], "scope": "col"},
            "a_href": "sortable?_sort_desc=sortable",
        },
        {
            "attrs": {"class": ["col-sortable_with_nulls"], "scope": "col"},
            "a_href": "sortable?_sort=sortable_with_nulls",
        },
        {
            "attrs": {"class": ["col-sortable_with_nulls_2"], "scope": "col"},
            "a_href": "sortable?_sort=sortable_with_nulls_2",
        },
        {
            "attrs": {"class": ["col-text"], "scope": "col"},
            "a_href": "sortable?_sort=text",
        },
    ] == attrs_and_link_attrs


def test_facet_display(app_client):
    response = app_client.get(
        "/fixtures/facetable?_facet=planet_int&_facet=city_id&_facet=on_earth"
    )
    assert response.status == 200
    soup = Soup(response.body, "html.parser")
    divs = soup.find(
        "div", {"class": "facet-results"}
    ).findAll("div")
    actual = []
    for div in divs:
        actual.append(
            {
                "name": div.find("strong").text,
                "items": [
                    {
                        "name": a.text,
                        "qs": a["href"].split("?")[-1],
                        "count": int(str(a.parent).split("</a>")[1].split("<")[0]),
                    }
                    for a in div.find("ul").findAll("a")
                ],
            }
        )
    assert [
        {
            "name": "city_id",
            "items": [
                {
                    "name": "San Francisco",
                    "qs": "_facet=planet_int&_facet=city_id&_facet=on_earth&city_id=1",
                    "count": 6,
                },
                {
                    "name": "Los Angeles",
                    "qs": "_facet=planet_int&_facet=city_id&_facet=on_earth&city_id=2",
                    "count": 4,
                },
                {
                    "name": "Detroit",
                    "qs": "_facet=planet_int&_facet=city_id&_facet=on_earth&city_id=3",
                    "count": 4,
                },
                {
                    "name": "Memnonia",
                    "qs": "_facet=planet_int&_facet=city_id&_facet=on_earth&city_id=4",
                    "count": 1,
                },
            ],
        },
        {
            "name": "planet_int",
            "items": [
                {
                    "name": "1",
                    "qs": "_facet=planet_int&_facet=city_id&_facet=on_earth&planet_int=1",
                    "count": 14,
                },
                {
                    "name": "2",
                    "qs": "_facet=planet_int&_facet=city_id&_facet=on_earth&planet_int=2",
                    "count": 1,
                },
            ],
        },
        {
            "name": "on_earth",
            "items": [
                {
                    "name": "1",
                    "qs": "_facet=planet_int&_facet=city_id&_facet=on_earth&on_earth=1",
                    "count": 14,
                },
                {
                    "name": "0",
                    "qs": "_facet=planet_int&_facet=city_id&_facet=on_earth&on_earth=0",
                    "count": 1,
                },
            ],
        },
    ] == actual


def test_facets_persist_through_filter_form(app_client):
    response = app_client.get(
        '/fixtures/facetable?_facet=planet_int&_facet=city_id'
    )
    assert response.status == 200
    inputs = Soup(response.body, 'html.parser').find('form').findAll('input')
    hiddens = [i for i in inputs if i['type'] == 'hidden']
    assert [
        ('_facet', 'city_id'),
        ('_facet', 'planet_int'),
    ] == [
        (hidden['name'], hidden['value']) for hidden in hiddens
    ]


@pytest.mark.parametrize('path,expected_classes', [
    ('/', ['index']),
    ('/fixtures', ['db', 'db-fixtures']),
    ('/fixtures/simple_primary_key', [
        'table', 'db-fixtures', 'table-simple_primary_key'
    ]),
    ('/fixtures/table%2Fwith%2Fslashes.csv', [
        'table', 'db-fixtures', 'table-tablewithslashescsv-fa7563'
    ]),
    ('/fixtures/simple_primary_key/1', [
        'row', 'db-fixtures', 'table-simple_primary_key'
    ]),
])
def test_css_classes_on_body(app_client, path, expected_classes):
    response = app_client.get(path)
    assert response.status == 200
    classes = re.search(r'<body class="(.*)">', response.text).group(1).split()
    assert classes == expected_classes


def test_table_html_simple_primary_key(app_client):
    response = app_client.get('/fixtures/simple_primary_key')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    assert table['class'] == ['rows-and-columns']
    ths = table.findAll('th')
    assert 'id' == ths[0].find('a').string.strip()
    for expected_col, th in zip(('content',), ths[1:]):
        a = th.find('a')
        assert expected_col == a.string
        assert a['href'].endswith('/simple_primary_key?_sort={}'.format(
            expected_col
        ))
        assert ['nofollow'] == a['rel']
    assert [
        [
            '<td class="col-id"><a href="/fixtures/simple_primary_key/1">1</a></td>',
            '<td class="col-content">hello</td>'
        ], [
            '<td class="col-id"><a href="/fixtures/simple_primary_key/2">2</a></td>',
            '<td class="col-content">world</td>'
        ], [
            '<td class="col-id"><a href="/fixtures/simple_primary_key/3">3</a></td>',
            '<td class="col-content">\xa0</td>'
        ]
    ] == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_table_csv_json_export_interface(app_client):
    response = app_client.get('/fixtures/simple_primary_key')
    assert response.status == 200
    # The links at the top of the page
    links = Soup(response.body, "html.parser").find("p", {
        "class": "export-links"
    }).findAll("a")
    actual = [l["href"].split("/")[-1] for l in links]
    expected = [
        "simple_primary_key.json",
        "simple_primary_key.csv?_size=max",
        "#export"
    ]
    assert expected == actual
    # And the advaced export box at the bottom:
    div = Soup(response.body, "html.parser").find("div", {
        "class": "advanced-export"
    })
    json_links = [a["href"].split("/")[-1] for a in div.find("p").findAll("a")]
    assert [
        "simple_primary_key.json",
        "simple_primary_key.json?_shape=array",
        "simple_primary_key.json?_shape=object"
    ] == json_links
    # And the CSV form
    form = div.find("form")
    assert form["action"].endswith("/simple_primary_key.csv")
    inputs = [str(input) for input in form.findAll("input")]
    assert [
        '<input name="_dl" type="checkbox"/>',
        '<input type="submit" value="Export CSV"/>',
        '<input name="_size" type="hidden" value="max"/>'
    ] == inputs


def test_csv_json_export_links_include_labels_if_foreign_keys(app_client):
    response = app_client.get('/fixtures/facetable')
    assert response.status == 200
    links = Soup(response.body, "html.parser").find("p", {
        "class": "export-links"
    }).findAll("a")
    actual = [l["href"].split("/")[-1] for l in links]
    expected = [
        "facetable.json?_labels=on",
        "facetable.csv?_labels=on&_size=max",
        "#export"
    ]
    assert expected == actual


def test_row_html_simple_primary_key(app_client):
    response = app_client.get('/fixtures/simple_primary_key/1')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    assert [
        'id', 'content'
    ] == [th.string.strip() for th in table.select('thead th')]
    assert [
        [
            '<td class="col-id">1</td>',
            '<td class="col-content">hello</td>'
        ]
    ] == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_table_not_exists(app_client):
    assert 'Table not found: blah' in app_client.get(
        '/fixtures/blah'
    ).body.decode('utf8')


def test_table_html_no_primary_key(app_client):
    response = app_client.get('/fixtures/no_primary_key')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    # We have disabled sorting for this table using metadata.json
    assert [
        'content', 'a', 'b', 'c'
    ] == [th.string.strip() for th in table.select('thead th')[2:]]
    expected = [
        [
            '<td class="col-Link"><a href="/fixtures/no_primary_key/{}">{}</a></td>'.format(i, i),
            '<td class="col-rowid">{}</td>'.format(i),
            '<td class="col-content">{}</td>'.format(i),
            '<td class="col-a">a{}</td>'.format(i),
            '<td class="col-b">b{}</td>'.format(i),
            '<td class="col-c">c{}</td>'.format(i),
        ] for i in range(1, 51)
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_row_html_no_primary_key(app_client):
    response = app_client.get('/fixtures/no_primary_key/1')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    assert [
        'rowid', 'content', 'a', 'b', 'c'
    ] == [th.string.strip() for th in table.select('thead th')]
    expected = [
        [
            '<td class="col-rowid">1</td>',
            '<td class="col-content">1</td>',
            '<td class="col-a">a1</td>',
            '<td class="col-b">b1</td>',
            '<td class="col-c">c1</td>',
        ]
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_table_html_compound_primary_key(app_client):
    response = app_client.get('/fixtures/compound_primary_key')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    ths = table.findAll('th')
    assert 'Link' == ths[0].string.strip()
    for expected_col, th in zip(('pk1', 'pk2', 'content'), ths[1:]):
        a = th.find('a')
        assert expected_col == a.string
        assert th['class'] == ['col-{}'.format(expected_col)]
        assert a['href'].endswith('/compound_primary_key?_sort={}'.format(
            expected_col
        ))
    expected = [
        [
            '<td class="col-Link"><a href="/fixtures/compound_primary_key/a,b">a,b</a></td>',
            '<td class="col-pk1">a</td>',
            '<td class="col-pk2">b</td>',
            '<td class="col-content">c</td>',
        ]
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_table_html_foreign_key_links(app_client):
    response = app_client.get('/fixtures/foreign_key_references')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    expected = [
        [
            '<td class="col-pk"><a href="/fixtures/foreign_key_references/1">1</a></td>',
            '<td class="col-foreign_key_with_label"><a href="/fixtures/simple_primary_key/1">hello</a>\xa0<em>1</em></td>',
            '<td class="col-foreign_key_with_no_label"><a href="/fixtures/primary_key_multiple_columns/1">1</a></td>'
        ]
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_table_html_disable_foreign_key_links_with_labels(app_client):
    response = app_client.get('/fixtures/foreign_key_references?_labels=off')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    expected = [
        [
            '<td class="col-pk"><a href="/fixtures/foreign_key_references/1">1</a></td>',
            '<td class="col-foreign_key_with_label">1</td>',
            '<td class="col-foreign_key_with_no_label">1</td>'
        ]
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_table_html_foreign_key_custom_label_column(app_client):
    response = app_client.get('/fixtures/custom_foreign_key_label')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    expected = [
        [
            '<td class="col-pk"><a href="/fixtures/custom_foreign_key_label/1">1</a></td>',
            '<td class="col-foreign_key_with_custom_label"><a href="/fixtures/primary_key_multiple_columns_explicit_label/1">world2</a>\xa0<em>1</em></td>',
        ]
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_row_html_compound_primary_key(app_client):
    response = app_client.get('/fixtures/compound_primary_key/a,b')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    assert [
        'pk1', 'pk2', 'content'
    ] == [th.string.strip() for th in table.select('thead th')]
    expected = [
        [
            '<td class="col-pk1">a</td>',
            '<td class="col-pk2">b</td>',
            '<td class="col-content">c</td>',
        ]
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_compound_primary_key_with_foreign_key_references(app_client):
    # e.g. a many-to-many table with a compound primary key on the two columns
    response = app_client.get('/fixtures/searchable_tags')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    expected = [
        [
            '<td class="col-Link"><a href="/fixtures/searchable_tags/1,feline">1,feline</a></td>',
            '<td class="col-searchable_id"><a href="/fixtures/searchable/1">1</a>\xa0<em>1</em></td>',
            '<td class="col-tag"><a href="/fixtures/tags/feline">feline</a></td>',
        ],
        [
            '<td class="col-Link"><a href="/fixtures/searchable_tags/2,canine">2,canine</a></td>',
            '<td class="col-searchable_id"><a href="/fixtures/searchable/2">2</a>\xa0<em>2</em></td>',
            '<td class="col-tag"><a href="/fixtures/tags/canine">canine</a></td>',
        ],
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_view_html(app_client):
    response = app_client.get('/fixtures/simple_view')
    assert response.status == 200
    table = Soup(response.body, 'html.parser').find('table')
    assert [
        'content', 'upper_content'
    ] == [th.string.strip() for th in table.select('thead th')]
    expected = [
        [
            '<td class="col-content">hello</td>',
            '<td class="col-upper_content">HELLO</td>'
        ], [
            '<td class="col-content">world</td>',
            '<td class="col-upper_content">WORLD</td>'
        ], [
            '<td class="col-content">\xa0</td>',
            '<td class="col-upper_content">\xa0</td>'
        ]
    ]
    assert expected == [[str(td) for td in tr.select('td')] for tr in table.select('tbody tr')]


def test_index_metadata(app_client):
    response = app_client.get('/')
    assert response.status == 200
    soup = Soup(response.body, 'html.parser')
    assert 'Datasette Fixtures' == soup.find('h1').text
    assert 'An example SQLite database demonstrating Datasette' == inner_html(
        soup.find('div', {'class': 'metadata-description'})
    )
    assert_footer_links(soup)


def test_database_metadata(app_client):
    response = app_client.get('/fixtures')
    assert response.status == 200
    soup = Soup(response.body, 'html.parser')
    # Page title should be the default
    assert 'fixtures' == soup.find('h1').text
    # Description should be custom
    assert 'Test tables description' == inner_html(
        soup.find('div', {'class': 'metadata-description'})
    )
    # The source/license should be inherited
    assert_footer_links(soup)


def test_table_metadata(app_client):
    response = app_client.get('/fixtures/simple_primary_key')
    assert response.status == 200
    soup = Soup(response.body, 'html.parser')
    # Page title should be custom and should be HTML escaped
    assert 'This &lt;em&gt;HTML&lt;/em&gt; is escaped' == inner_html(soup.find('h1'))
    # Description should be custom and NOT escaped (we used description_html)
    assert 'Simple <em>primary</em> key' == inner_html(soup.find(
        'div', {'class': 'metadata-description'})
    )
    # The source/license should be inherited
    assert_footer_links(soup)


def test_allow_download_on(app_client):
    response = app_client.get(
        "/fixtures"
    )
    soup = Soup(response.body, 'html.parser')
    assert len(soup.findAll('a', {'href': re.compile('\.db$')}))


def test_allow_download_off():
    for client in app_client(config={
        'allow_download': False,
    }):
        response = client.get(
            "/fixtures",

        )
        soup = Soup(response.body, 'html.parser')
        assert not len(soup.findAll('a', {'href': re.compile('\.db$')}))
        # Accessing URL directly should 403
        response = client.get(
            "/fixtures.db",

        )
        assert 403 == response.status


def test_allow_sql_on(app_client):
    response = app_client.get(
        "/fixtures"
    )
    soup = Soup(response.body, 'html.parser')
    assert len(soup.findAll('textarea', {'name': 'sql'}))


def test_allow_sql_off():
    for client in app_client(config={
        'allow_sql': False,
    }):
        response = client.get(
            "/fixtures"
        )
        soup = Soup(response.body, 'html.parser')
        assert not len(soup.findAll('textarea', {'name': 'sql'}))


def assert_querystring_equal(expected, actual):
    assert sorted(expected.split('&')) == sorted(actual.split('&'))


def assert_footer_links(soup):
    footer_links = soup.find('div', {'class': 'ft'}).findAll('a')
    assert 3 == len(footer_links)
    datasette_link, license_link, source_link = footer_links
    assert 'Datasette' == datasette_link.text.strip()
    assert 'tests/fixtures.py' == source_link.text.strip()
    assert 'Apache License 2.0' == license_link.text.strip()
    assert 'https://github.com/simonw/datasette' == datasette_link['href']
    assert 'https://github.com/simonw/datasette/blob/master/tests/fixtures.py' == source_link['href']
    assert 'https://github.com/simonw/datasette/blob/master/LICENSE' == license_link['href']


def inner_html(soup):
    html = str(soup)
    # This includes the parent tag - so remove that
    inner_html = html.split('>', 1)[1].rsplit('<', 1)[0]
    return inner_html.strip()


@pytest.mark.parametrize('path,expected_redirect', [
    ('/fixtures/', '/fixtures'),
    ('/fixtures/simple_view/', '/fixtures/simple_view'),
])
def test_404_trailing_slash_redirect(app_client, path, expected_redirect):
    response = app_client.get(path, allow_redirects=False)
    assert 302 == response.status
    assert expected_redirect == response.headers["Location"]
