Changelog
=========

0.14 (2017-12-09)
-----------------

The theme of this release is customization: Datasette now allows every aspect
of its presentation `to be customized <http://datasette.readthedocs.io/en/latest/custom_templates.html>`_
either using additional CSS or by providing entirely new templates.

Datasette's `metadata.json format <http://datasette.readthedocs.io/en/latest/metadata.html>`_
has also been expanded, to allow per-database and per-table metadata. A new
``datasette skeleton`` command can be used to generate a skeleton JSON file
ready to be filled in with per-database and per-table details.

The ``metadata.json`` file can also be used to define
`canned queries <http://datasette.readthedocs.io/en/latest/sql_queries.html#canned-queries>`_,
as a more powerful alternative to SQL views.

- ``extra_css_urls``/``extra_js_urls`` in metadata

  A mechanism in the ``metadata.json`` format for adding custom CSS and JS urls.

  Create a ``metadata.json`` file that looks like this::

      {
          "extra_css_urls": [
              "https://simonwillison.net/static/css/all.bf8cd891642c.css"
          ],
          "extra_js_urls": [
              "https://code.jquery.com/jquery-3.2.1.slim.min.js"
          ]
      }

  Then start datasette like this::

      datasette mydb.db --metadata=metadata.json

  The CSS and JavaScript files will be linked in the ``<head>`` of every page.

  You can also specify a SRI (subresource integrity hash) for these assets::

      {
          "extra_css_urls": [
              {
                  "url": "https://simonwillison.net/static/css/all.bf8cd891642c.css",
                  "sri": "sha384-9qIZekWUyjCyDIf2YK1FRoKiPJq4PHt6tp/ulnuuyRBvazd0hG7pWbE99zvwSznI"
              }
          ],
          "extra_js_urls": [
              {
                  "url": "https://code.jquery.com/jquery-3.2.1.slim.min.js",
                  "sri": "sha256-k2WSCIexGzOj3Euiig+TlR8gA0EmPjuc79OEeY5L45g="
              }
          ]
      }

  Modern browsers will only execute the stylesheet or JavaScript if the SRI hash
  matches the content served. You can generate hashes using https://www.srihash.org/

- Auto-link column values that look like URLs (`#153 <https://github.com/simonw/datasette/issues/153>`_)

- CSS styling hooks as classes on the body (`#153 <https://github.com/simonw/datasette/issues/153>`_)

  Every template now gets CSS classes in the body designed to support custom
  styling.

  The index template (the top level page at ``/``) gets this::

      <body class="index">

  The database template (``/dbname/``) gets this::

      <body class="db db-dbname">

  The table template (``/dbname/tablename``) gets::

      <body class="table db-dbname table-tablename">

  The row template (``/dbname/tablename/rowid``) gets::

      <body class="row db-dbname table-tablename">

  The ``db-x`` and ``table-x`` classes use the database or table names themselves IF
  they are valid CSS identifiers. If they aren't, we strip any invalid
  characters out and append a 6 character md5 digest of the original name, in
  order to ensure that multiple tables which resolve to the same stripped
  character version still have different CSS classes.

  Some examples (extracted from the unit tests)::

      "simple" => "simple"
      "MixedCase" => "MixedCase"
      "-no-leading-hyphens" => "no-leading-hyphens-65bea6"
      "_no-leading-underscores" => "no-leading-underscores-b921bc"
      "no spaces" => "no-spaces-7088d7"
      "-" => "336d5e"
      "no $ characters" => "no--characters-59e024"

- ``datasette --template-dir=mytemplates/`` argument

  You can now pass an additional argument specifying a directory to look for
  custom templates in.

  Datasette will fall back on the default templates if a template is not
  found in that directory.

- Ability to over-ride templates for individual tables/databases.

  It is now possible to over-ride templates on a per-database / per-row or per-
  table basis.

  When you access e.g. ``/mydatabase/mytable`` Datasette will look for the following::

      - table-mydatabase-mytable.html
      - table.html

  If you provided a ``--template-dir`` argument to datasette serve it will look in
  that directory first.

  The lookup rules are as follows::

      Index page (/):
          index.html

      Database page (/mydatabase):
          database-mydatabase.html
          database.html

      Table page (/mydatabase/mytable):
          table-mydatabase-mytable.html
          table.html

      Row page (/mydatabase/mytable/id):
          row-mydatabase-mytable.html
          row.html

  If a table name has spaces or other unexpected characters in it, the template
  filename will follow the same rules as our custom ``<body>`` CSS classes
  - for example, a table called "Food Trucks"
  will attempt to load the following templates::

      table-mydatabase-Food-Trucks-399138.html
      table.html

  It is possible to extend the default templates using Jinja template
  inheritance. If you want to customize EVERY row template with some additional
  content you can do so by creating a row.html template like this::

      {% extends "default:row.html" %}

      {% block content %}
      <h1>EXTRA HTML AT THE TOP OF THE CONTENT BLOCK</h1>
      <p>This line renders the original block:</p>
      {{ super() }}
      {% endblock %}

- ``--static`` option for datasette serve (`#160 <https://github.com/simonw/datasette/issues/160>`_)

  You can now tell Datasette to serve static files from a specific location at a
  specific mountpoint.

  For example::

    datasette serve mydb.db --static extra-css:/tmp/static/css

  Now if you visit this URL::

    http://localhost:8001/extra-css/blah.css

  The following file will be served::

    /tmp/static/css/blah.css

- Canned query support.

  Named canned queries can now be defined in ``metadata.json`` like this::

      {
          "databases": {
              "timezones": {
                  "queries": {
                      "timezone_for_point": "select tzid from timezones ..."
                  }
              }
          }
      }

  These will be shown in a new "Queries" section beneath "Views" on the database page.

- New ``datasette skeleton`` command for generating ``metadata.json`` (`#164 <https://github.com/simonw/datasette/issues/164>`_)

- ``metadata.json`` support for per-table/per-database metadata (`#165 <https://github.com/simonw/datasette/issues/165>`_)

  Also added support for descriptions and HTML descriptions.

  Here's an example metadata.json file illustrating custom per-database and per-
  table metadata::

      {
          "title": "Overall datasette title",
          "description_html": "This is a <em>description with HTML</em>.",
          "databases": {
              "db1": {
                  "title": "First database",
                  "description": "This is a string description & has no HTML",
                  "license_url": "http://example.com/",
              "license": "The example license",
                  "queries": {
                    "canned_query": "select * from table1 limit 3;"
                  },
                  "tables": {
                      "table1": {
                          "title": "Custom title for table1",
                          "description": "Tables can have descriptions too",
                          "source": "This has a custom source",
                          "source_url": "http://example.com/"
                      }
                  }
              }
          }
      }

- Renamed ``datasette build`` command to ``datasette inspect`` (`#130 <https://github.com/simonw/datasette/issues/130>`_)

- Upgrade to Sanic 0.7.0 (`#168 <https://github.com/simonw/datasette/issues/168>`_)

  https://github.com/channelcat/sanic/releases/tag/0.7.0

- Package and publish commands now accept ``--static`` and ``--template-dir``

  Example usage::

      datasette package --static css:extra-css/ --static js:extra-js/ \
        sf-trees.db --template-dir templates/ --tag sf-trees --branch master

  This creates a local Docker image that includes copies of the templates/,
  extra-css/ and extra-js/ directories. You can then run it like this::

    docker run -p 8001:8001 sf-trees

  For publishing to Zeit now::

    datasette publish now --static css:extra-css/ --static js:extra-js/ \
      sf-trees.db --template-dir templates/ --name sf-trees --branch master

- HTML comment showing which templates were considered for a page (`#171 <https://github.com/simonw/datasette/issues/171>`_)

0.13 (2017-11-24)
-----------------
- Search now applies to current filters.

  Combined search into the same form as filters.

  Closes `#133`_

- Much tidier design for table view header.

  Closes `#147`_

- Added ``?column__not=blah`` filter.

  Closes `#148`_

- Row page now resolves foreign keys.

  Closes `#132`_

- Further tweaks to select/input filter styling.

  Refs `#86`_ - thanks for the help, @natbat!

- Show linked foreign key in table cells.

- Added UI for editing table filters.

  Refs `#86`_

- Hide FTS-created tables on index pages.

  Closes `#129`_

- Add publish to heroku support [Jacob Kaplan-Moss]

  ``datasette publish heroku mydb.db``

  Pull request `#104`_

- Initial implementation of ``?_group_count=column``.

  URL shortcut for counting rows grouped by one or more columns.

  ``?_group_count=column1&_group_count=column2`` works as well.

  SQL generated looks like this::

      select "qSpecies", count(*) as "count"
      from Street_Tree_List
      group by "qSpecies"
      order by "count" desc limit 100

  Or for two columns like this::

      select "qSpecies", "qSiteInfo", count(*) as "count"
      from Street_Tree_List
      group by "qSpecies", "qSiteInfo"
      order by "count" desc limit 100

  Refs `#44`_

- Added ``--build=master`` option to datasette publish and package.

  The ``datasette publish`` and ``datasette package`` commands both now accept an
  optional ``--build`` argument. If provided, this can be used to specify a branch
  published to GitHub that should be built into the container.

  This makes it easier to test code that has not yet been officially released to
  PyPI, e.g.::

      datasette publish now mydb.db --branch=master

- Implemented ``?_search=XXX`` + UI if a FTS table is detected.

  Closes `#131`_

- Added ``datasette --version`` support.

- Table views now show expanded foreign key references, if possible.

  If a table has foreign key columns, and those foreign key tables have
  ``label_columns``, the TableView will now query those other tables for the
  corresponding values and display those values as links in the corresponding
  table cells.

  label_columns are currently detected by the ``inspect()`` function, which looks
  for any table that has just two columns - an ID column and one other - and
  sets the ``label_column`` to be that second non-ID column.

- Don't prevent tabbing to "Run SQL" button (`#117`_) [Robert Gieseke]

  See comment in `#115`_

- Add keyboard shortcut to execute SQL query (`#115`_) [Robert Gieseke]

- Allow ``--load-extension`` to be set via environment variable.

- Add support for ``?field__isnull=1`` (`#107`_) [Ray N]

- Add spatialite, switch to debian and local build (`#114`_) [Ariel Núñez]

- Added ``--load-extension`` argument to datasette serve.

  Allows loading of SQLite extensions. Refs `#110`_.

.. _#133: https://github.com/simonw/datasette/issues/133
.. _#147: https://github.com/simonw/datasette/issues/147
.. _#148: https://github.com/simonw/datasette/issues/148
.. _#132: https://github.com/simonw/datasette/issues/132
.. _#86: https://github.com/simonw/datasette/issues/86
.. _#129: https://github.com/simonw/datasette/issues/129
.. _#104: https://github.com/simonw/datasette/issues/104
.. _#44: https://github.com/simonw/datasette/issues/44
.. _#131: https://github.com/simonw/datasette/issues/131
.. _#115: https://github.com/simonw/datasette/issues/115
.. _#117: https://github.com/simonw/datasette/issues/117
.. _#107: https://github.com/simonw/datasette/issues/107
.. _#114: https://github.com/simonw/datasette/issues/114
.. _#110: https://github.com/simonw/datasette/issues/110

0.12 (2017-11-16)
-----------------
- Added ``__version__``, now displayed as tooltip in page footer (`#108`_).
- Added initial docs, including a changelog (`#99`_).
- Turned on auto-escaping in Jinja.
- Added a UI for editing named parameters (`#96`_).

  You can now construct a custom SQL statement using SQLite named
  parameters (e.g. ``:name``) and datasette will display form fields for
  editing those parameters. `Here’s an example`_ which lets you see the
  most popular names for dogs of different species registered through
  various dog registration schemes in Australia.

.. _Here’s an example: https://australian-dogs.now.sh/australian-dogs-3ba9628?sql=select+name%2C+count%28*%29+as+n+from+%28%0D%0A%0D%0Aselect+upper%28%22Animal+name%22%29+as+name+from+%5BAdelaide-City-Council-dog-registrations-2013%5D+where+Breed+like+%3Abreed%0D%0A%0D%0Aunion+all%0D%0A%0D%0Aselect+upper%28Animal_Name%29+as+name+from+%5BAdelaide-City-Council-dog-registrations-2014%5D+where+Breed_Description+like+%3Abreed%0D%0A%0D%0Aunion+all+%0D%0A%0D%0Aselect+upper%28Animal_Name%29+as+name+from+%5BAdelaide-City-Council-dog-registrations-2015%5D+where+Breed_Description+like+%3Abreed%0D%0A%0D%0Aunion+all%0D%0A%0D%0Aselect+upper%28%22AnimalName%22%29+as+name+from+%5BCity-of-Port-Adelaide-Enfield-Dog_Registrations_2016%5D+where+AnimalBreed+like+%3Abreed%0D%0A%0D%0Aunion+all%0D%0A%0D%0Aselect+upper%28%22Animal+Name%22%29+as+name+from+%5BMitcham-dog-registrations-2015%5D+where+Breed+like+%3Abreed%0D%0A%0D%0Aunion+all%0D%0A%0D%0Aselect+upper%28%22DOG_NAME%22%29+as+name+from+%5Bburnside-dog-registrations-2015%5D+where+DOG_BREED+like+%3Abreed%0D%0A%0D%0Aunion+all+%0D%0A%0D%0Aselect+upper%28%22Animal_Name%22%29+as+name+from+%5Bcity-of-playford-2015-dog-registration%5D+where+Breed_Description+like+%3Abreed%0D%0A%0D%0Aunion+all%0D%0A%0D%0Aselect+upper%28%22Animal+Name%22%29+as+name+from+%5Bcity-of-prospect-dog-registration-details-2016%5D+where%22Breed+Description%22+like+%3Abreed%0D%0A%0D%0A%29+group+by+name+order+by+n+desc%3B&breed=pug

- Pin to specific Jinja version. (`#100`_).
- Default to 127.0.0.1 not 0.0.0.0. (`#98`_).
- Added extra metadata options to publish and package commands. (`#92`_).

  You can now run these commands like so::

      datasette now publish mydb.db \
          --title="My Title" \
          --source="Source" \
          --source_url="http://www.example.com/" \
          --license="CC0" \
          --license_url="https://creativecommons.org/publicdomain/zero/1.0/"

  This will write those values into the metadata.json that is packaged with the
  app. If you also pass ``--metadata=metadata.json`` that file will be updated with the extra
  values before being written into the Docker image.
- Added simple production-ready Dockerfile (`#94`_) [Andrew
  Cutler]
- New ``?_sql_time_limit_ms=10`` argument to database and table page (`#95`_)
- SQL syntax highlighting with Codemirror (`#89`_) [Tom Dyson]

.. _#89: https://github.com/simonw/datasette/issues/89
.. _#92: https://github.com/simonw/datasette/issues/92
.. _#94: https://github.com/simonw/datasette/issues/94
.. _#95: https://github.com/simonw/datasette/issues/95
.. _#96: https://github.com/simonw/datasette/issues/96
.. _#98: https://github.com/simonw/datasette/issues/98
.. _#99: https://github.com/simonw/datasette/issues/99
.. _#100: https://github.com/simonw/datasette/issues/100
.. _#108: https://github.com/simonw/datasette/issues/108

0.11 (2017-11-14)
-----------------
- Added ``datasette publish now --force`` option.

  This calls ``now`` with ``--force`` - useful as it means you get a fresh copy of datasette even if Now has already cached that docker layer.
- Enable ``--cors`` by default when running in a container.

0.10 (2017-11-14)
-----------------
- Fixed `#83`_ - 500 error on individual row pages.
- Stop using sqlite WITH RECURSIVE in our tests.

  The version of Python 3 running in Travis CI doesn't support this.

.. _#83: https://github.com/simonw/datasette/issues/83

0.9 (2017-11-13)
----------------
- Added ``--sql_time_limit_ms`` and ``--extra-options``.

  The serve command now accepts ``--sql_time_limit_ms`` for customizing the SQL time
  limit.

  The publish and package commands now accept ``--extra-options`` which can be used
  to specify additional options to be passed to the datasite serve command when
  it executes inside the resulting Docker containers.

0.8 (2017-11-13)
----------------
- V0.8 - added PyPI metadata, ready to ship.
- Implemented offset/limit pagination for views (`#70`_).
- Improved pagination. (`#78`_)
- Limit on max rows returned, controlled by ``--max_returned_rows`` option. (`#69`_)

  If someone executes 'select * from table' against a table with a million rows
  in it, we could run into problems: just serializing that much data as JSON is
  likely to lock up the server.

  Solution: we now have a hard limit on the maximum number of rows that can be
  returned by a query. If that limit is exceeded, the server will return a
  ``"truncated": true`` field in the JSON.

  This limit can be optionally controlled by the new ``--max_returned_rows``
  option. Setting that option to 0 disables the limit entirely.

.. _#70: https://github.com/simonw/datasette/issues/70
.. _#78: https://github.com/simonw/datasette/issues/78
.. _#69: https://github.com/simonw/datasette/issues/69
