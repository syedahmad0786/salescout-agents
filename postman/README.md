# Postman

`openapi.json` is generated from FastAPI. The collection is converted from that contract and adds only the `data_fragmentation` replay, run chaining, human decision, and zero-send assertions. The environment contains no secrets.

```powershell
postman-cli collection run postman/revenue-intelligence-council.postman_collection.json -e postman/revenue-intelligence-council.postman_environment.json --bail
```
