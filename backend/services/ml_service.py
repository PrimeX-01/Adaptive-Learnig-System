# services/ml_service.py

import numpy as np
import pandas as pd
import shap

CATEGORY_TO_FCL = {
    'Low': 3,
    'Developing': 6,
    'Proficient': 9,
    'Advanced': 12
}


def predict_cognitive_level(request_data: dict, app_state) -> dict:
    model        = app_state.model
    preprocessor = app_state.preprocessor
    fcl_mapping  = app_state.fcl_mapping

    raw = pd.DataFrame([{
        'gender':                      request_data['gender'],
        'race/ethnicity':              request_data.get('race_ethnicity', 'group C'),
        'parental level of education': request_data['parental_level_of_education'],
        'lunch':                       request_data['lunch'],
        'test preparation course':     request_data['test_preparation_course'],
        'math score':                  request_data['math_score'],
        'reading score':               request_data['reading_score'],
        'writing score':               request_data['writing_score'],
    }])

    X_enc      = preprocessor.transform(raw)
    category   = model.predict(X_enc)[0]
    proba      = model.predict_proba(X_enc)[0]
    confidence = float(max(proba))
    fcl_level  = CATEGORY_TO_FCL.get(category, 6)

    cats     = fcl_mapping.get('categories', {})
    fcl_info = cats.get(category, {})

    # SHAP explanation for this prediction
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_enc)
    feat_names  = preprocessor.get_feature_names_out()

    if isinstance(shap_values, list):
        class_idx = list(model.classes_).index(category)
        shap_arr  = shap_values[class_idx][0]
    else:
        shap_arr = shap_values[0]

    top_features = sorted(
        [{'feature': str(n), 'value': float(v)} for n, v in zip(feat_names, shap_arr)],
        key=lambda x: abs(x['value']),
        reverse=True
    )[:5]

    return {
        'performance_category': category,
        'fcl_level':            fcl_level,
        'fcl_range':            fcl_info.get('fcl_range', ''),
        'fcl_description':      fcl_info.get('description', ''),
        'confidence':           confidence,
        'shap_top_features':    top_features
    }