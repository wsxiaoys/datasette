import json
from sanic import response
from .base import RenderMixin


class JsonDataView(RenderMixin):
    def __init__(self, datasette, filename, data_callback):
        self.ds = datasette
        self.jinja_env = datasette.jinja_env
        self.filename = filename
        self.data_callback = data_callback

    async def get(self, request, as_format):
        data = self.data_callback()
        if as_format:
            headers = {}
            if self.ds.cors:
                headers["Access-Control-Allow-Origin"] = "*"
            return response.HTTPResponse(
                json.dumps(data),
                content_type="application/json",
                headers=headers
            )

        else:
            return self.render(
                ["show_json.html"],
                filename=self.filename,
                data=data
            )
