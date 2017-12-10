Running SQL queries
===================

Datasette treats SQLite database files as read-only and immutable. This means it
is not possible to execute INSERT or UPDATE statements using Datasette, which
allows us to expose SELECT statements to the outside world without needing to
worry about SQL injection attacks.

The easiest way to execute custom SQL against Datasette is through the web UI.
The database index page includes a SQL editor that lets you run any SELECT query
you like. You can also construct queries using the filter interface on the
tables page, then click "View and edit SQL" to open that query in the cgustom
SQL editor.

Any Datasette SQL query is reflected in the URL of the page, allowing you to
bookmark them, share them with others and navigate through previous queries
using your browser back button.

You can also retrieve the results of any query as JSON by adding ``.json`` to
the base URL.

Named parameters
----------------

Datasette has special support for SQLite named parameters. Consider a SQL query
like this::

    select * from Street_Tree_List
    where "PermitNotes" like :notes
    and "qSpecies" = :species

If you execute this query using the custom query editor, Datasette will extract
the two named parameters and use them to construct form fields for you to
provide values.

You can also provide values for these fields by constructing a URL::

    /mydatabase?sql=select...&species=44

SQLite string escaping rules will be applied to values passed using named
parameters - they will be wrapped in quotes and their content will be correctly
escaped.

Datasette disallows custom SQL containing the string PRAGMA, as SQLite pragma
statements can be used to change database settings at runtime. If you need to
include the string "pragma" in a query you can do so safely using a named
parameter.

Query limits
------------

To prevent rogue, long-running queries from making a Datasette instance
inaccessible to other users, Datasette imposes some limits on the SQL that you
can execute.

By default, queries have a time limit of one second. If a query takes longer
than this to run Datasette will terminate the query and return an error.

If this time limit is too short for you, you can customize it using the
``sql_time_limit_ms`` option - for example, to increase it to 3.5 seconds::

    datasette mydatabase.db --sql_time_limit_ms=3500

You can optionally set a lower time limit for an individual query using the
``_sql_time_limit_ms`` query string argument::

    /my-database/my-table?qSpecies=44&_sql_time_limit_ms=100

This would set the time limit to 100ms for that specific query. This feature
is useful if you are working with databases of unknown size and complexity -
a query that might make perfect sense for a smaller table could take too long
to execute on a table with millions of rows. By setting custom time limits you
can execute queries "optimistically" - e.g. give me an exact count of rows
matching this query but only if it takes less than 100ms to calculate.

Datasette returns a maximum of 1,000 rows of data at a time. If you execute a
query that returns more than 1,000 rows, Datasette will return the first 1,000
and include a warning that the result set has been truncated. You can use
OFFSET/LIMIT or other methods in your SQL to implement pagination if you need to
return more than 1,000 rows.

Views
-----

If you want to bundle some pre-written SQL queries with your Datasette-hosted
database you can do so in two ways. The first is to include SQL views in your
database - Datasette will then list those views on your database index page.

The easiest way to create views is with the SQLite command-line interface::

    $ sqlite3 sf-trees.db
    SQLite version 3.19.3 2017-06-27 16:48:08
    Enter ".help" for usage hints.
    sqlite> CREATE VIEW demo_view AS select qSpecies from Street_Tree_List;
    <CTRL+D>

Canned queries
--------------

As an alternative to adding views to your database, you can define canned
queries inside your ``metadata.json`` file. Here's an example::

    {
        "databases": {
           "sf-trees": {
               "queries": {
                   "just_species": "select qSpecies from Street_Tree_List"
               }
           }
        }
    }

Then run datasette like this::

    datasette sf-trees.db -m metadata.json

Each canned query will be listed on the database index page, and will also get
its own URL at::

    /database-name/canned-query-name

For the above example, that URL would be::

    /sf-trees/just_species

Canned queries support named parameters, so if you include those in the SQL you
will then be able to enter them using the form fields on the canned query page
or by adding them to the URL. This means canned queries can be used to create
custom JSON APIs based on a carefully designed SQL.
