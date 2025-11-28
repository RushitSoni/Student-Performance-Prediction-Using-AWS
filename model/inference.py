import joblib
import json
import numpy as np
import pandas as pd

def model_fn(model_dir):
    model = joblib.load(f"{model_dir}/model.joblib")
    return model

def input_fn(request_body, request_content_type):
    if request_content_type == "application/json":
        data = json.loads(request_body)

        # Convert to DataFrame — IMPORTANT
        df = pd.DataFrame(data)

        return df   # pipeline expects DataFrame
    else:
        raise ValueError("Unsupported content type")


def predict_fn(input_data, model):
    try:
        preds = model.predict(input_data)
        return preds
    except Exception as e:
        return {"error": str(e)}


def output_fn(prediction, content_type):
    return json.dumps({"prediction": prediction.tolist()})
