{
    "model_name": {"type": "string", "required": true},
    "dymola": {
        "type": "dict",
        "schema": {
            "translate": {"type": "boolean"},
            "simulate": {"type": "boolean"},
            "comment": {"type": "string"}
        }
    },
    "optimica": {
        "type": "dict",
        "schema": {
            "translate": {"type": "boolean"},
            "simulate": {"type": "boolean"},
            "comment": {"type": "string"},
            "solver": {"type": "string"},
            "rtol": {"type": "number"},
            "ncp": {"type": "integer", "min": 500}
        }
    },
    "openmodelica": {
        "type": "dict",
        "schema": {
            "translate": {"type": "boolean"},
            "simulate": {"type": "boolean"},
            "comment": {"type": "string"},
            "solver": {"type": "string"},
            "rtol": {"type": "number"},
            "ncp": {"type": "integer", "min": 500}
        }
    }
}
