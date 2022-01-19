{
  "model_name": { "type": "string", "required": true },
  "dymola": {
    "type": "dict",
    "schema": {
      "simulate": {"type": "boolean"},
      "translate": {"type": "boolean"},
      "comment": {"type": "string"}
    }
  },
  "optimica": {
    "type": "dict",
    "schema": {
      "simulate": {"type": "boolean"},
      "translate": {"type": "boolean"},
      "comment": {"type": "string"},
      "rtol": {"type": "number"},
      "solver": {"type": "string"}
    }
  },
  "openmodelica": {
    "type": "dict",
    "schema": {
      "simulate": {"type": "boolean"},
      "translate": {"type": "boolean"},
      "comment": {"type": "string"},
      "solver": {"type": "string"}
    }
  }
}
