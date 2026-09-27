"""
export_openapi.py
------------------
Dumps the live OpenAPI 3.1 contract to openapi.json. This is the file you
hand to an API gateway (AWS API Gateway "Import API", Azure APIM, Apigee,
Kong) to register this service, generate a client SDK, or validate
requests at the edge - the point of the "integrate into a cloud-native
API" step.

Usage:
    python export_openapi.py            # writes ./openapi.json
"""
import json
from pathlib import Path

from api.main import app

if __name__ == "__main__":
    schema = app.openapi()
    out = Path(__file__).parent / "openapi.json"
    out.write_text(json.dumps(schema, indent=2))
    print(f"Wrote {out} ({len(schema['paths'])} paths, OpenAPI {schema['openapi']})")
